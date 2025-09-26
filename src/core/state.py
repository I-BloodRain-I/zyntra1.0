import json
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass, field, asdict

ALL_PRODUCTS = [
    "Lighteruv1", "Lighteruv2", "LighterMax", "LighterMini",
    "TorchMini", "TorchPro", "CandlePro", "MatchStick",
    "SparkLite", "Product2", "Product3"
]
MM_TO_PX = 1  # simple scale mm→px for drawing
APP_TITLE = "Zyntra 1.0"
IMAGES_PATH = Path.cwd() / "images"


@dataclass
class AppState:
    saved_search: str = "Lighteruv1"
    saved_product: str = ""
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

    # Non-sticker: number of image objects on canvas when proceeding
    nonsticker_image_count: int = 0

state = AppState()


def save_state(path: str | Path) -> None:
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(asdict(state), f, ensure_ascii=False, indent=2)


def load_state(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False
    for k, v in data.items():
        if hasattr(state, k):
            setattr(state, k, v)
    return True