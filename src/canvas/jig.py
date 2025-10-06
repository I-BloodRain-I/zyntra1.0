from __future__ import annotations

import math
import logging
from typing import Optional, Tuple

import tkinter as tk

from src.core import MM_TO_PX

logger = logging.getLogger(__name__)


class JigController:
    """Handles jig drawing, zooming, scrollregion and common drawing helpers.

    All methods operate on the owning screen raiseed at construction time.
    """

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen

    # ---- Common helpers ----
    def scaled_pt(self, base: int) -> int:
        try:
            # Scale text strictly by zoom so perceived size stays real except when zooming
            return max(1, int(base * self.s._zoom))
        except Exception:
            return max(1, int(base))

    def update_all_text_fonts(self) -> None:
        # Scale fonts of all canvas item labels according to current zoom
        for cid, meta in list(self.s._items.items()):
            t = meta.get("type")
            if t == "rect":
                # Rect labels are rendered as rotated images; re-render at current zoom
                try:
                    self.s._update_rect_label_image(cid)
                except Exception:
                    logger.exception("Failed to update rotated rect label image during font update")
            elif t == "slot":
                tid = meta.get("label_id")
                if tid:
                    try:
                        self.s.canvas.itemconfig(tid, state="normal")
                        self.s.canvas.itemconfig(tid, font=("Myriad Pro", self.scaled_pt(6)))
                    except Exception:
                        logger.exception("Failed to update slot label font/visibility")
            elif t == "text":
                tid = meta.get("label_id") or cid
                family = str(meta.get("font_family", "Myriad Pro"))
                try:
                    base_pt = int(float(meta.get("font_size_pt", 12)))
                except Exception:
                    base_pt = 12
                size_px = self.scaled_pt(base_pt)
                try:
                    # Keep bold if requested in metadata, otherwise normal
                    weight = str(meta.get("font_weight", "normal"))
                    if weight.lower() == "bold":
                        self.s.canvas.itemconfig(tid, state="normal", font=(family, size_px, "bold"))
                    else:
                        self.s.canvas.itemconfig(tid, state="normal", font=(family, size_px))
                except Exception:
                    if weight.lower() == "bold":
                        self.s.canvas.itemconfig(tid, state="normal", font=("Myriad Pro", size_px, "bold"))
                    else:
                        self.s.canvas.itemconfig(tid, state="normal", font=("Myriad Pro", size_px))
                # Apply text fill override when present
                try:
                    fill_col = str(meta.get("default_fill")) if meta.get("default_fill") else None
                    if fill_col:
                        self.s.canvas.itemconfig(tid, fill=fill_col)
                except Exception:
                    logger.exception("Failed to apply default fill to text item")
            elif t == "major":
                # Scale major label font
                tid = meta.get("label_id")
                if tid:
                    try:
                        self.s.canvas.itemconfig(tid, font=("Myriad Pro", self.scaled_pt(8), "bold"))
                    except Exception:
                        logger.exception("Failed to update major label font")

    def update_rect_overlay(self, cid: int, meta: dict, left: float, top: float, bbox_w: float, bbox_h: float) -> None:
        try:
            ang = float(meta.get("angle", 0.0) or 0.0)
        except Exception:
            ang = 0.0
        # Source (unrotated) size in px from stored mm
        try:
            w_src = float(meta.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom
            h_src = float(meta.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom
        except Exception:
            w_src = bbox_w
            h_src = bbox_h
        cx = left + bbox_w / 2.0
        cy = top + bbox_h / 2.0
        # Compute rotated rectangle polygon (clockwise degrees)
        a = -math.radians(ang)
        ca = math.cos(a)
        sa = math.sin(a)
        hw = w_src / 2.0
        hh = h_src / 2.0
        pts = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        rot = []
        for x, y in pts:
            rx = x * ca - y * sa
            ry = x * sa + y * ca
            rot.extend([cx + rx, cy + ry])
        # Create or update polygon
        rid = int(meta.get("rot_id", 0) or 0)
        fill_col = "#2b2b2b"
        # If this rect is currently selected, use blue selection color and thicker stroke
        try:
            sel_id = getattr(self.s.selection, "_selected", None)
        except Exception:
            sel_id = None
        is_selected = bool(sel_id and sel_id == cid)
        outline_col = "#6ec8ff" if is_selected else str(meta.get("outline", "#d0d0d0"))
        stroke_w = 3 if is_selected else 2
        try:
            if rid and self.s.canvas.type(rid):
                self.s.canvas.coords(rid, *rot)
                self.s.canvas.itemconfig(rid, fill=fill_col, outline=outline_col, width=stroke_w)
            else:
                rid = self.s.canvas.create_polygon(*rot, fill=fill_col, outline=outline_col, width=stroke_w,
                                                    tags=("text_item",) if outline_col == "#17a24b" else None)
                meta["rot_id"] = rid
        except Exception as e:
            logger.exception(f"Failed to update rect overlay polygon: {e}")
        # Keep overlay above base rect
        try:
            self.s.canvas.tag_raise(rid, cid)
        except Exception as e:
            logger.exception(f"Failed to raise rect overlay above base: {e}")

    # ---- Jig and viewport geometry ----
    def jig_rect_px(self) -> Tuple[int, int, int, int]:
        objs = self.s.canvas.find_withtag("jig")
        if not objs:
            return (20, 20, self.s.canvas.winfo_width() - 20, self.s.canvas.winfo_height() - 20)
        return self.s.canvas.bbox(objs[0])

    def jig_inner_rect_px(self) -> Tuple[float, float, float, float]:
        x0, y0, x1, y1 = self.jig_rect_px()
        # compensate for jig border width (3px) drawing centered on the rectangle edge
        stroke = 3.0
        half = stroke / 2.0
        return (x0 + half, y0 + half, x1 - half, y1 - half)

    def item_outline_half_px(self) -> float:
        # Rectangle outline width is 2 px (see placeholder creation); keep fully inside jig
        return 1.0

    def update_scrollregion(self) -> None:
        # still maintain scrollregion internally for centering math
        bbox = self.s.canvas.bbox("all")
        cw = self.s.canvas.winfo_width()
        ch = self.s.canvas.winfo_height()
        if bbox is None:
            self.s.canvas.configure(scrollregion=(0, 0, cw, ch))
            return
        x0, y0, x1, y1 = bbox
        pad = 20
        left = min(0, x0 - pad)
        top = min(0, y0 - pad)
        right = max(cw, x1 + pad)
        bottom = max(ch, y1 + pad)
        self.s.canvas.configure(scrollregion=(left, top, right, bottom))

    def center_view(self) -> None:
        # Center viewport on the jig if content is larger than the viewport
        jig_bbox = self.s.canvas.bbox("jig")
        all_bbox = self.s.canvas.bbox("all")
        if not jig_bbox or not all_bbox:
            return
        x0, y0, x1, y1 = jig_bbox
        ax0, ay0, ax1, ay1 = all_bbox
        cw = max(1, self.s.canvas.winfo_width())
        ch = max(1, self.s.canvas.winfo_height())
        total_w = max(1, ax1 - ax0)
        total_h = max(1, ay1 - ay0)
        # Only move if we actually have scrollable overflow
        if total_w > cw:
            target_x = (x0 + x1) / 2 - cw / 2
            frac_x = (target_x - ax0) / max(1, total_w - cw)
            frac_x = min(1.0, max(0.0, frac_x))
            try:
                self.s.canvas.xview_moveto(frac_x)
            except Exception as e:
                logger.exception(f"Failed to move xview: {e}")
        if total_h > ch:
            target_y = (y0 + y1) / 2 - ch / 2
            frac_y = (target_y - ay0) / max(1, total_h - ch)
            frac_y = min(1.0, max(0.0, frac_y))
            try:
                self.s.canvas.yview_moveto(frac_y)
            except Exception as e:
                logger.exception(f"Failed to move yview: {e}")

    # ---- Drawing / zoom ----
    def redraw_jig(self, _evt=None, center: bool = True) -> None:
        self.s.canvas.delete("jig")
        try:
            jx = float(self.s.jig_x.get())
            jy = float(self.s.jig_y.get())
        except ValueError:
            jx, jy = 296, 394.5831
        # Draw jig scaled by current zoom
        w = int(jx * MM_TO_PX * self.s._zoom)
        h = int(jy * MM_TO_PX * self.s._zoom)
        pad = 20
        cw = max(1, self.s.canvas.winfo_width())
        ch = max(1, self.s.canvas.winfo_height())
        if w + 2 * pad <= cw:
            x0 = (cw - w) // 2
        else:
            x0 = pad
        if h + 2 * pad <= ch:
            y0 = (ch - h) // 2
        else:
            y0 = pad
        x1 = x0 + w
        y1 = y0 + h
        self.s.canvas.create_rectangle(x0, y0, x1, y1, outline="#dddddd", width=3, tags="jig")
        self.update_scrollregion()
        if center:
            self.center_view()
        # Reposition all items using persisted mm
        for cid, meta in self.s._items.items():
            t = meta.get("type")
            if t in ("rect", "slot", "major"):
                try:
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                    w_mm = float(meta.get("w_mm", 0.0))
                    h_mm = float(meta.get("h_mm", 0.0))
                except Exception as e:
                    logger.exception(f"Failed to get dimensions for item {cid}: {e}")
                    continue
                # Allow touching jig border for rects and slots
                ox = 0.0
                oy = 0.0
                wpx = w_mm * MM_TO_PX * self.s._zoom
                hpx = h_mm * MM_TO_PX * self.s._zoom
                # If rect has 90/270 rotation, display as swapped dims
                if t == "rect":
                    try:
                        ang = float(meta.get("angle", 0.0) or 0.0)
                    except Exception:
                        ang = 0.0
                    if int(abs(ang)) % 180 == 90:
                        wpx, hpx = hpx, wpx
                min_left = x0 + ox
                min_top = y0 + oy
                max_left = x1 - ox - wpx
                max_top = y1 - oy - hpx
                left = x0 + x_mm * MM_TO_PX * self.s._zoom + ox
                top = y0 + y_mm * MM_TO_PX * self.s._zoom + oy
                new_left = max(min_left, min(left, max_left))
                new_top = max(min_top, min(top, max_top))
                # Always keep base rect coords in sync (even if invisible for rects)
                self.s.canvas.coords(cid, new_left, new_top, new_left + wpx, new_top + hpx)
                if t == "rect":
                    # Update overlay polygon used for visuals/selection
                    self.update_rect_overlay(cid, meta, new_left, new_top, wpx, hpx)
                if meta.get("type") == "rect":
                    try:
                        self.s._update_rect_label_image(cid)
                    except Exception:
                        raise
                elif meta.get("label_id"):
                    self.s.canvas.coords(meta.label_id, new_left + wpx / 2, new_top + hpx / 2)
                    self.s._raise_all_labels()
                # don't mutate stored mm during redraw
            elif t == "image":
                try:
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                    w_mm = float(meta.get("w_mm", 0.0))
                    h_mm = float(meta.get("h_mm", 0.0))
                except Exception as e:
                    logger.exception(f"Failed to get image dimensions for item {cid}: {e}")
                    continue
                # Allow touching jig border for images
                ox = 0.0
                oy = 0.0
                wpx = int(w_mm * MM_TO_PX * self.s._zoom)
                hpx = int(h_mm * MM_TO_PX * self.s._zoom)
                try:
                    ang = float(meta.get("angle", 0.0) or 0.0)
                except Exception:
                    ang = 0.0
                bw, bh = self.s._rotated_bounds_px(wpx, hpx, ang)
                min_left = x0 + ox
                min_top = y0 + oy
                # Place by the visual top-left of rotated bounds
                max_left = x1 - ox - bw
                max_top = y1 - oy - bh
                left = x0 + x_mm * MM_TO_PX * self.s._zoom + ox
                top = y0 + y_mm * MM_TO_PX * self.s._zoom + oy
                new_left = max(min_left, min(left, max_left))
                new_top = max(min_top, min(top, max_top))
                photo = self.s._render_photo(meta, max(1, int(wpx)), max(1, int(hpx)))
                if photo is not None:
                    self.s.canvas.itemconfig(cid, image=photo)
                # Use visual top-left directly
                place_left = new_left
                place_top = new_top
                self.s.canvas.coords(cid, place_left, place_top)
                bid = meta.get("border_id")
                if bid:
                    self.s.canvas.coords(bid, place_left, place_top, place_left + bw, place_top + bh)
                # don't mutate stored mm during redraw
        # Re-apply stacking order after positions were updated
        self.s.selection._reorder_by_z()
        # After redraw, restore fonts/colors from metadata instead of defaults
        try:
            self.update_all_text_fonts()
        except Exception as e:
            logger.exception(f"Failed to update text fonts after redraw: {e}")

    def zoom_step(self, direction: int) -> None:
        # direction: +1 zoom in, -1 zoom out
        old_zoom = self.s._zoom
        if direction > 0:
            self.s._zoom = min(20.0, self.s._zoom * 2)
        else:
            self.s._zoom = max(0.2, self.s._zoom / 2)
        if abs(self.s._zoom - old_zoom) < 1e-6:
            return
        # Compute current viewport center pivot in mm relative to jig
        cw = max(1, self.s.canvas.winfo_width())
        ch = max(1, self.s.canvas.winfo_height())
        px = self.s.canvas.canvasx(cw // 2)
        py = self.s.canvas.canvasy(ch // 2)
        jx0, jy0, jx1, jy1 = self.jig_inner_rect_px()
        pivot_x_mm = (px - jx0) / (MM_TO_PX * max(old_zoom, 1e-6))
        pivot_y_mm = (py - jy0) / (MM_TO_PX * max(old_zoom, 1e-6))
        # Recompute all coordinates from mm at the new zoom
        self.redraw_jig(_evt=None, center=False)
        # Keep the same pivot at the center of the viewport
        try:
            njx0, njy0, njx1, njy1 = self.jig_inner_rect_px()
            target_px = njx0 + pivot_x_mm * MM_TO_PX * self.s._zoom
            target_py = njy0 + pivot_y_mm * MM_TO_PX * self.s._zoom
            # Update scrollregion and move view so target pivot is centered
            self.update_scrollregion()
            sx0, sy0, sx1, sy1 = [float(v) for v in str(self.s.canvas.cget("scrollregion")).split()]
            total_w = max(1.0, sx1 - sx0)
            total_h = max(1.0, sy1 - sy0)
            desired_left = max(sx0, min(target_px - cw / 2, sx1 - cw))
            desired_top = max(sy0, min(target_py - ch / 2, sy1 - ch))
            if total_w > cw:
                self.s.canvas.xview_moveto((desired_left - sx0) / (total_w - cw))
            if total_h > ch:
                self.s.canvas.yview_moveto((desired_top - sy0) / (total_h - ch))
        except Exception as e:
            logger.exception(f"Failed to update zoom view: {e}")
        # After zooming, scale all text fonts to match the new zoom
        try:
            self.update_all_text_fonts()
        except Exception as e:
            logger.exception(f"Failed to update text fonts: {e}")


