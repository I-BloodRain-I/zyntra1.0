import json
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass, field, asdict

# ALL_PRODUCTS = [
#     "Lighteruv1", "Lighteruv2", "LighterMax", "LighterMini",
#     "TorchMini", "TorchPro", "CandlePro", "MatchStick",
#     "SparkLite", "Product2", "Product3"
# ]
MM_TO_PX = 1  # simple scale mm→px for drawing
APP_TITLE = "Zyntra 1.0"

INTERNAL_PATH = Path.cwd() / "_internal"
INTERNAL_PATH.mkdir(exist_ok=True)

IMAGES_PATH   = INTERNAL_PATH / "images"
FONTS_PATH    = INTERNAL_PATH / "fonts"
PRODUCTS_PATH = INTERNAL_PATH / "products"
PRODUCTS_PATH.mkdir(exist_ok=True)

ALL_PRODUCTS = [f.stem for f in INTERNAL_PATH.glob("products/*.json") if f.is_file()]


@dataclass
class AppState:
    saved_search: str = "Lighteruv1"
    is_sticker: Optional[bool] = None
    saved_product: str = ""
    order_from: str = "13111"
    order_to: str = "13112"

    # Screen 1
    sku: str = ""
    sku_name: str = ""
    pkg_x: str = ""
    pkg_y: str = ""
    major_variations: int = 1
    # variation_design_counts: List[int] = field(default_factory=list)
    variation_design_counts: List[int] = field(default_factory=lambda: [3])
    font_variations_total: int = 2
    # (font_name, file_path)
    uploaded_fonts: List[Tuple[str, str]] = field(default_factory=list)
    # (x, y, file_path)
    # major_sizes: List[Tuple[str, str, str]] = field(default_factory=list)
    major_sizes: List[Tuple[str, str, str]] = field(default_factory=lambda: [("5", "8", "text.svg")])

    # Sheet summary / layout
    sheet_total: int = 0
    sheet_per_major: List[int] = field(default_factory=list)
    ai_arrange: bool = False

    # Non-sticker: number of image objects on canvas when proceeding
    nonsticker_image_count: int = 0

    # Background processing status for non-blocking generation
    is_processing: bool = False
    processing_message: str = ""
    is_failed: bool = False
    error_message: str = ""

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