from __future__ import annotations

import os
import math
import logging
from typing import Optional

import tkinter as tk

from src.core import MM_TO_PX
from src.canvas.object import CanvasObject
from src.utils import svg_to_png

logger = logging.getLogger(__name__)


class ImageManager:
    """Create and render images, including rotation-aware placement and sizing."""

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen

    def rotated_bounds_px(self, w_px: int, h_px: int, angle_deg: float) -> tuple[int, int]:
        try:
            a = math.radians(float(angle_deg) % 360.0)
            ca = abs(math.cos(a))
            sa = abs(math.sin(a))
            bw = int(round(w_px * ca + h_px * sa))
            bh = int(round(w_px * sa + h_px * ca))
            return max(1, bw), max(1, bh)
        except Exception:
            return max(1, int(w_px)), max(1, int(h_px))

    def rotated_bounds_mm(self, w_mm: float, h_mm: float, angle_deg: float) -> tuple[float, float]:
        try:
            a = math.radians(float(angle_deg) % 360.0)
            ca = abs(math.cos(a))
            sa = abs(math.sin(a))
            bw = (w_mm * ca) + (h_mm * sa)
            bh = (w_mm * sa) + (h_mm * ca)
            return float(max(0.0, bw)), float(max(0.0, bh))
        except Exception:
            return float(max(0.0, w_mm)), float(max(0.0, h_mm))

    def render_photo(self, meta: dict, w_px: int, h_px: int) -> Optional[tk.PhotoImage]:
        # Returns a tk.PhotoImage of requested size; stores reference on meta to avoid GC
        if w_px < 1 or h_px < 1:
            return None
        path = meta.get("path")
        if not path or not os.path.exists(path):
            return None
        # Optional PIL (Pillow) import for high-quality image scaling
        try:
            from PIL import Image, ImageTk  # type: ignore
        except Exception:
            Image = None  # type: ignore
            ImageTk = None  # type: ignore

        # SVG handling via svg_to_png → PIL → ImageTk
        try:
            ext = os.path.splitext(str(path))[1].lower()
        except Exception:
            ext = ""
        if ext == ".svg" and Image is not None and ImageTk is not None:
            try:
                pil = svg_to_png(str(path), width=int(w_px), height=int(h_px), device_pixel_ratio=1.0)
                try:
                    pil = pil.convert("RGBA")
                except Exception as e:
                    logger.exception(f"Failed to convert SVG image to RGBA: {e}")
                try:
                    angle = float(meta.get("angle", 0.0) or 0.0)
                except Exception:
                    angle = 0.0
                if abs(angle) > 1e-6:
                    pil = pil.rotate(-angle, expand=True, resample=Image.BICUBIC)
                photo = ImageTk.PhotoImage(pil)
                meta["photo"] = photo
                return photo
            except Exception as e:
                logger.exception(f"Failed to rasterize SVG with svg_to_png: {e}")
        # Try high-quality resize via PIL for raster formats
        try:
            if Image is not None and ImageTk is not None:
                pil = meta.get("pil")
                if pil is None:
                    pil = Image.open(path)
                    meta["pil"] = pil
                # Ensure RGBA to preserve transparency during rotation
                try:
                    pil = pil.convert("RGBA")
                except Exception as e:
                    logger.exception(f"Failed to convert raster image to RGBA: {e}")
                resized = pil.resize((int(w_px), int(h_px)), Image.LANCZOS)
                # Apply rotation if any (clockwise degrees)
                angle = 0.0
                try:
                    angle = float(meta.get("angle", 0.0) or 0.0)
                except Exception:
                    angle = 0.0
                if abs(angle) > 1e-6:
                    rotated = resized.rotate(-angle, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
                    resized = rotated
                photo = ImageTk.PhotoImage(resized)
                meta["photo"] = photo
                return photo
        except Exception as e:
            logger.exception(f"Failed to render photo with PIL: {e}")
        # Fallback to tk.PhotoImage (best-effort; may not scale exactly)
        try:
            photo = tk.PhotoImage(file=path)
            meta["photo"] = photo
            return photo
        except Exception:
            return None

    def create_image_item(self, path: str, w_mm: float, h_mm: float, x_mm: Optional[float] = None, y_mm: Optional[float] = None) -> None:
        # place at the center of current viewport similar to placeholders
        cw = max(1, self.s.canvas.winfo_width())
        ch = max(1, self.s.canvas.winfo_height())
        cx = self.s.canvas.canvasx(cw // 2)
        cy = self.s.canvas.canvasy(ch // 2)
        # snap width/height to integer millimeters
        qw_mm = self.s._snap_mm(w_mm)
        qh_mm = self.s._snap_mm(h_mm)
        base_w = float(qw_mm) * MM_TO_PX
        base_h = float(qh_mm) * MM_TO_PX
        scaled_w = int(round(base_w * self.s._zoom))
        scaled_h = int(round(base_h * self.s._zoom))
        # Ensure within jig; compute snapped top-left mm
        ox = self.s._item_outline_half_px()
        oy = self.s._item_outline_half_px()
        jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
        if x_mm is None:
            x_mm = (cx - scaled_w / 2 - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
        if y_mm is None:
            y_mm = (cy - scaled_h / 2 - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
        sx_mm = self.s._snap_mm(x_mm)
        sy_mm = self.s._snap_mm(y_mm)
        new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self.s._zoom
        new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self.s._zoom
        # Build meta and render
        meta = CanvasObject(
            type="image",
            path=path,
            w_mm=float(qw_mm),
            h_mm=float(qh_mm),
            x_mm=float(sx_mm),
            y_mm=float(sy_mm),
        )
        photo = self.render_photo(meta, scaled_w, scaled_h)
        if photo is None:
            # fallback to placeholder if render failed
            self.s.create_placeholder(os.path.basename(path), qw_mm, qh_mm)
            return
        # For rotation, use visual top-left of rotated bounds
        angle = 0.0
        try:
            angle = float(meta.get("angle", 0.0) or 0.0)
        except Exception:
            angle = 0.0
        bw, bh = self.rotated_bounds_px(scaled_w, scaled_h, angle)
        place_left = new_left
        place_top = new_top
        img_id = self.s.canvas.create_image(place_left, place_top, image=photo, anchor="nw")
        meta.canvas_id = img_id
        # assign next z
        max_z = max(int(m.get("z", 0)) for _cid, m in self.s._items.items()) if self.s._items else 0
        meta["z"] = int(max_z + 1)
        self.s._items[img_id] = meta
        self.s.selection.select(img_id)
        self.s._update_scrollregion()
        self.s.selection._reorder_by_z()


