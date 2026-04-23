"""
AI Agent service – supports Claude (Anthropic), Gemini (Google), OpenAI.

The agent has read-only tools to query the local database and can be extended
with write tools (create order, assign email) in the future.
"""
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from pathlib import Path
import app.services.client_service as client_svc
import app.services.order_service as order_svc
import app.services.email_service as email_svc
from app.config import _BASE_DIR

PROVIDERS = ["Claude (Anthropic)", "Gemini (Google)", "OpenAI"]

SOUL_FILE = _BASE_DIR / "soul.md"
MEMORY_FILE = _BASE_DIR / "memory.md"
CONTEXT_FILE = _BASE_DIR / "context.md"

_SOUL_DEFAULT = """# Soul
Jestem Marek – asystent biurowy firmy stolarki okiennej.
Odpowiadam po polsku, zwięźle i rzeczowo. Nie wymyślam danych – używam narzędzi.
"""
_MEMORY_DEFAULT = "# Memory\n\n(brak zapisanych informacji)\n"
_CONTEXT_DEFAULT = "# Context\n\nNazwa firmy: (uzupełnij)\nBranża: stolarka okienna\n"


def _read_file(path: Path, default: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    path.write_text(default, encoding="utf-8")
    return default.strip()


def _append_memory(text: str) -> None:
    """Append a new memory entry to memory.md."""
    content = _read_file(MEMORY_FILE, _MEMORY_DEFAULT)
    updated = content + f"\n- {text.strip()}"
    MEMORY_FILE.write_text(updated, encoding="utf-8")


def get_agent_files() -> Dict[str, str]:
    return {
        "soul": _read_file(SOUL_FILE, _SOUL_DEFAULT),
        "memory": _read_file(MEMORY_FILE, _MEMORY_DEFAULT),
        "context": _read_file(CONTEXT_FILE, _CONTEXT_DEFAULT),
    }


def save_agent_file(name: str, content: str) -> None:
    files = {"soul": SOUL_FILE, "memory": MEMORY_FILE, "context": CONTEXT_FILE}
    if name in files:
        files[name].write_text(content, encoding="utf-8")

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
    soul = _read_file(SOUL_FILE, _SOUL_DEFAULT)
    memory = _read_file(MEMORY_FILE, _MEMORY_DEFAULT)
    context = _read_file(CONTEXT_FILE, _CONTEXT_DEFAULT)
    return (
        f"{soul}\n\n"
        f"---\n## Informacje o firmie\n{context}\n\n"
        f"---\n## Twoja pamięć (zapamiętane informacje)\n{memory}\n\n"
        "---\n"
        "Masz dostęp do bazy danych firmy przez narzędzia. "
        "Gdy pytają o dane – użyj odpowiedniego narzędzia zamiast zgadywać. "
        "Jeśli w rozmowie pojawi się ważna informacja warta zapamiętania, "
        "zakończ odpowiedź tagiem: <zapamiętaj>treść do zapamiętania</zapamiętaj>"
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


def _http_get(url: str, headers: Optional[dict] = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {error_body}")


def _list_claude_models(api_key: str) -> List[str]:
    resp = _http_get(
        "https://api.anthropic.com/v1/models",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    return [item["id"] for item in resp.get("data", []) if item.get("id")]


def _list_gemini_models(api_key: str) -> List[str]:
    resp = _http_get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    )
    models = []
    for item in resp.get("models", []):
        methods = item.get("supportedGenerationMethods", [])
        if methods and "generateContent" not in methods:
            continue
        model_id = item.get("baseModelId") or item.get("name", "").replace("models/", "")
        if model_id:
            models.append(model_id)
    return models


def _list_openai_models(api_key: str) -> List[str]:
    resp = _http_get(
        "https://api.openai.com/v1/models",
        {"Authorization": f"Bearer {api_key}"},
    )
    allowed_prefixes = ("gpt-", "o", "chatgpt-")
    blocked_prefixes = ("gpt-image-", "gpt-audio-", "gpt-realtime")
    models = []
    for item in resp.get("data", []):
        model_id = item.get("id", "")
        if not model_id:
            continue
        if blocked_prefixes and model_id.startswith(blocked_prefixes):
            continue
        if model_id.startswith(allowed_prefixes):
            models.append(model_id)
    return models


def list_models(cfg: dict) -> List[str]:
    provider = cfg.get("provider", "Claude (Anthropic)")
    api_key = cfg.get("api_key", "").strip()
    if not api_key:
        return []

    if "Claude" in provider:
        models = _list_claude_models(api_key)
    elif "Gemini" in provider:
        models = _list_gemini_models(api_key)
    else:
        models = _list_openai_models(api_key)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(models))


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


def _extract_and_save_memory(response: str) -> str:
    """Extract <zapamiętaj>...</zapamiętaj> tag, save to memory.md, return cleaned response."""
    import re
    matches = re.findall(r"<zapamiętaj>(.*?)</zapamiętaj>", response, re.DOTALL)
    for match in matches:
        _append_memory(match.strip())
    return re.sub(r"<zapamiętaj>.*?</zapamiętaj>", "", response, flags=re.DOTALL).strip()


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
            response = _chat_claude(api_key, messages, model or "claude-sonnet-4-6")
        elif "Gemini" in provider:
            response = _chat_gemini(api_key, messages, model or "gemini-2.0-flash")
        else:
            response = _chat_openai(api_key, messages, model or "gpt-4o-mini")
        return _extract_and_save_memory(response)
    except RuntimeError as e:
        return f"Błąd API: {e}"
    except Exception as e:
        return f"Błąd: {e}"
