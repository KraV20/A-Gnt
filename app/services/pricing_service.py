"""
Pricing service for smart-slide windows.

Two modes:
  1. Rule-based - always available, uses parametric price table
  2. ML-based   - available after training on uploaded dataset (RandomForest)
"""
import json
import pickle
import random
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import _BASE_DIR
from app.models.pricing import (
    COLORS,
    CONFIGURATIONS,
    GLASS_TYPES,
    HARDWARE,
    THRESHOLDS,
    PriceResult,
    SmartSlideConfig,
)

_PRICING_DIR = _BASE_DIR / "pricing"
_PRICING_DIR.mkdir(exist_ok=True)

_MODEL_FILE = _PRICING_DIR / "model.pkl"
_META_FILE = _PRICING_DIR / "model_meta.json"
_DATASETS_DIR = _PRICING_DIR / "datasets"
_DATASETS_DIR.mkdir(exist_ok=True)
_REPORTS_DIR = _PRICING_DIR / "reports"
_REPORTS_DIR.mkdir(exist_ok=True)

_BASE_PRICE_PER_M2 = 1200.0

_GLASS_FACTORS = {
    GLASS_TYPES[0]: 1.00,
    GLASS_TYPES[1]: 1.10,
    GLASS_TYPES[2]: 1.30,
    GLASS_TYPES[3]: 1.45,
    GLASS_TYPES[4]: 1.55,
    GLASS_TYPES[5]: 1.65,
    GLASS_TYPES[6]: 1.80,
}
_COLOR_SURCHARGE = {
    COLORS[0]: 0,
    COLORS[1]: 150,
    COLORS[2]: 250,
    COLORS[3]: 200,
    COLORS[4]: 200,
    COLORS[5]: 300,
    COLORS[6]: 200,
}
_THRESHOLD_SURCHARGE = {
    THRESHOLDS[0]: 0,
    THRESHOLDS[1]: 400,
    THRESHOLDS[2]: 800,
}
_HARDWARE_SURCHARGE = {
    HARDWARE[0]: 0,
    HARDWARE[1]: 600,
    HARDWARE[2]: 1400,
}
_CONFIG_FACTOR = {
    CONFIGURATIONS[0]: 1.00,
    CONFIGURATIONS[1]: 1.35,
    CONFIGURATIONS[2]: 1.65,
    CONFIGURATIONS[3]: 1.90,
}

REQUIRED_COLUMNS = {
    "width_mm",
    "height_mm",
    "configuration",
    "glass_type",
    "color",
    "threshold",
    "hardware",
    "mosquito_net",
    "installation",
    "price_net",
}

FEATURE_COLS = [
    "width_mm",
    "height_mm",
    "area_m2",
    "configuration",
    "glass_type",
    "color",
    "threshold",
    "hardware",
    "mosquito_net",
    "installation",
]


