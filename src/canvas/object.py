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

    type: str  # "rect", "image", "text", "slot", "major", or "barcode"

    # Geometry in millimeters (top-left for rect/image, center for text)
    x_mm: float = 0.0
    y_mm: float = 0.0
    w_mm: float = 0.0  # width for rect/image; ignored for text
    h_mm: float = 0.0  # height for rect/image; ignored for text

    # Rendering/storage
    path: Optional[str] = None  # for kind == "image"
    outline: Optional[str] = None  # for kind == "rect"
    default_fill: Optional[str] = None  # for kind == "text"
    # Optional mask path (PNG) for image items; persisted to JSON
    mask_path: Optional[str] = None

    # Canvas linkage
    label_id: Optional[int] = None  # text item inside rect, or text id for text items
    border_id: Optional[int] = None  # selection border for images
    canvas_id: Optional[int] = None  # primary canvas object id

    # Runtime image caches (Pillow/tk)
    pil: Any = field(default=None)   # PIL.Image.Image
    photo: Any = field(default=None) # tk.PhotoImage

    # Stacking order indicator (optional, for future z-ordering)
    z: int = 0

    # Rotation angle in degrees (clockwise), for type in {"rect", "image"}
    angle: float = 0.0

    # Optional human-readable name assigned via UI input
    amazon_label: str = ""
    # Optional flags controlled by UI
    is_options: bool = False
    is_static: bool = False
    
    # Export file assignment (default "File 1", ignored for slots and majors)
    export_file: str = "File 1"
    
    # Custom images for image objects (name -> path dict and selected name)
    custom_images: dict = field(default_factory=dict)
    custom_image: str = ""

    def is_text_rect(self) -> bool:
        # Text rects have green outline; barcode has black outline but should not be treated as text rect
        """Return True when this object represents a 'text rectangle'.

        Text rectangles are represented as rectangle objects with a specific
        outline color ("#17a24b" in the application's convention). Barcodes or
        other rect types should not be treated as text rects; callers use this
        predicate to enable text-specific UI controls and sizing behavior.
        """
        return self.type == "rect" and str(self.outline or "") == "#17a24b"

    # Minimal dict-like API for compatibility during refactor
    def get(self, key: str, default=None):
        """Dictionary-like get(key, default) accessor for compatibility.

        This mirrors behavior of a mapping to ease transition from older
        code that used dict meta objects. It returns the attribute value if
        present or the provided default otherwise.
        """
        return getattr(self, key, default)

    def __getitem__(self, key: str):
        """Allow bracket access (obj[key]) to read attributes.

        Raises AttributeError if the attribute does not exist (matching
        previous dict-like expectations where KeyError would be analogous).
        """
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        """Allow bracket assignment (obj[key] = value) to set attributes.

        This provides a minimal dict-like interface used in various legacy
        call sites while keeping the benefits of a typed dataclass.
        """
        setattr(self, key, value)


