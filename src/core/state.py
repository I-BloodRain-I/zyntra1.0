import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass, field, asdict


MM_TO_PX = 1  # simple scale mm→px for drawing
APP_TITLE = "Zyntra 1.0"

INTERNAL_PATH = Path.cwd() / "_internal"
INTERNAL_PATH.mkdir(exist_ok=True)

IMAGES_PATH   = INTERNAL_PATH / "images"
FONTS_PATH    = INTERNAL_PATH / "fonts"
MODEL_PATH    = INTERNAL_PATH / "u2net.onnx"
PRODUCTS_PATH = INTERNAL_PATH / "products"
PRODUCTS_PATH.mkdir(exist_ok=True)
LOGS_PATH     = INTERNAL_PATH / "logs"
LOGS_PATH.mkdir(exist_ok=True)
INPUT_PATH    = Path.cwd() / "inputs"
# INPUT_PATH.mkdir(exist_ok=True)
OUTPUT_PATH   = Path.cwd() / "outputs"
OUTPUT_PATH.mkdir(exist_ok=True)

ENV_PATH = INTERNAL_PATH / "env"
CACHE_PATH = INTERNAL_PATH / "cache.json"

ALL_PRODUCTS = [f.stem for f in INTERNAL_PATH.glob("products/*.json") if f.is_file()]


@dataclass
class AppState:
    saved_search: str = "Lighteruv1"
    is_sticker: Optional[bool] = None
    saved_product: str = ""
    order_from: str = "0"
    order_to: str = "0"

    dropbox_from = datetime.now()
    dropbox_to = datetime(day=1, month=1, year=datetime.now().year + 1)

    # Screen 1
    asins: List[Tuple[str, int]] = field(default_factory=list)
    prev_sku_name: str = ""
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
    is_cancelled: bool = False
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