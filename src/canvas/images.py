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
        """Compute axis-aligned bounding box of a rotated rectangle in pixels.

        Args:
            w_px: Width of the source rectangle in pixels.
            h_px: Height of the source rectangle in pixels.
            angle_deg: Rotation angle in degrees (clockwise).

        Returns:
            Tuple of (width_px, height_px) for the smallest axis-aligned box
            that fully contains the rotated rectangle. Values are at least 1.0.
        """
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
        """Compute axis-aligned bounding box of a rotated rectangle in mm.

        Same computation as rotated_bounds_px but works with millimeter units.
        Returns a tuple (width_mm, height_mm).
        """
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
        """Return a tk.PhotoImage for the given meta.path scaled to (w_px,h_px).

        The function prefers Pillow (high-quality resizing and rotation) and
        supports SVG source rendering via svg_to_png. The returned PhotoImage
        is stored on the meta dict under 'photo' to prevent garbage-collection
        by Tkinter.
        """
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
                # Mirror is a per-ASIN export flag; do NOT alter canvas rendering here
                # Apply mask using clip (cut) logic: keep pixels only where mask alpha > 0
                try:
                    mpath = str(meta.get("mask_path", "") or "")
                    if mpath and os.path.exists(mpath):
                        pil = self._apply_mask_clip(pil, mpath, int(w_px), int(h_px))
                except Exception:
                    logger.exception("Failed to apply window-based mask to SVG rasterization")
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
                # Mirror is a per-ASIN export flag; do NOT alter canvas rendering here
                # Apply mask using clip (cut) logic: keep pixels only where mask alpha > 0
                try:
                    mpath = str(meta.get("mask_path", "") or "")
                    if mpath and os.path.exists(mpath):
                        resized = self._apply_mask_clip(resized, mpath, int(w_px), int(h_px))
                except Exception as e:
                    logger.exception(f"Failed to apply window-based mask: {e}")
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
        """Create an image item on the canvas and add its metadata.

        Args:
            path: Path to source image file (raster or SVG).
            w_mm, h_mm: Desired size in millimeters.
            x_mm, y_mm: Optional position in millimeters. If omitted the image
                is placed at the viewport center or in the currently selected
                major.

        The method renders the image at current zoom, creates the canvas item,
        and registers a CanvasObject in screen._items.
        """
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
        # Initialize empty custom image assignment and empty custom images dict
        meta["custom_image"] = ""
        meta["custom_images"] = {}
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
        
        # Auto-save to current ASIN after adding new object
        try:
            if hasattr(self.s, '_save_current_asin_objects'):
                logger.debug(f"[OBJECT_CREATE] Image created: id={img_id}, path={os.path.basename(path)}, x={sx_mm:.2f}, y={sy_mm:.2f} - auto-saving to ASIN")
                self.s._save_current_asin_objects()
        except Exception:
            pass
        self.s.selection.select(img_id)
        self.s._update_scrollregion()
        self.s.selection._reorder_by_z()
        # Ensure only current major's items are visible
        if hasattr(self.s, "_refresh_major_visibility"):
            try:
                self.s._refresh_major_visibility()
            except Exception:
                raise

    def _apply_mask_window_compose(self, content_rgba, mask_path: str, target_w: int, target_h: int):
        """Apply mask like order_range._apply_mask: use largest transparent window in mask
        to place cover-fitted content. Returns RGBA image of size (target_w, target_h).
        """
        try:
            from PIL import Image
            import numpy as np  # type: ignore
        except Exception:
            return content_rgba

        try:
            mask_img = Image.open(mask_path).convert("RGBA")
        except Exception:
            return content_rgba

        # Resize mask to target using nearest to preserve edges
        if mask_img.size != (int(target_w), int(target_h)):
            try:
                mask_img = mask_img.resize((int(target_w), int(target_h)), Image.NEAREST)
            except Exception:
                mask_img = mask_img.resize((int(target_w), int(target_h)))

        # Ensure content is RGBA and sized to target canvas for bbox/alpha ops
        try:
            content_rgba = content_rgba.convert("RGBA")
        except Exception:
            pass

        alpha = np.array(mask_img.split()[-1], dtype=np.uint8)
        inv_alpha = (255 - alpha).astype(np.uint8)
        window = inv_alpha > 0
        if not window.any():
            return content_rgba

        # Keep only largest 4-connected component
        h, w = window.shape
        visited = np.zeros((h, w), dtype=bool)
        best_coords = None
        best_len = 0
        for i in range(h):
            for j in range(w):
                if window[i, j] and not visited[i, j]:
                    stack = [(i, j)]
                    visited[i, j] = True
                    coords = []
                    while stack:
                        y, x = stack.pop()
                        coords.append((y, x))
                        if y > 0 and window[y - 1, x] and not visited[y - 1, x]:
                            visited[y - 1, x] = True; stack.append((y - 1, x))
                        if y + 1 < h and window[y + 1, x] and not visited[y + 1, x]:
                            visited[y + 1, x] = True; stack.append((y + 1, x))
                        if x > 0 and window[y, x - 1] and not visited[y, x - 1]:
                            visited[y, x - 1] = True; stack.append((y, x - 1))
                        if x + 1 < w and window[y, x + 1] and not visited[y, x + 1]:
                            visited[y, x + 1] = True; stack.append((y, x + 1))
                    if len(coords) > best_len:
                        best_len = len(coords)
                        best_coords = coords
        if not best_coords:
            return content_rgba

        ys, xs = zip(*best_coords)
        top, left = int(min(ys)), int(min(xs))
        bottom, right = int(max(ys)) + 1, int(max(xs)) + 1
        bw, bh = max(1, right - left), max(1, bottom - top)

        # Compute active bbox of content alpha and cover-fit into (bw, bh)
        try:
            a = np.array(content_rgba.split()[-1], dtype=np.uint8)
            ys2, xs2 = np.where(a > 1)
            if ys2.size == 0:
                fitted = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            else:
                c_top, c_left = int(ys2.min()), int(xs2.min())
                c_bottom, c_right = int(ys2.max()) + 1, int(xs2.max()) + 1
                core = content_rgba.crop((c_left, c_top, c_right, c_bottom))
                cw, ch = core.size
                s = max(bw / max(1, cw), bh / max(1, ch))
                nw, nh = max(1, int(round(cw * s))), max(1, int(round(ch * s)))
                scaled = core.resize((nw, nh), Image.LANCZOS)
                x0 = max(0, (nw - bw) // 2)
                y0 = max(0, (nh - bh) // 2)
                fitted = scaled.crop((x0, y0, x0 + bw, y0 + bh))
        except Exception:
            fitted = content_rgba.resize((bw, bh), Image.LANCZOS)

        matte = (window[top:bottom, left:right].astype(np.uint8) * 255)
        out = Image.new("RGBA", (int(target_w), int(target_h)), (0, 0, 0, 0))
        try:
            out.paste(fitted, (left, top), Image.fromarray(matte, mode="L"))
        except Exception:
            out.paste(fitted, (left, top))
        return out

    def _apply_mask_clip(self, content_rgba, mask_path: str, target_w: int, target_h: int):
        """Clip content to the mask's opaque area without resizing to fit.

        - Resizes the mask to target size if needed
        - Multiplies the content alpha by mask alpha (keeps pixels where mask alpha > 0)
        - Returns RGBA image same size as target with content cut by the mask
        """
        try:
            from PIL import Image
        except Exception:
            return content_rgba

        try:
            mask_raw = Image.open(mask_path)
        except Exception:
            return content_rgba

        # Derive a binary mask (L mode) from either transparency windows or luminance
        try:
            if mask_raw.mode != "RGBA":
                mask_rgba = mask_raw.convert("RGBA")
            else:
                mask_rgba = mask_raw
            alpha_band = mask_rgba.split()[-1]
            # Detect if the mask uses transparency windows (significant transparent area)
            try:
                # Count fraction of pixels with alpha < 128
                hist = alpha_band.histogram()
                total = max(1, sum(hist))
                transparent_count = sum(hist[:128])
                transparent_frac = float(transparent_count) / float(total)
            except Exception:
                transparent_frac = 0.0
            if transparent_frac > 0.05:
                # Use inverted alpha so transparent regions become selection (keep content there)
                from PIL import ImageChops as _ImageChops  # type: ignore
                mask_l = _ImageChops.invert(alpha_band)
            else:
                # Use luminance; keep bright (white) regions
                mask_l = mask_rgba.convert("L")
            # Threshold to binary to avoid halos from antialiasing
            mask_l = mask_l.point(lambda p: 255 if int(p) >= 128 else 0)
        except Exception:
            # Fallback: grayscale luminance
            try:
                mask_l = mask_raw.convert("L")
                mask_l = mask_l.point(lambda p: 255 if int(p) >= 128 else 0)
            except Exception:
                return content_rgba

        # Ensure content is RGBA and of target size
        try:
            content_rgba = content_rgba.convert("RGBA")
        except Exception:
            pass
        if content_rgba.size != (int(target_w), int(target_h)):
            try:
                content_rgba = content_rgba.resize((int(target_w), int(target_h)), Image.LANCZOS)
            except Exception:
                content_rgba = content_rgba.resize((int(target_w), int(target_h)))

        # Resize mask to target using nearest to preserve hard edges
        if mask_l.size != (int(target_w), int(target_h)):
            try:
                mask_l = mask_l.resize((int(target_w), int(target_h)), Image.NEAREST)
            except Exception:
                mask_l = mask_l.resize((int(target_w), int(target_h)))

        # Multiply content alpha by mask alpha
        r, g, b, a = content_rgba.split()
        try:
            from PIL import ImageChops  # type: ignore
            a_masked = ImageChops.multiply(a, mask_l)
        except Exception:
            # Fallback: overwrite alpha with mask
            a_masked = mask_l
        out = Image.merge("RGBA", (r, g, b, a_masked))
        return out

