from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class CanvasObject:
    """Encapsulates state for an item placed on the canvas.

    Fields store geometry in millimeters relative to the jig: top-left for
    rectangles/images and center for text items. Pixel conversion and zooming
    are handled by the screen.
    """

    type: str  # "rect", "image", or "text"

    # Geometry in millimeters (top-left for rect/image, center for text)
    x_mm: float = 0.0
    y_mm: float = 0.0
    w_mm: float = 0.0  # width for rect/image; ignored for text
    h_mm: float = 0.0  # height for rect/image; ignored for text

    # Rendering/storage
    path: Optional[str] = None  # for kind == "image"
    outline: Optional[str] = None  # for kind == "rect"
    default_fill: Optional[str] = None  # for kind == "text"

    # Canvas linkage
    label_id: Optional[int] = None  # text item inside rect, or text id for text items
    border_id: Optional[int] = None  # selection border for images
    canvas_id: Optional[int] = None  # primary canvas object id

    # Runtime image caches (Pillow/tk)
    pil: Any = field(default=None)   # PIL.Image.Image
    photo: Any = field(default=None) # tk.PhotoImage

    # Stacking order indicator (optional, for future z-ordering)
    z: int = 0

    def is_text_rect(self) -> bool:
        return self.type == "rect" and str(self.outline or "") == "#17a24b"

    # Minimal dict-like API for compatibility during refactor
    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        setattr(self, key, value)


