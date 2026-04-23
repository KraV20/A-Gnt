"""
Pricing service for smart-slide windows.

Two modes:
  1. Rule-based  – always available, uses parametric price table
  2. ML-based    – available after training on uploaded dataset (scikit-learn RandomForest)
"""
import json
import pickle
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from app.config import _BASE_DIR
from app.models.pricing import (
    SmartSlideConfig, PriceResult,
    CONFIGURATIONS, GLASS_TYPES, COLORS, THRESHOLDS, HARDWARE,
)

_PRICING_DIR = _BASE_DIR / "pricing"
_PRICING_DIR.mkdir(exist_ok=True)

_MODEL_FILE = _PRICING_DIR / "model.pkl"
_META_FILE  = _PRICING_DIR / "model_meta.json"
_DATASETS_DIR = _PRICING_DIR / "datasets"
_DATASETS_DIR.mkdir(exist_ok=True)

# ── Rule-based pricing ────────────────────────────────────────────────────────

_BASE_PRICE_PER_M2 = 1200.0   # PLN netto za m²

_GLASS_FACTORS = {
    "float 4mm":            1.00,
    "float 6mm":            1.10,
    "2x float (zespolone)": 1.30,
    "niskoemisyjne":        1.45,
    "przeciwsłoneczne":     1.55,
    "laminowane":           1.65,
    "P2A bezpieczne":       1.80,
}
_COLOR_SURCHARGE = {
    "biały":      0,
    "brązowy":    150,
    "antracyt":   250,
    "złoty dąb":  200,
    "orzech":     200,
    "czarny":     300,
    "szary":      200,
}
_THRESHOLD_SURCHARGE = {
    "standardowy":  0,
    "niskoprogowy": 400,
    "bezprogowy":   800,
}
_HARDWARE_SURCHARGE = {
    "standard":    0,
    "premium":     600,
    "ekskluzywny": 1400,
}
_CONFIG_FACTOR = {
    "2-skrzydłowe": 1.00,
    "3-skrzydłowe": 1.35,
    "4-skrzydłowe": 1.65,
    "kątowe 90°":   1.90,
}


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
            "Podstawa (powierzchnia × stawka × szkło × konfiguracja)": round(base * cfg.quantity, 2),
            "Kolor":       color_s * cfg.quantity,
            "Próg":        threshold_s * cfg.quantity,
            "Okucia":      hardware_s * cfg.quantity,
            "Siatka":      mosquito_s * cfg.quantity,
            "Montaż":      install_s,
        },
    )


# ── ML model ─────────────────────────────────────────────────────────────────

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
    confidence = "wysoka" if r2 > 0.90 else "średnia" if r2 > 0.75 else "niska"
    return PriceResult(
        net_price=round(float(pred) * cfg.quantity, 2),
        source="ml",
        ml_confidence=f"{confidence} (R²={r2:.3f}, próbek: {meta.get('samples', '?')})",
        breakdown={"Predykcja modelu ML (netto za szt.)": round(float(pred), 2)},
    )


def calculate(cfg: SmartSlideConfig, prefer_ml: bool = True) -> PriceResult:
    if prefer_ml:
        ml = calculate_ml(cfg)
        if ml:
            return ml
    return calculate_rules(cfg)


# ── Dataset management ────────────────────────────────────────────────────────

def list_datasets() -> List[Path]:
    return sorted(_DATASETS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)


def save_dataset(source_path: str, filename: str) -> Path:
    import shutil
    dest = _DATASETS_DIR / filename
    shutil.copy2(source_path, dest)
    return dest


def delete_dataset(filename: str) -> None:
    p = _DATASETS_DIR / filename
    if p.exists():
        p.unlink()


def load_dataset_preview(filename: str, rows: int = 10) -> Tuple[List[str], List[List]]:
    """Returns (columns, rows) for preview."""
    import pandas as pd
    p = _DATASETS_DIR / filename
    df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_excel(p)
    return list(df.columns), df.head(rows).values.tolist()


# ── Model training ────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {
    "width_mm", "height_mm", "configuration", "glass_type",
    "color", "threshold", "hardware", "mosquito_net", "installation", "price_net",
}

FEATURE_COLS = [
    "width_mm", "height_mm", "area_m2",
    "configuration", "glass_type", "color",
    "threshold", "hardware", "mosquito_net", "installation",
]


def _encode_df(df):
    import pandas as pd
    df = df.copy()
    df["area_m2"] = (df["width_mm"] / 1000) * (df["height_mm"] / 1000)

    for col, lst in [
        ("configuration", CONFIGURATIONS),
        ("glass_type",    GLASS_TYPES),
        ("color",         COLORS),
        ("threshold",     THRESHOLDS),
        ("hardware",      HARDWARE),
    ]:
        if df[col].dtype == object:
            mapping = {v: i for i, v in enumerate(lst)}
            df[col] = df[col].map(mapping).fillna(0).astype(int)

    for col in ("mosquito_net", "installation"):
        if df[col].dtype == object:
            df[col] = df[col].map({"tak": 1, "nie": 0, "true": 1, "false": 0,
                                   "1": 1, "0": 0}).fillna(0).astype(int)
        else:
            df[col] = df[col].fillna(0).astype(int)

    return df


def train(filenames: List[str]) -> Dict:
    """Train RandomForest on selected datasets. Returns metrics dict."""
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    frames = []
    for fn in filenames:
        p = _DATASETS_DIR / fn
        df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_excel(p)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Plik '{fn}' brakuje kolumn: {', '.join(missing)}")
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
    """Generate a sample CSV dataset for reference."""
    import pandas as pd
    import random
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
        # add ±8% noise
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

    cols = ["width_mm", "height_mm", "configuration", "glass_type", "color",
            "threshold", "hardware", "mosquito_net", "installation", "price_net"]
    df = pd.DataFrame(rows)[cols]
    dest = _DATASETS_DIR / filename
    df.to_csv(dest, index=False)
    return dest
