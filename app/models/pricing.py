from dataclasses import dataclass, field
from typing import Optional

# Smart-slide configurations
CONFIGURATIONS = ["2-skrzydłowe", "3-skrzydłowe", "4-skrzydłowe", "kątowe 90°"]
GLASS_TYPES = ["float 4mm", "float 6mm", "2x float (zespolone)", "niskoemisyjne", "przeciwsłoneczne", "laminowane", "P2A bezpieczne"]
COLORS = ["biały", "brązowy", "antracyt", "złoty dąb", "orzech", "czarny", "szary"]
THRESHOLDS = ["standardowy", "niskoprogowy", "bezprogowy"]
HARDWARE = ["standard", "premium", "ekskluzywny"]


@dataclass
class SmartSlideConfig:
    width_mm: int = 2000
    height_mm: int = 2200
    configuration: str = "2-skrzydłowe"
    glass_type: str = "niskoemisyjne"
    color: str = "biały"
    threshold: str = "standardowy"
    hardware: str = "standard"
    mosquito_net: bool = False
    installation: bool = False
    quantity: int = 1

    @property
    def area_m2(self) -> float:
        return (self.width_mm / 1000) * (self.height_mm / 1000)

    def to_feature_dict(self) -> dict:
        return {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "area_m2": self.area_m2,
            "configuration": CONFIGURATIONS.index(self.configuration) if self.configuration in CONFIGURATIONS else 0,
            "glass_type": GLASS_TYPES.index(self.glass_type) if self.glass_type in GLASS_TYPES else 0,
            "color": COLORS.index(self.color) if self.color in COLORS else 0,
            "threshold": THRESHOLDS.index(self.threshold) if self.threshold in THRESHOLDS else 0,
            "hardware": HARDWARE.index(self.hardware) if self.hardware in HARDWARE else 0,
            "mosquito_net": int(self.mosquito_net),
            "installation": int(self.installation),
        }


@dataclass
class PriceResult:
    net_price: float = 0.0
    vat_rate: float = 0.23
    source: str = "rules"      # "rules" or "ml"
    ml_confidence: str = ""
    breakdown: dict = field(default_factory=dict)

    @property
    def vat_amount(self) -> float:
        return self.net_price * self.vat_rate

    @property
    def gross_price(self) -> float:
        return self.net_price * (1 + self.vat_rate)
