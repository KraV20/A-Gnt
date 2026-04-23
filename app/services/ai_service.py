"""
AI Agent service – supports Claude (Anthropic), Gemini (Google), OpenAI.

The agent has read-only tools to query the local database and can be extended
with write tools (create order, assign email) in the future.
"""
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
import app.services.client_service as client_svc
import app.services.order_service as order_svc
import app.services.email_service as email_svc

PROVIDERS = ["Claude (Anthropic)", "Gemini (Google)", "OpenAI"]

# ── Tool definitions ────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_clients",
        "description": "Pobiera listę wszystkich klientów z bazy danych.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Opcjonalna fraza wyszukiwania"}
            },
        },
    },
    {
        "name": "get_orders",
        "description": "Pobiera zlecenia z bazy danych. Można filtrować po statusie.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status: nowe, w trakcie, wstrzymane, zakończone, anulowane",
                },
                "search": {"type": "string", "description": "Opcjonalna fraza wyszukiwania"},
            },
        },
    },
    {
        "name": "get_emails",
        "description": "Pobiera ostatnie wiadomości e-mail ze skrzynki.",
        "input_schema": {
            "type": "object",
            "properties": {
                "unread_only": {"type": "boolean", "description": "Tylko nieprzeczytane"},
                "limit": {"type": "integer", "description": "Liczba maili (domyślnie 20)"},
            },
        },
    },
    {
        "name": "get_stats",
        "description": "Pobiera statystyki zleceń (liczba per status) i liczbę klientów.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _run_tool(name: str, inputs: dict) -> str:
    if name == "get_clients":
        query = inputs.get("search", "")
        clients = client_svc.search(query) if query else client_svc.get_all()
        data = [{"id": c.id, "nazwa": c.name, "firma": c.company,
                 "email": c.email, "telefon": c.phone, "miasto": c.city} for c in clients]
        return json.dumps(data, ensure_ascii=False)

    if name == "get_orders":
        status = inputs.get("status")
        query = inputs.get("search", "")
        orders = order_svc.search(query) if query else order_svc.get_all(status=status or None)
        data = [{"id": o.id, "numer": o.number, "tytuł": o.title, "klient": o.client_name,
                 "status": o.status, "priorytet": o.priority,
                 "termin": o.deadline, "wartość": o.value_display} for o in orders]
        return json.dumps(data, ensure_ascii=False)

    if name == "get_emails":
        unread_only = inputs.get("unread_only", False)
        limit = inputs.get("limit", 20)
        emails = email_svc.get_all(unread_only=unread_only)[:limit]
        data = [{"id": e.id, "temat": e.subject, "od": e.sender,
                 "data": e.date[:16], "przeczytany": e.is_read,
                 "klient": e.client_name} for e in emails]
        return json.dumps(data, ensure_ascii=False)

    if name == "get_stats":
        stats = order_svc.get_stats()
        clients = client_svc.get_all()
        unread = email_svc.get_unread_count()
        return json.dumps({
            "zlecenia": stats,
            "klienci_łącznie": len(clients),
            "nieprzeczytane_maile": unread,
        }, ensure_ascii=False)

    return json.dumps({"error": f"Nieznane narzędzie: {name}"})


def _system_prompt() -> str:
    return (
        "Jesteś asystentem biurowym dla firmy zajmującej się produkcją okien i drzwi (WHOkna). "
        "Pomagasz zarządzać klientami, zleceniami, dokumentami i skrzynką e-mail. "
        "Masz dostęp do bazy danych firmy przez narzędzia. "
        "Odpowiadaj po polsku, zwięźle i rzeczowo. "
        "Gdy pytają o dane – użyj odpowiedniego narzędzia zamiast zgadywać."
    )


def _http_post(url: str, headers: dict, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {error_body}")


# ── Claude (Anthropic) ───────────────────────────────────────────────────────

def _chat_claude(api_key: str, messages: List[Dict], model: str = "claude-sonnet-4-6") -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Tool-use loop
    current_messages = list(messages)
    for _ in range(5):
        body = {
            "model": model,
            "max_tokens": 1024,
            "system": _system_prompt(),
            "tools": TOOLS,
            "messages": current_messages,
        }
        resp = _http_post(url, headers, body)

        if resp.get("stop_reason") == "tool_use":
            tool_results = []
            assistant_content = resp["content"]
            for block in assistant_content:
                if block["type"] == "tool_use":
                    result = _run_tool(block["name"], block.get("input", {}))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result,
                    })
            current_messages.append({"role": "assistant", "content": assistant_content})
            current_messages.append({"role": "user", "content": tool_results})
        else:
            for block in resp.get("content", []):
                if block.get("type") == "text":
                    return block["text"]
            return ""

    return "Przekroczono limit wywołań narzędzi."