def _normalize_text(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _parse_decimal(value: str) -> float:
    cleaned = str(value).strip().replace(" ", "").replace("\u00a0", "")
    if not cleaned:
        return 0.0
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def _parse_bool(value: str) -> int:
    normalized = _normalize_text(value)
    return 1 if normalized in {"1", "tak", "true", "yes", "y", "t"} else 0


def calculate_rules(cfg: SmartSlideConfig) -> PriceResult:
    area = cfg.area_m2
    glass_f = _GLASS_FACTORS.get(cfg.glass_type, 1.0)
    config_f = _CONFIG_FACTOR.get(cfg.configuration, 1.0)

    base = area * _BASE_PRICE_PER_M2 * glass_f * config_f
    color_s = _COLOR_SURCHARGE.get(cfg.color, 0)
    threshold_s = _THRESHOLD_SURCHARGE.get(cfg.threshold, 0)
    hardware_s = _HARDWARE_SURCHARGE.get(cfg.hardware, 0)
    mosquito_s = 280 if cfg.mosquito_net else 0
    install_s = round(base * 0.12) if cfg.installation else 0

    net = (base + color_s + threshold_s + hardware_s + mosquito_s + install_s) * cfg.quantity

    return PriceResult(
        net_price=round(net, 2),
        source="rules",
        breakdown={
            "Podstawa": round(base * cfg.quantity, 2),
            "Kolor": color_s * cfg.quantity,
            "Prog": threshold_s * cfg.quantity,
            "Okucia": hardware_s * cfg.quantity,
            "Siatka": mosquito_s * cfg.quantity,
            "Montaz": install_s,
        },
    )


def _load_model() -> Tuple[Optional[object], Optional[dict]]:
    if _MODEL_FILE.exists() and _META_FILE.exists():
        with open(_MODEL_FILE, "rb") as f:
            model = pickle.load(f)
        with open(_META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return model, meta
    return None, None


def calculate_ml(cfg: SmartSlideConfig) -> Optional[PriceResult]:
    model, meta = _load_model()
    if model is None:
        return None

    import pandas as pd

    features = cfg.to_feature_dict()
    X = pd.DataFrame([features])
    pred = model.predict(X)[0]
    r2 = meta.get("r2", 0)
    confidence = "wysoka" if r2 > 0.90 else "srednia" if r2 > 0.75 else "niska"
    return PriceResult(
        net_price=round(float(pred) * cfg.quantity, 2),
        source="ml",
        ml_confidence=f"{confidence} (R2={r2:.3f}, probek: {meta.get('samples', '?')})",
        breakdown={"Predykcja modelu ML (netto za szt.)": round(float(pred), 2)},
    )


def calculate(cfg: SmartSlideConfig, prefer_ml: bool = True) -> PriceResult:
    if prefer_ml:
        ml = calculate_ml(cfg)
        if ml:
            return ml
    return calculate_rules(cfg)


def list_datasets() -> List[Path]:
    return sorted(_DATASETS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)


def save_dataset(source_path: str, filename: str) -> Path:
    import shutil

    dest = _DATASETS_DIR / filename
    shutil.copy2(source_path, dest)
    return dest


def _build_pdf_choice_aliases() -> Dict[str, Dict[str, List[str]]]:
    return {
        "configuration": {
            CONFIGURATIONS[0]: ["2-skrzydl", "2 skrzydl", "dwuskrzydl", "2 kwat"],
            CONFIGURATIONS[1]: ["3-skrzydl", "3 skrzydl", "trzyskrzydl", "3 kwat"],
            CONFIGURATIONS[2]: ["4-skrzydl", "4 skrzydl", "czteroskrzydl", "4 kwat"],
            CONFIGURATIONS[3]: ["katowe 90", "kat 90", "narozne 90", "corner 90"],
        },
        "glass_type": {
            GLASS_TYPES[0]: ["float 4", "4mm", "4 mm"],
            GLASS_TYPES[1]: ["float 6", "6mm", "6 mm"],
            GLASS_TYPES[2]: ["zespol", "2x float", "pakiet 2-szyb", "2 szyb"],
            GLASS_TYPES[3]: ["niskoem", "low-e"],
            GLASS_TYPES[4]: ["przeciwslon", "solar"],
            GLASS_TYPES[5]: ["lamin"],
            GLASS_TYPES[6]: ["p2a", "bezpiecz"],
        },
        "color": {
            COLORS[0]: ["bial", "white"],
            COLORS[1]: ["braz"],
            COLORS[2]: ["antracyt", "anthracite"],
            COLORS[3]: ["zloty dab", "zloty"],
            COLORS[4]: ["orzech", "walnut"],
            COLORS[5]: ["czarn", "black"],
            COLORS[6]: ["szary", "grey", "gray"],
        },
        "threshold": {
            THRESHOLDS[0]: ["standard"],
            THRESHOLDS[1]: ["niskoprog"],
            THRESHOLDS[2]: ["bezprog"],
        },
        "hardware": {
            HARDWARE[0]: ["standard"],
            HARDWARE[1]: ["premium"],
            HARDWARE[2]: ["ekskluzy", "exclusive"],
        },
    }


def _detect_choice(text: str, field: str, default: str, aliases: Dict[str, Dict[str, List[str]]]) -> str:
    normalized = _normalize_text(text)
    for value, hints in aliases[field].items():
        if any(hint in normalized for hint in hints):
            return value
    return default


def _detect_flag(text: str, positive_aliases: List[str], negative_aliases: List[str], default: int) -> int:
    normalized = _normalize_text(text)
    if any(alias in normalized for alias in negative_aliases):
        return 0
    if any(alias in normalized for alias in positive_aliases):
        return 1
    return default


def _normalize_pdf_header(value: str, header_map: Dict[str, set]) -> Optional[str]:
    normalized = re.sub(r"[^a-z0-9_]", "", _normalize_text(value).replace(" ", "_"))
    for target, aliases in header_map.items():
        normalized_aliases = {re.sub(r"[^a-z0-9_]", "", _normalize_text(alias).replace(" ", "_")) for alias in aliases}
        if normalized in normalized_aliases:
            return target
    return None


def _parse_pdf_table_rows(
    lines: List[str],
    header_map: Dict[str, set],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    header_idx = None
    normalized_headers: List[str] = []

    for i, line in enumerate(lines):
        parts = [part.strip() for part in re.split(r"[;\t]| {2,}", line) if part.strip()]
        if len(parts) < 6:
            continue
        candidate = [_normalize_pdf_header(part, header_map) for part in parts]
        if sum(1 for col in candidate if col in REQUIRED_COLUMNS) >= 5:
            header_idx = i
            normalized_headers = [col or "" for col in candidate]
            break

    if header_idx is None:
        return rows

    for line in lines[header_idx + 1:]:
        parts = [part.strip() for part in re.split(r"[;\t]| {2,}", line) if part.strip()]
        if len(parts) < 6:
            continue
        record = {}
        for idx, value in enumerate(parts):
            if idx >= len(normalized_headers):
                continue
            col = normalized_headers[idx]
            if col:
                record[col] = value
        if not record:
            continue
        try:
            row = {
                "width_mm": int(_parse_decimal(record.get("width_mm", "0"))),
                "height_mm": int(_parse_decimal(record.get("height_mm", "0"))),
                "configuration": record.get("configuration", CONFIGURATIONS[0]),
                "glass_type": record.get("glass_type", GLASS_TYPES[0]),
                "color": record.get("color", COLORS[0]),
                "threshold": record.get("threshold", THRESHOLDS[0]),
                "hardware": record.get("hardware", HARDWARE[0]),
                "mosquito_net": _parse_bool(str(record.get("mosquito_net", "0"))),
                "installation": _parse_bool(str(record.get("installation", "0"))),
                "price_net": _parse_decimal(record.get("price_net", "0")),
            }
        except ValueError:
            continue
        if row["width_mm"] > 0 and row["height_mm"] > 0 and row["price_net"] > 0:
            rows.append(row)
    return rows


def _parse_pdf_fallback_rows(lines: List[str], raw_text: str) -> List[Dict[str, object]]:
    aliases = _build_pdf_choice_aliases()
    context = {
        "configuration": _detect_choice(raw_text, "configuration", CONFIGURATIONS[0], aliases),
        "glass_type": _detect_choice(raw_text, "glass_type", GLASS_TYPES[0], aliases),
        "color": _detect_choice(raw_text, "color", COLORS[0], aliases),
        "threshold": _detect_choice(raw_text, "threshold", THRESHOLDS[0], aliases),
        "hardware": _detect_choice(raw_text, "hardware", HARDWARE[0], aliases),
        "mosquito_net": _detect_flag(raw_text, ["siatka", "moskit"], ["bez siatki", "bez moskitiery"], 0),
        "installation": _detect_flag(raw_text, ["montaz"], ["bez montazu"], 0),
    }

    def update_context(text: str) -> None:
        for field, default in [
            ("configuration", CONFIGURATIONS[0]),
            ("glass_type", GLASS_TYPES[0]),
            ("color", COLORS[0]),
            ("threshold", THRESHOLDS[0]),
            ("hardware", HARDWARE[0]),
        ]:
            context[field] = _detect_choice(text, field, str(context.get(field, default)), aliases)
        context["mosquito_net"] = _detect_flag(
            text, ["siatka", "moskit"], ["bez siatki", "bez moskitiery"], int(context.get("mosquito_net", 0))
        )
        context["installation"] = _detect_flag(
            text, ["montaz"], ["bez montazu"], int(context.get("installation", 0))
        )

    rows: List[Dict[str, object]] = []
    seen = set()

    for line in lines:
        update_context(line)
        normalized = _normalize_text(line)
        if len(re.findall(r"\d", normalized)) < 5:
            continue

        size_match = re.search(r"(?P<w>\d{3,4})\s*[x×]\s*(?P<h>\d{3,4})", normalized)
        if size_match:
            width_mm = int(size_match.group("w"))
            height_mm = int(size_match.group("h"))
        else:
            dim_candidates = [int(match.group(0)) for match in re.finditer(r"\b\d{3,4}\b", normalized)]
            valid_dims = [n for n in dim_candidates if 600 <= n <= 8000]
            if len(valid_dims) < 2:
                continue
            width_mm, height_mm = valid_dims[0], valid_dims[1]

        price_candidates: List[float] = []
        for match in re.finditer(r"\d[\d\s]*[,.]?\d*", normalized):
            raw = match.group(0).strip()
            if not raw:
                continue
            try:
                value = _parse_decimal(raw)
            except ValueError:
                continue
            if value > 100 and int(round(value)) not in {width_mm, height_mm}:
                price_candidates.append(value)

        if not price_candidates:
            continue

        row = {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "configuration": str(context["configuration"]),
            "glass_type": str(context["glass_type"]),
            "color": str(context["color"]),
            "threshold": str(context["threshold"]),
            "hardware": str(context["hardware"]),
            "mosquito_net": int(context["mosquito_net"]),
            "installation": int(context["installation"]),
            "price_net": float(price_candidates[-1]),
        }
        key = (row["width_mm"], row["height_mm"], round(float(row["price_net"]), 2))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    return rows


def import_pdf_to_dataset(source_path: str, filename: Optional[str] = None) -> Tuple[Path, int]:
    """
    Parse a PDF price list/offer and convert recognized rows to dataset CSV.

    The parser first tries a header-based table extraction and then falls back
    to line parsing for PDFs that contain rows like "2000 x 2200 ... 7999,00".
    """
    import pandas as pd
    from pypdf import PdfReader

    src = Path(source_path)
    out_name = filename or f"{src.stem}_from_pdf.csv"
    if not out_name.endswith(".csv"):
        out_name = f"{Path(out_name).stem}.csv"
    out_path = _DATASETS_DIR / out_name

    text_parts: List[str] = []
    reader = PdfReader(str(src))
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    raw_text = "\n".join(text_parts)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    header_map = {
        "width_mm": {"width_mm", "width", "szerokosc", "szer_mm", "w"},
        "height_mm": {"height_mm", "height", "wysokosc", "h", "wys_mm"},
        "configuration": {"configuration", "konfiguracja", "uklad"},
        "glass_type": {"glass_type", "szklo", "pakiet"},
        "color": {"color", "kolor"},
        "threshold": {"threshold", "prog"},
        "hardware": {"hardware", "okucia"},
        "mosquito_net": {"mosquito_net", "mosquito", "siatka"},
        "installation": {"installation", "montaz"},
        "price_net": {"price_net", "cena_netto", "netto", "cena", "price"},
    }
    required = [
        "width_mm",
        "height_mm",
        "configuration",
        "glass_type",
        "color",
        "threshold",
        "hardware",
        "mosquito_net",
        "installation",
        "price_net",
    ]

    rows = _parse_pdf_table_rows(lines, header_map)
    if not rows:
        rows = _parse_pdf_fallback_rows(lines, raw_text)

    if not rows:
        raise ValueError("Nie udalo sie odczytac rekordow z PDF. Sprobuj PDF z czytelna tabela lub CSV/XLSX.")

    df = pd.DataFrame(rows, columns=required)
    df.to_csv(out_path, index=False, encoding="utf-8")
    return out_path, len(df)


def delete_dataset(filename: str) -> None:
    p = _DATASETS_DIR / filename
    if p.exists():
        p.unlink()


def load_dataset_preview(filename: str, rows: int = 10) -> Tuple[List[str], List[List]]:
    import pandas as pd

    p = _DATASETS_DIR / filename
    df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_excel(p)
    return list(df.columns), df.head(rows).values.tolist()


def _encode_df(df):
    import pandas as pd

    df = df.copy()
    df["area_m2"] = (df["width_mm"] / 1000) * (df["height_mm"] / 1000)

    for col, lst in [
        ("configuration", CONFIGURATIONS),
        ("glass_type", GLASS_TYPES),
        ("color", COLORS),
        ("threshold", THRESHOLDS),
        ("hardware", HARDWARE),
    ]:
        if df[col].dtype == object:
            mapping = {value: index for index, value in enumerate(lst)}
            df[col] = df[col].map(mapping).fillna(0).astype(int)

    for col in ("mosquito_net", "installation"):
        if df[col].dtype == object:
            df[col] = df[col].map(
                {"tak": 1, "nie": 0, "true": 1, "false": 0, "1": 1, "0": 0}
            ).fillna(0).astype(int)
        else:
            df[col] = df[col].fillna(0).astype(int)

    return df


def train(filenames: List[str]) -> Dict:
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score

    frames = []
    for fn in filenames:
        p = _DATASETS_DIR / fn
        df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_excel(p)
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Plik '{fn}' brakuje kolumn: {', '.join(sorted(missing))}")
        frames.append(df)

    data = pd.concat(frames, ignore_index=True).dropna(subset=["price_net"])
    data = _encode_df(data)

    X = data[FEATURE_COLS].fillna(0)
    y = data["price_net"].astype(float)

    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    cv_scores = cross_val_score(model, X, y, cv=min(5, len(data)), scoring="r2")
    model.fit(X, y)

    with open(_MODEL_FILE, "wb") as f:
        pickle.dump(model, f)

    meta = {
        "r2": round(float(cv_scores.mean()), 4),
        "r2_std": round(float(cv_scores.std()), 4),
        "samples": len(data),
        "datasets": filenames,
        "features": FEATURE_COLS,
        "importances": dict(zip(FEATURE_COLS, model.feature_importances_.tolist())),
    }
    with open(_META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return meta


def get_model_meta() -> Optional[dict]:
    if _META_FILE.exists():
        with open(_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def delete_model() -> None:
    for p in (_MODEL_FILE, _META_FILE):
        if p.exists():
            p.unlink()


def generate_sample_dataset(filename: str = "przykladowy_dataset.csv") -> Path:
    import pandas as pd

    random.seed(42)
    rows = []
    for _ in range(200):
        cfg = SmartSlideConfig(
            width_mm=random.choice(range(1500, 5000, 100)),
            height_mm=random.choice(range(1800, 2800, 100)),
            configuration=random.choice(CONFIGURATIONS),
            glass_type=random.choice(GLASS_TYPES),
            color=random.choice(COLORS),
            threshold=random.choice(THRESHOLDS),
            hardware=random.choice(HARDWARE),
            mosquito_net=random.choice([True, False]),
            installation=random.choice([True, False]),
            quantity=1,
        )
        result = calculate_rules(cfg)
        noise = 1 + random.uniform(-0.08, 0.08)
        row = cfg.to_feature_dict()
        row["width_mm"] = cfg.width_mm
        row["height_mm"] = cfg.height_mm
        row["configuration"] = cfg.configuration
        row["glass_type"] = cfg.glass_type
        row["color"] = cfg.color
        row["threshold"] = cfg.threshold
        row["hardware"] = cfg.hardware
        row["mosquito_net"] = int(cfg.mosquito_net)
        row["installation"] = int(cfg.installation)
        row["price_net"] = round(result.net_price * noise, 2)
        rows.append(row)

    cols = [
        "width_mm",
        "height_mm",
        "configuration",
        "glass_type",
        "color",
        "threshold",
        "hardware",
        "mosquito_net",
        "installation",
        "price_net",
    ]
    df = pd.DataFrame(rows)[cols]
    dest = _DATASETS_DIR / filename
    df.to_csv(dest, index=False)
    return dest


def analyze_pdf_offers(source_paths: List[str]) -> Dict[str, object]:
    converted: List[Dict[str, object]] = []
    failed: List[Dict[str, str]] = []
    dataset_names: List[str] = []

    for source_path in source_paths:
        pdf_path = Path(source_path)
        dataset_name = f"{pdf_path.stem}_from_pdf.csv"
        try:
            out_path, rows = import_pdf_to_dataset(source_path, dataset_name)
            converted.append(
                {
                    "source_pdf": pdf_path.name,
                    "dataset": out_path.name,
                    "rows": rows,
                }
            )
            dataset_names.append(out_path.name)
        except Exception as exc:
            failed.append({"source_pdf": pdf_path.name, "error": str(exc)})

    if not dataset_names:
        raise ValueError("Nie udalo sie zbudowac datasetu z zadnego PDF.")

    meta = train(dataset_names)
    report = {
        "pdf_files": len(source_paths),
        "converted_count": len(converted),
        "failed_count": len(failed),
        "total_rows": sum(int(item["rows"]) for item in converted),
        "converted": converted,
        "failed": failed,
        "model": meta,
    }

    report_path = _REPORTS_DIR / "last_pdf_offer_analysis.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def get_last_pdf_analysis_report() -> Optional[dict]:
    report_path = _REPORTS_DIR / "last_pdf_offer_analysis.json"
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
