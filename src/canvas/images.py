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

    def rotated_bounds_px(self, w_px: float, h_px: float, angle_deg: float) -> tuple[float, float]:
        try:
            a = math.radians(float(angle_deg) % 360.0)
            ca = abs(math.cos(a))
            sa = abs(math.sin(a))
            bw = (float(w_px) * ca) + (float(h_px) * sa)
            bh = (float(w_px) * sa) + (float(h_px) * ca)
            return max(1.0, float(bw)), max(1.0, float(bh))
        except Exception:
            return max(1.0, float(w_px)), max(1.0, float(h_px))

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
                # Apply mask selection if provided (treat near-transparent as fully transparent)
                try:
                    mpath = str(meta.get("mask_path", "") or "")
                    if mpath and os.path.exists(mpath):
                        mimg = Image.open(mpath).convert("RGBA")
                        mimg = mimg.resize((int(w_px), int(h_px)), Image.LANCZOS)
                        mask_alpha = mimg.split()[-1]
                        # Keep-map for TRANSPARENT areas: 255 where alpha <= threshold
                        thr = 12
                        keep = mask_alpha.point(lambda a: 255 if int(a) <= thr else 0, "L")
                        try:
                            from PIL import ImageChops as _ImageChops, ImageFilter as _ImageFilter  # type: ignore
                        except Exception:
                            _ImageChops = None  # type: ignore
                            _ImageFilter = None  # type: ignore
                        # Slightly dilate keep region to cover anti-aliased edges
                        try:
                            if _ImageFilter is not None:
                                keep = keep.filter(_ImageFilter.MaxFilter(3))
                        except Exception:
                            raise
                        if _ImageChops is not None:
                            orig_a = pil.split()[-1]
                            new_a = _ImageChops.multiply(orig_a, keep)
                            pil.putalpha(new_a)
                        else:
                            pil.putalpha(keep)
                except Exception:
                    logger.exception("Failed to apply mask selection to SVG rasterization")
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
                # Apply mask selection if provided (treat near-transparent as fully transparent)
                try:
                    mpath = str(meta.get("mask_path", "") or "")
                    if mpath and os.path.exists(mpath):
                        mimg = Image.open(mpath).convert("RGBA")
                        mimg = mimg.resize((int(w_px), int(h_px)), Image.LANCZOS)
                        mask_alpha = mimg.split()[-1]
                        thr = 12
                        # Keep transparent areas
                        keep = mask_alpha.point(lambda a: 255 if int(a) <= thr else 0, "L")
                        try:
                            from PIL import ImageChops as _ImageChops, ImageFilter as _ImageFilter  # type: ignore
                        except Exception:
                            _ImageChops = None  # type: ignore
                            _ImageFilter = None  # type: ignore
                        try:
                            if _ImageFilter is not None:
                                keep = keep.filter(_ImageFilter.MaxFilter(3))
                        except Exception:
                            raise
                        if _ImageChops is not None:
                            orig_a = resized.split()[-1]
                            new_a = _ImageChops.multiply(orig_a, keep)
                            resized.putalpha(new_a)
                        else:
                            resized.putalpha(keep)
                except Exception as e:
                    logger.exception(f"Failed to apply mask selection: {e}")
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
        # place at the center of selected major if available; otherwise viewport center
        cw = max(1, self.s.canvas.winfo_width())
        ch = max(1, self.s.canvas.winfo_height())
        cx = self.s.canvas.canvasx(cw // 2)
        cy = self.s.canvas.canvasy(ch // 2)
        # keep fractional millimeters
        qw_mm = self.s._snap_mm(w_mm)
        qh_mm = self.s._snap_mm(h_mm)
        base_w = float(qw_mm) * MM_TO_PX
        base_h = float(qh_mm) * MM_TO_PX
        scaled_w = float(base_w * self.s._zoom)
        scaled_h = float(base_h * self.s._zoom)
        # Compute initial placement snapped to grid and clamped inside selected major if bound
        ox = self.s._item_outline_half_px()
        oy = self.s._item_outline_half_px()
        jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
        clamp_left, clamp_top, clamp_right, clamp_bottom = jx0, jy0, jx1, jy1
        try:
            owner_try = str(getattr(self.s, "major_name").get()).strip()
        except Exception:
            owner_try = ""
        # Prefer explicit x_mm/y_mm if provided; otherwise derive from center of clamp rect
        if owner_try and hasattr(self.s, "_majors") and owner_try in getattr(self.s, "_majors", {}):
            try:
                mid = int(self.s._majors.get(owner_try) or 0)
            except Exception:
                mid = 0
            if mid:
                try:
                    mb = self.s.canvas.bbox(mid)
                except Exception:
                    mb = None
                if mb:
                    clamp_left, clamp_top, clamp_right, clamp_bottom = float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3])
                    cx = (clamp_left + clamp_right) / 2.0
                    cy = (clamp_top + clamp_bottom) / 2.0
        if x_mm is None or y_mm is None:
            desired_left = cx - scaled_w / 2.0
            desired_top = cy - scaled_h / 2.0
            desired_left = max(clamp_left, min(desired_left, clamp_right - scaled_w))
            desired_top = max(clamp_top, min(desired_top, clamp_bottom - scaled_h))
            x_mm = (desired_left - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            y_mm = (desired_top - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
        sx_mm = self.s._snap_mm(float(x_mm))
        sy_mm = self.s._snap_mm(float(y_mm))
        new_left = (jx0 + ox) + float(sx_mm) * MM_TO_PX * self.s._zoom
        new_top = (jy0 + oy) + float(sy_mm) * MM_TO_PX * self.s._zoom
        # Build meta and render
        meta = CanvasObject(
            type="image",
            path=path,
            w_mm=float(qw_mm),
            h_mm=float(qh_mm),
            x_mm=float(sx_mm),
            y_mm=float(sy_mm),
        )
        # Tag ownership: prefer the major under initial placement; fallback to selected major
        try:
            owner_hit = ""
            try:
                cx0 = float(new_left)
                cy0 = float(new_top)
                cx1 = float(new_left + scaled_w)
                cy1 = float(new_top + scaled_h)
                center_x = (cx0 + cx1) / 2.0
                center_y = (cy0 + cy1) / 2.0
            except Exception:
                center_x = float(new_left)
                center_y = float(new_top)
            if hasattr(self.s, "_majors"):
                for nm, rid in getattr(self.s, "_majors", {}).items():
                    try:
                        mb = self.s.canvas.bbox(rid)
                    except Exception:
                        mb = None
                    if not mb:
                        continue
                    mx0, my0, mx1, my1 = float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3])
                    if center_x >= mx0 and center_x <= mx1 and center_y >= my0 and center_y <= my1:
                        owner_hit = str(nm)
                        break
            owner_sel = ""
            try:
                owner_sel = str(getattr(self.s, "major_name").get()).strip()
            except Exception:
                owner_sel = ""
            # Prioritize explicitly selected major over hit-detected one to avoid overlap issues
            final_owner = owner_sel or owner_hit
            if final_owner:
                meta["owner_major"] = final_owner
        except Exception:
            raise
        photo = self.render_photo(meta, max(1, int(scaled_w)), max(1, int(scaled_h)))
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
        bw, bh = self.rotated_bounds_px(float(scaled_w), float(scaled_h), angle)
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
        # Ensure only current major's items are visible
        if hasattr(self.s, "_refresh_major_visibility"):
            try:
                self.s._refresh_major_visibility()
            except Exception:
                raise


