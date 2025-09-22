from dataclasses import dataclass, field
from typing import List, Tuple, Optional

ALL_PRODUCTS = [
    "Lighteruv1", "Lighteruv2", "LighterMax", "LighterMini",
    "TorchMini", "TorchPro", "CandlePro", "MatchStick",
    "SparkLite", "Product2", "Product3"
]
MM_TO_PX = 3  # simple scale mm→px for drawing
APP_TITLE = "Zyntra 1.0"


@dataclass
class AppState:
    saved_search: str = ""
    saved_product: str = "Lighteruv1"
    order_from: str = "13111"
    order_to: str = "13112"

    # Screen 1
    is_sticker: Optional[bool] = None
    sku: str = ""
    pkg_x: str = ""
    pkg_y: str = ""
    major_variations: int = 0
    variation_design_counts: List[int] = field(default_factory=list)
    font_variations_total: int = 0
    font_names: List[str] = field(default_factory=list)
    font_uploaded: List[bool] = field(default_factory=list)
    major_sizes: List[Tuple[str, str]] = field(default_factory=list)

    # Sheet summary / layout
    sheet_total: int = 0
    sheet_per_major: List[int] = field(default_factory=list)
    ai_arrange: bool = False

state = AppState()