# ── Gemini (Google) ──────────────────────────────────────────────────────────

def _tools_to_gemini() -> list:
    functions = []
    for t in TOOLS:
        schema = t["input_schema"].copy()
        schema.pop("type", None)
        functions.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": {"type": "object", **schema},
        })
    return [{"function_declarations": functions}]


def _chat_gemini(api_key: str, messages: List[Dict], model: str = "gemini-2.0-flash") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"content-type": "application/json"}

    contents = [{"role": "user" if m["role"] == "user" else "model",
                 "parts": [{"text": m["content"]}]} for m in messages if isinstance(m["content"], str)]

    for _ in range(5):
        body = {
            "system_instruction": {"parts": [{"text": _system_prompt()}]},
            "contents": contents,
            "tools": _tools_to_gemini(),
        }
        resp = _http_post(url, headers, body)
        candidate = resp.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])

        tool_calls = [p for p in parts if "functionCall" in p]
        if tool_calls:
            contents.append({"role": "model", "parts": parts})
            result_parts = []
            for p in tool_calls:
                fc = p["functionCall"]
                result = _run_tool(fc["name"], fc.get("args", {}))
                result_parts.append({
                    "functionResponse": {
                        "name": fc["name"],
                        "response": {"content": result},
                    }
                })
            contents.append({"role": "user", "parts": result_parts})
        else:
            return "".join(p.get("text", "") for p in parts)

    return "Przekroczono limit wywołań narzędzi."


# ── OpenAI ───────────────────────────────────────────────────────────────────

def _tools_to_openai() -> list:
    return [{"type": "function", "function": {
        "name": t["name"],
        "description": t["description"],
        "parameters": t["input_schema"],
    }} for t in TOOLS]


def _chat_openai(api_key: str, messages: List[Dict], model: str = "gpt-4o-mini") -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}

    current_messages = [{"role": "system", "content": _system_prompt()}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
        if isinstance(m["content"], str)
    ]

    for _ in range(5):
        body = {"model": model, "messages": current_messages, "tools": _tools_to_openai()}
        resp = _http_post(url, headers, body)
        msg = resp["choices"][0]["message"]

        if msg.get("tool_calls"):
            current_messages.append(msg)
            for tc in msg["tool_calls"]:
                fn = tc["function"]
                result = _run_tool(fn["name"], json.loads(fn.get("arguments", "{}")))
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
        else:
            return msg.get("content", "")

    return "Przekroczono limit wywołań narzędzi."


# ── Public API ───────────────────────────────────────────────────────────────

def chat(cfg: dict, messages: List[Dict]) -> str:
    """
    cfg: {"provider": "Claude (Anthropic)", "api_key": "...", "model": "..."}
    messages: [{"role": "user"/"assistant", "content": "..."}]
    """
    provider = cfg.get("provider", "Claude (Anthropic)")
    api_key = cfg.get("api_key", "")
    model = cfg.get("model", "")

    if not api_key:
        return "Brak klucza API. Skonfiguruj go w Ustawienia → AI Agent."

    try:
        if "Claude" in provider:
            return _chat_claude(api_key, messages, model or "claude-sonnet-4-6")
        elif "Gemini" in provider:
            return _chat_gemini(api_key, messages, model or "gemini-2.0-flash")
        else:
            return _chat_openai(api_key, messages, model or "gpt-4o-mini")
    except RuntimeError as e:
        return f"Błąd API: {e}"
    except Exception as e:
        return f"Błąd: {e}"
