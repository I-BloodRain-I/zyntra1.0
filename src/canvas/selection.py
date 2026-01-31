from typing import Optional, Tuple
from dataclasses import asdict
from copy import deepcopy

import os
import logging
import tkinter as tk
from tkinter import messagebox, filedialog

from src.canvas.object import CanvasObject
from src.core import MM_TO_PX
from .context_menu import CanvasContextPopup

logger = logging.getLogger(__name__)


class CanvasSelection:
    """Encapsulates canvas selection, dragging, sizing, positioning, and context menu.

    This controller delegates drawing and geometry helpers to the owning screen.
    """

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen
        self._selected: Optional[int] = None
        self._drag_off: Tuple[int, int] = (0, 0)
        self._drag_kind: Optional[str] = None  # 'rect' or 'text'
        self._drag_size: Tuple[int, int] = (0, 0)
        self._suppress_size_trace: bool = False
        self._suppress_pos_trace: bool = False
        self._ctx_popup_obj: Optional[CanvasContextPopup] = None
        self._previous_state = {
            "zoom": self.s._zoom,
            "cid": self._selected
        }
        # Global arrow-key panning bindings (work even when canvas not focused)
        try:
            for seq in ("<KeyPress-Left>", "<KeyPress-Right>", "<KeyPress-Up>", "<KeyPress-Down>"):
                self.s.app.bind(seq, self.on_key_pan)
        except Exception:
            # Fallback: bind to canvas only
            try:
                for seq in ("<KeyPress-Left>", "<KeyPress-Right>", "<KeyPress-Up>", "<KeyPress-Down>"):
                    self.s.canvas.bind(seq, self.on_key_pan)
            except Exception:
                logger.exception("Failed to bind key pan handlers on canvas")

    # --- Event bindings ---
    def on_click(self, e):
        """Handle left-click on the canvas.

        Determine which canvas item (if any) was clicked, resolve label/overlay
        hits to their owning item, ignore hidden items, and update the current
        selection by calling self.select(target).
        """
        logger.debug(
            "on_click: at canvas coords x=%s y=%s (event x=%s y=%s), current selected=%s",
            getattr(self.s.canvas, "canvasx", lambda v: v)(getattr(e, "x", 0)),
            getattr(self.s.canvas, "canvasy", lambda v: v)(getattr(e, "y", 0)),
            getattr(e, "x", None), getattr(e, "y", None), getattr(self, "_selected", None)
        )
        try:
            self.s.canvas.focus_set()
        except Exception:
            logger.exception("Failed to set focus to canvas")
        hit = self.s.canvas.find_withtag("current")
        target = None
        if hit:
            cid = hit[0]
            logger.debug("on_click: 'current' hit canvas id=%s", cid)
            if cid in self.s._items:
                # If we hit a slot or major, try to find underlying selectable items
                hit_type = self.s._items.get(cid, {}).get("type")
                logger.debug("on_click: hit belongs to _items with type=%s", hit_type)
                if hit_type in ("slot", "major"):
                    try:
                        # Convert event coords to canvas coordinates
                        cx = self.s.canvas.canvasx(e.x)
                        cy = self.s.canvas.canvasy(e.y)
                        # find_overlapping returns items bottom->top; reverse to check topmost first
                        ids = list(self.s.canvas.find_overlapping(cx, cy, cx, cy))
                        ids.reverse()
                        logger.debug("on_click: overlapping ids (top->bottom)=%s", ids)
                        for iid in ids:
                            try:
                                # Direct base item hit
                                if iid in self.s._items:
                                    if self.s._items.get(iid, {}).get("type") not in ("slot", "major"):
                                        logger.debug("on_click: selecting underlying non-slot item=%s type=%s", iid, self.s._items.get(iid, {}).get("type"))
                                        target = iid
                                        break
                                else:
                                    # Maybe it's a label_id belonging to an item; map back to owner
                                    for rid, rmeta in self.s._items.items():
                                        try:
                                            if rmeta.get("label_id") == iid and rmeta.get("type") not in ("slot", "major"):
                                                logger.debug("on_click: selecting item via label hit; owner=%s type=%s", rid, rmeta.get("type"))
                                                target = rid
                                                break
                                        except Exception:
                                            continue
                                    if target:
                                        break
                            except Exception:
                                logger.exception("Error while inspecting overlapping items for selection")
                    except Exception:
                        logger.exception("Failed to query overlapping items to find underlying selectable item")
                else:
                    # Normal item (not slot/major) — select it
                    if self.s._items.get(cid, {}).get("type") not in ("slot", "major"):
                        logger.debug("on_click: selecting non-slot/major item=%s", cid)
                        target = cid
            else:
                logger.debug("on_click: 'current' id is not a base item; checking labels and overlays")
                for rid, meta in self.s._items.items():
                    if meta.get("label_id") == cid:
                        # Ignore slots for selection (even via their label)
                        if meta.get("type") not in ("slot", "major"):
                            logger.debug("on_click: selecting item via its label; owner=%s type=%s", rid, meta.get("type"))
                            target = rid
                            break
                # Also allow clicking the rotated overlay polygon to select the rect/barcode
                if not target:
                    for rid, meta in self.s._items.items():
                        try:
                            if int(meta.get("rot_id", 0) or 0) == cid and meta.get("type") in ("rect", "barcode"):
                                logger.debug("on_click: selecting rect via its overlay polygon; owner=%s", rid)
                                target = rid
                                break
                        except Exception:
                            logger.exception("Error while checking overlay hit for rect selection")
        # If still nothing selected, attempt a generic pick at the pointer position
        if not target:
            try:
                cx = self.s.canvas.canvasx(e.x)
                cy = self.s.canvas.canvasy(e.y)
                ids = list(self.s.canvas.find_overlapping(cx, cy, cx, cy))
                ids.reverse()  # top-most first
                logger.debug("on_click: fallback overlapping ids (top->bottom)=%s", ids)
                for iid in ids:
                    # direct item
                    if iid in self.s._items and self.s._items.get(iid, {}).get("type") not in ("slot", "major"):
                        logger.debug("on_click: fallback selecting item=%s type=%s", iid, self.s._items.get(iid, {}).get("type"))
                        target = iid
                        break
                    # or a label id belonging to an item
                    for rid, rmeta in self.s._items.items():
                        try:
                            if rmeta.get("label_id") == iid and rmeta.get("type") not in ("slot", "major"):
                                logger.debug("on_click: fallback selecting via label; owner=%s type=%s", rid, rmeta.get("type"))
                                target = rid
                                break
                        except Exception:
                            continue
                    if target:
                        break
            except Exception:
                logger.exception("Failed fallback pick for selection")
        # Prevent selecting hidden items (belonging to other majors)
        try:
            if target and (str(self.s.canvas.itemcget(target, "state")).lower() == "hidden"):
                logger.debug("on_click: target=%s is hidden; clearing selection", target)
                target = None
        except Exception:
            raise
        logger.debug("on_click: final target to select=%s", target)
        self.select(target)
        if target:
            meta = self.s._items.get(target, {})
            # Treat barcode like a rect for selection/dragging purposes because
            # it is rendered as a rectangle on the canvas (coords() returns
            # a bbox with 4 values). This prevents unpacking errors when
            # attempting to read center coords.
            if meta.get("type") in ("rect", "image", "major", "barcode"):
                x1, y1, x2, y2 = self.s.canvas.bbox(target)
                self._drag_off = (e.x - x1, e.y - y1)
                # Use bbox size for both rects and images
                self._drag_size = (x2 - x1, y2 - y1)
                self._drag_kind = "rect"
                logger.debug("on_click: prepared drag rect; drag_off=%s drag_size=%s", self._drag_off, self._drag_size)
            else:
                cx, cy = self.s.canvas.coords(target)
                self._drag_off = (e.x - cx, e.y - cy)
                self._drag_kind = "text"
                logger.debug("on_click: prepared drag text; drag_off=%s", self._drag_off)
        else:
            self._drag_kind = None
            logger.debug("on_click: no target; drag_kind cleared")

    def on_drag(self, e):
        """Handle pointer motion while dragging the currently selected item.

        Supports both rectangle/image dragging (self._drag_kind == 'rect') and
        text dragging (self._drag_kind == 'text'). Updates canvas coords live
        and persists new mm coordinates into the item's metadata.
        """
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if self._drag_kind == "rect":
            # Always drag by the same visual top-left used for drawing the object
            # For images we stored _drag_off against the current bbox at mouse-down,
            # so compute target top-left and then derive anchor placement.
            x1 = e.x - self._drag_off[0]
            y1 = e.y - self._drag_off[1]
            # constrain to inner jig bounds
            jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
            obj = self.s._items[self._selected]
            # base size in px
            w = float(obj.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom
            h = float(obj.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom
            # effective bbox size considering rotation
            try:
                ang = float(obj.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            if obj.get("type") == "image":
                bw, bh = self.s._rotated_bounds_px(float(w), float(h), ang)
            elif obj.get("type") in ("rect", "barcode"):
                # Use rotated bounding box for rects and barcodes
                bw, bh = self.s._rotated_bounds_px(float(w), float(h), ang)
            else:
                bw, bh = w, h
            # clamp to owning major bounds if present; otherwise inner jig bounds
            # Use the same inner offset as used during creation so mm<->px stays consistent
            ox = self.s._item_outline_half_px()
            oy = self.s._item_outline_half_px()
            clamp_left = jx0 + ox
            clamp_top = jy0 + oy
            clamp_right = jx1 - ox
            clamp_bottom = jy1 - oy
            try:
                owner = str(obj.get("owner_major", ""))
            except Exception:
                owner = ""
            if owner and hasattr(self.s, "_majors") and owner in getattr(self.s, "_majors", {}):
                try:
                    mid = int(self.s._majors.get(owner) or 0)
                except Exception:
                    mid = 0
                if mid:
                    try:
                        mb = self.s.canvas.bbox(mid)
                    except Exception:
                        mb = None
                    if mb:
                        clamp_left, clamp_top, clamp_right, clamp_bottom = float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3])
            x1 = max(clamp_left, min(x1, clamp_right - bw))
            y1 = max(clamp_top, min(y1, clamp_bottom - bh))
            # compute raw mm from clamped px; keep fractional mm
            raw_x_mm = (x1 - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            raw_y_mm = (y1 - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            sx_mm = self.s._snap_mm(raw_x_mm)
            sy_mm = self.s._snap_mm(raw_y_mm)
            # clamp mm to allowed range (floats)
            min_mm_x = (jx0 + ox - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            max_mm_x = (jx1 - ox - bw - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            min_mm_y = (jy0 + oy - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            max_mm_y = (jy1 - oy - bh - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            sx_mm = float(max(min_mm_x, min(sx_mm, max_mm_x)))
            sy_mm = float(max(min_mm_y, min(sy_mm, max_mm_y)))
            # Prevent major/major overlap by nudging away from neighbors
            if str(meta.get("type", "")) == "major":
                try:
                    w_mm = float(meta.get("w_mm", 0.0) or 0.0)
                    h_mm = float(meta.get("h_mm", 0.0) or 0.0)
                except Exception:
                    w_mm, h_mm = 0.0, 0.0
                pad_mm = 2.0
                # Bounds in mm for clamping after adjustment
                min_x_mm_allowed = min_mm_x
                max_x_mm_allowed = max_mm_x
                min_y_mm_allowed = min_mm_y
                max_y_mm_allowed = max_mm_y
                # Previous position in mm (for movement direction)
                prev_mm_x = float(meta.get("x_mm", 0.0) or 0.0)
                prev_mm_y = float(meta.get("y_mm", 0.0) or 0.0)
                # Build list of other majors
                others = []
                for rid, m in self.s._items.items():
                    if rid == self._selected:
                        continue
                    if str(m.get("type", "")) != "major":
                        continue
                    try:
                        ox_mm = float(m.get("x_mm", 0.0) or 0.0)
                        oy_mm = float(m.get("y_mm", 0.0) or 0.0)
                        ow_mm = float(m.get("w_mm", 0.0) or 0.0)
                        oh_mm = float(m.get("h_mm", 0.0) or 0.0)
                    except Exception:
                        ox_mm, oy_mm, ow_mm, oh_mm = 0.0, 0.0, 0.0, 0.0
                    others.append((ox_mm, oy_mm, ow_mm, oh_mm))

                def _overlaps(ax, ay, aw, ah, bx, by, bw, bh, pad=0.0) -> bool:
                    return not ((ax + aw + pad) <= bx or (bx + bw) <= (ax - pad) or (ay + ah + pad) <= by or (by + bh) <= (ay - pad))

                # Iteratively resolve collisions with a single-step push along move axis
                max_iter = 16
                it = 0
                while it < max_iter:
                    collided = False
                    for (ox, oy, ow, oh) in others:
                        if _overlaps(sx_mm, sy_mm, w_mm, h_mm, ox, oy, ow, oh, pad=pad_mm):
                            collided = True
                            dx = sx_mm - prev_mm_x
                            dy = sy_mm - prev_mm_y
                            if abs(dx) >= abs(dy):
                                # Resolve along X
                                if dx >= 0:
                                    sx_mm = min(max_x_mm_allowed, ox - pad_mm - w_mm)
                                else:
                                    sx_mm = max(min_x_mm_allowed, ox + ow + pad_mm)
                            else:
                                # Resolve along Y
                                if dy >= 0:
                                    sy_mm = min(max_y_mm_allowed, oy - pad_mm - h_mm)
                                else:
                                    sy_mm = max(min_y_mm_allowed, oy + oh + pad_mm)
                            # Re-clamp to bounds
                            sx_mm = float(max(min_x_mm_allowed, min(sx_mm, max_x_mm_allowed)))
                            sy_mm = float(max(min_y_mm_allowed, min(sy_mm, max_y_mm_allowed)))
                            break
                    if not collided:
                        break
                    it += 1
            # if mm didn't change materially, skip redundant updates for smoother feel
            prev_mm_x = float(meta.get("x_mm", 0.0) or 0.0)
            prev_mm_y = float(meta.get("y_mm", 0.0) or 0.0)
            if abs(sx_mm - prev_mm_x) < 1e-6 and abs(sy_mm - prev_mm_y) < 1e-6:
                return
            new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self.s._zoom
            new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self.s._zoom

            if meta.get("type") == "rect":
                # Size base rect to rotated bounds and update overlay using those extents
                self.s.canvas.coords(self._selected, new_left, new_top, new_left + bw, new_top + bh)
                try:
                    self.s._update_rect_label_image(self._selected)
                except Exception:
                    logger.exception("Failed to update rect label image during drag")
                try:
                    self.s._update_rect_overlay(self._selected, meta, new_left, new_top, bw, bh)
                except Exception:
                    logger.exception("Failed to update rect overlay during drag")
                if meta.get("label_id"):
                    self.s.canvas.coords(meta["label_id"], new_left + bw / 2, new_top + bh / 2)
                    self.s._raise_all_labels()
            elif meta.get("type") in ("slot", "major"):
                # Slots and majors are never rotated; use raw w/h
                self.s.canvas.coords(self._selected, new_left, new_top, new_left + w, new_top + h)
                if meta.get("label_id"):
                    self.s.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                    self.s._raise_all_labels()
            elif meta.get("type") == "barcode":
                # Barcode uses overlay polygon to show rotation, same as rect
                logger.debug("on_drag: moving barcode cid=%s to left/top=(%s,%s) size=(%s,%s)", self._selected, new_left, new_top, bw, bh)
                self.s.canvas.coords(self._selected, new_left, new_top, new_left + bw, new_top + bh)
                try:
                    self.s._update_rect_label_image(self._selected)
                except Exception:
                    logger.exception("Failed to update barcode label image during drag")
                try:
                    self.s._update_rect_overlay(self._selected, meta, new_left, new_top, bw, bh)
                except Exception:
                    logger.exception("Failed to update barcode overlay during drag")
                if meta.get("label_id"):
                    self.s.canvas.coords(meta["label_id"], new_left + bw / 2, new_top + bh / 2)
                    self.s._raise_all_labels()
            elif meta.get("type") == "image":
                # place using rotated bounds (visual top-left == new_left/new_top)
                self.s.canvas.coords(self._selected, new_left, new_top)
                # move selection border if present
                bid = meta.get("border_id")
                if bid:
                    self.s.canvas.coords(bid, new_left, new_top, new_left + bw, new_top + bh)
            # update position fields and persist (keep floats)
            try:
                self._suppress_pos_trace = True
                if self.s.sel_x.get() != str(sx_mm):
                    self.s.sel_x.set(str(sx_mm))
                if self.s.sel_y.get() != str(sy_mm):
                    self.s.sel_y.set(str(sy_mm))
                meta["x_mm"], meta["y_mm"] = float(sx_mm), float(sy_mm)
            finally:
                self._suppress_pos_trace = False
            # Keep stacking updated so dragged item remains interactable above slots/majors
            try:
                self._reorder_by_z()
            except Exception:
                logger.exception("Failed to reapply z-order after drag")
            # If dragging a major, shift all owned non-slot items by the same delta
            if str(meta.get("type", "")) == "major":
                try:
                    prev_left = (jx0 + 0.0) + float(prev_mm_x) * MM_TO_PX * self.s._zoom
                    prev_top = (jy0 + 0.0) + float(prev_mm_y) * MM_TO_PX * self.s._zoom
                    dx_px = float(new_left - prev_left)
                    dy_px = float(new_top - prev_top)
                    dx_mm = float(sx_mm - prev_mm_x)
                    dy_mm = float(sy_mm - prev_mm_y)
                except Exception:
                    dx_px = 0.0; dy_px = 0.0; dx_mm = 0.0; dy_mm = 0.0
                try:
                    major_name = None
                    if hasattr(self.s, "_majors"):
                        for nm, rid in getattr(self.s, "_majors", {}).items():
                            if int(rid) == int(self._selected):
                                major_name = str(nm)
                                break
                    if major_name:
                        self._shift_children_for_major(major_name, dx_px, dy_px, dx_mm, dy_mm)
                except Exception:
                    logger.exception("Failed to shift children while dragging major")
        elif self._drag_kind == "text":
            cx = e.x - self._drag_off[0]
            cy = e.y - self._drag_off[1]
            self.s.canvas.coords(self._selected, cx, cy)
            # persist text center in mm
            try:
                jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
                x_mm = (cx - jx0) / (MM_TO_PX * max(self.s._zoom, 1e-6))
                y_mm = (cy - jy0) / (MM_TO_PX * max(self.s._zoom, 1e-6))
                meta["x_mm"], meta["y_mm"] = float(x_mm), float(y_mm)
            except Exception:
                logger.exception("Failed to persist text position during drag")

    def on_release(self, _):
        """Handle pointer release after a drag operation.

        If a major rectangle was moved, triggers a re-layout of its slots.
        Clears drag state at the end of the operation.
        """
        # If releasing a major move, refresh its slots layout
        try:
            t_selected = self._selected if hasattr(self, "_selected") else None
            selected_meta = self.s._items.get(t_selected, {}) if t_selected else {}
            if t_selected and str(selected_meta.get("type", "")) == "major":
                major_name = None
                if hasattr(self.s, "_majors"):
                    for nm, rid in getattr(self.s, "_majors", {}).items():
                        if int(rid) == int(t_selected):
                            major_name = str(nm)
                            break
                if major_name and hasattr(self.s, "_place_slots_for_major"):
                    self.s._place_slots_for_major(major_name, silent=True)
                    if hasattr(self.s, "_renumber_slots"):
                        self.s._renumber_slots()
        except Exception:
            logger.exception("Failed to refresh slots after moving major")
        
        # Auto-save current ASIN's objects after any drag operation
        try:
            if hasattr(self.s, '_save_current_asin_objects'):
                logger.debug(f"[DRAG_END] Drag operation completed - auto-saving to ASIN")
                self.s._save_current_asin_objects()
        except Exception:
            logger.exception("Failed to auto-save ASIN objects after drag")
        
        self._drag_kind = None

    def destroy_context_popup(self):
        """Safely destroy any currently shown context popup.

        This wrapper ensures callers can request destruction without checking
        for existence and logs any exceptions.
        """
        try:
            if self._ctx_popup_obj:
                self._ctx_popup_obj.destroy()
        except Exception:
            logger.exception("Failed to delete selected canvas item")
        finally:
            self._ctx_popup_obj = None

    def maybe_show_context_menu(self, e):
        """Show a context menu on right-click when an object is targeted.

        Determines the target under the mouse and builds a CanvasContextPopup
        with actions appropriate to the selected type. Returns "break" when a
        popup was shown to stop further event propagation.
        """
        # Only show when right-click targets an existing object
        try:
            hit = self.s.canvas.find_withtag("current")
        except Exception:
            hit = None
        target = None
        if hit:
            cid = hit[0]
            if cid in self.s._items:
                # Don't show menu for slots or majors
                if self.s._items.get(cid, {}).get("type") not in ("slot", "major"):
                    target = cid
            else:
                for rid, meta in self.s._items.items():
                    try:
                        if meta.get("label_id") == cid:
                            if meta.get("type") not in ("slot", "major"):
                                target = rid
                                break
                    except Exception:
                        logger.exception("Failed to delete selection border on deselect")
                # Also allow right-clicking the rotated overlay polygon for rects/barcodes
                if not target:
                    for rid, meta in self.s._items.items():
                        try:
                            if int(meta.get("rot_id", 0) or 0) == cid and meta.get("type") in ("rect", "barcode"):
                                target = rid
                                break
                        except Exception:
                            logger.exception("Error while checking overlay hit for context menu")
                # And allow right-clicking the image selection border
                if not target:
                    for iid, meta in self.s._items.items():
                        try:
                            if int(meta.get("border_id", 0) or 0) == cid and meta.get("type") == "image":
                                target = iid
                                break
                        except Exception:
                            logger.exception("Error while checking image border hit for context menu")
        if not target:
            self.destroy_context_popup()
            return
        try:
            self.select(target)
        except Exception:
            logger.exception("Failed to delete selection border")
        # Rebuild popup via ContextPopup
        self.destroy_context_popup()
        buttons = [
            ("Bring Forward", lambda: self.nudge_z(+1)),
            ("Send Backward", lambda: self.nudge_z(-1)),
            ("Duplicate", self.on_duplicate),
        ]
        meta = self.s._items.get(target, {})
        if str(meta.get("type", "")) == "image":
            buttons.append(("Set mask", self._on_set_mask))
            buttons.append(("Remove mask", self._on_remove_mask))
        buttons.append(("Delete", self.on_delete))
        self._ctx_popup_obj = CanvasContextPopup(self.s, buttons=buttons)
        self._ctx_popup_obj.show(e.x_root, e.y_root, close_bind_widget=self.s.canvas)
        return "break"

    def _on_set_mask(self) -> None:
        # Only applicable to selected images
        if not self._selected or self._selected not in self.s._items:
            return
        meta = self.s._items.get(self._selected, {})
        if str(meta.get("type", "")) != "image":
            return
        # Choose PNG mask file
        try:
            mask_path = filedialog.askopenfilename(
                title="Select PNG mask",
                filetypes=[("PNG image", "*.png")],
            )
        except Exception:
            mask_path = ""
        if not mask_path:
            return
        # Compute original image size (in pixels) for the selected item
        img_w_px = None
        img_h_px = None
        try:
            from PIL import Image  # type: ignore
        except Exception:
            Image = None  # type: ignore
        src_path = str(meta.get("path", "") or "")
        if Image is not None and src_path:
            try:
                with Image.open(src_path) as im0:
                    img_w_px, img_h_px = int(im0.width), int(im0.height)
            except Exception:
                img_w_px, img_h_px = None, None
        # Fallback for non-raster (e.g., SVG): use import mm size → px
        if (img_w_px is None or img_h_px is None) and src_path:
            try:
                mm_pair = getattr(self.s, "_compute_import_size_mm", None)
                if callable(mm_pair):
                    res = self.s._compute_import_size_mm(src_path)
                    if res and isinstance(res, tuple) and len(res) == 2:
                        img_w_px = int(round(float(res[0]) * MM_TO_PX))
                        img_h_px = int(round(float(res[1]) * MM_TO_PX))
            except Exception:
                img_w_px, img_h_px = None, None
        if img_w_px is None or img_h_px is None:
            messagebox.showerror("Mask error", "Cannot determine original image size for comparison.")
            return
        # Read mask size
        mask_w_px = None
        mask_h_px = None
        if Image is None:
            messagebox.showerror("Mask error", "Pillow is required to load PNG mask.")
            return
        try:
            with Image.open(mask_path) as im1:
                mask_w_px, mask_h_px = int(im1.width), int(im1.height)
        except Exception:
            messagebox.showerror("Mask error", "Failed to load PNG mask.")
            return
        # Compare sizes
        if int(img_w_px) != int(mask_w_px) or int(img_h_px) != int(mask_h_px):
            messagebox.showerror(
                "Mismatch size",
                f"Mask size {mask_w_px}x{mask_h_px} must match image size {img_w_px}x{img_h_px}.",
            )
            return
        # Persist mask path on object for export/restore
        meta["mask_path"] = str(mask_path)
        # Re-render image immediately at current size
        try:
            w_px = max(1, int(round(float(meta.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom)))
            h_px = max(1, int(round(float(meta.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom)))
            photo = self.s._render_photo(meta, w_px, h_px)
            if photo is not None:
                self.s.canvas.itemconfig(self._selected, image=photo)
        except Exception:
            logger.exception("Failed to refresh image after setting mask")
        messagebox.showinfo("Mask set", "Mask set successfully.")

    def _on_remove_mask(self) -> None:
        if not self._selected or self._selected not in self.s._items:
            return
        meta = self.s._items.get(self._selected, {})
        if str(meta.get("type", "")) != "image":
            return
        # Clear mask and re-render using base size with current angle; preserve top-left
        try:
            meta["mask_path"] = ""
        except Exception:
            raise
        # Preserve current visual top-left from rotated bbox
        try:
            tlx, tly, _x2, _y2 = self.s.canvas.bbox(self._selected)
        except Exception:
            tlx, tly = None, None
        try:
            w_px = max(1, int(round(float(meta.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom)))
            h_px = max(1, int(round(float(meta.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom)))
            photo = self.s._render_photo(meta, w_px, h_px)
            if photo is not None:
                self.s.canvas.itemconfig(self._selected, image=photo)
                # Restore placement and update selection border based on angle
                try:
                    ang = float(meta.get("angle", 0.0) or 0.0)
                except Exception:
                    ang = 0.0
                bw, bh = self.s._rotated_bounds_px(float(w_px), float(h_px), float(ang))
                if tlx is not None and tly is not None:
                    self.s.canvas.coords(self._selected, float(tlx), float(tly))
                    bid = meta.get("border_id")
                    if bid:
                        self.s.canvas.coords(bid, float(tlx), float(tly), float(tlx) + float(bw), float(tly) + float(bh))
        except Exception:
            logger.exception("Failed to refresh image after removing mask")

    # mirror toggle handled as per-ASIN setting; per-object mirroring is not supported

    def on_delete(self, _evt=None):
        if not self._selected:
            return
        cid = self._selected
        meta = self.s._items.pop(cid, None)
        if meta is None:
            return
        try:
            self.s.canvas.delete(cid)
        except Exception:
            logger.exception("Failed to mark canvas for scan (pan start)")
        # delete selection border if any
        try:
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.delete(bid)
        except Exception:
            logger.exception("Failed to scan-drag canvas (pan move)")
        # delete rotation overlay polygon if any
        try:
            rid = int(meta.get("rot_id", 0) or 0)
        except Exception:
            rid = 0
        if rid:
            try:
                self.s.canvas.delete(rid)
            except Exception:
                logger.exception("Failed to delete rotated overlay polygon")
            meta["rot_id"] = None
        try:
            lbl_id = meta.get("label_id")
            if lbl_id:
                self.s.canvas.delete(lbl_id)
        except Exception:
            logger.exception("Failed to delete item label")
        self._selected = None
        self.s._update_scrollregion()
        # Ensure text controls hide immediately after deletion of a text block
        try:
            if hasattr(self.s, "_refresh_text_controls"):
                self.s._refresh_text_controls()
        except Exception:
            logger.exception("Failed to refresh text controls after delete")

    def on_duplicate(self, _evt=None):
        if not self._selected:
            return
        cid = self._selected
        obj: CanvasObject = self.s._items.get(cid, {})
        t = str(obj.get("type", ""))
        # Duplicate images: preserve size, position, angle, mask, and labels/flags
        if t == "image":
            try:
                self.s.create_image_item(str(obj.get("path", "")), float(obj.get("w_mm", 0.0)), float(obj.get("h_mm", 0.0)), float(obj.get("x_mm", 0.0)), float(obj.get("y_mm", 0.0)))
            except Exception:
                return
            # New item becomes selected by create_image_item
            nid = self._selected
            if not nid or nid not in self.s._items:
                return
            nmeta = self.s._items.get(nid, {})
            # Copy metadata
            try:
                nmeta["amazon_label"] = str(obj.get("amazon_label", "") or "")
                nmeta["is_options"] = bool(obj.get("is_options", False))
                nmeta["is_static"] = bool(obj.get("is_static", False))
                if obj.get("mask_path"):
                    nmeta["mask_path"] = str(obj.get("mask_path"))
                if obj.get("owner_major"):
                    nmeta["owner_major"] = str(obj.get("owner_major"))
                if obj.get("custom_images"):
                    nmeta["custom_images"] = deepcopy(obj.get("custom_images"))
                if obj.get("custom_image"):
                    nmeta["custom_image"] = str(obj.get("custom_image"))
                if obj.get("export_file"):
                    nmeta["export_file"] = str(obj.get("export_file"))
                # mirror is a per-ASIN setting and isn't copied per-object
                # Angle and re-render
                try:
                    ang = float(obj.get("angle", 0.0) or 0.0)
                except Exception:
                    ang = 0.0
                nmeta["angle"] = float(ang)
                # Re-render image at current size and keep visual top-left
                w_px = max(1, int(round(float(nmeta.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom)))
                h_px = max(1, int(round(float(nmeta.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom)))
                try:
                    tlx, tly, _x2, _y2 = self.s.canvas.bbox(nid)
                except Exception:
                    coords = self.s.canvas.coords(nid)
                    tlx, tly = (float(coords[0]), float(coords[1])) if coords and len(coords) >= 2 else (0.0, 0.0)
                photo = self.s._render_photo(nmeta, w_px, h_px)
                if photo is not None:
                    self.s.canvas.itemconfig(nid, image=photo)
                bw, bh = self.s._rotated_bounds_px(float(w_px), float(h_px), float(ang))
                self.s.canvas.coords(nid, float(tlx), float(tly))
                bid = nmeta.get("border_id")
                if bid:
                    self.s.canvas.coords(bid, float(tlx), float(tly), float(tlx) + float(bw), float(tly) + float(bh))
            finally:
                self.s._update_scrollregion()
                self._reorder_by_z()
        # Duplicate text-rects (type==rect): preserve label, colors, font, angle, amazon_label
        elif t == "rect":
            try:
                label_text = str(obj.get("label", "Text"))
            except Exception:
                label_text = "Text"
            outline = str(obj.get("outline", "#d0d0d0"))
            try:
                self.s.create_placeholder(label_text, float(obj.get("w_mm", 0.0)), float(obj.get("h_mm", 0.0)), str(obj.get("label_fill", "#ffffff")), outline, float(obj.get("x_mm", 0.0)), float(obj.get("y_mm", 0.0)))
            except Exception:
                return
            nid = self._selected
            if not nid or nid not in self.s._items:
                return
            nmeta = self.s._items.get(nid, {})
            # Copy rect-specific styling and flags
            try:
                nmeta["amazon_label"] = str(obj.get("amazon_label", "") or "")
                nmeta["is_options"] = bool(obj.get("is_options", False))
                nmeta["is_static"] = bool(obj.get("is_static", False))
                if obj.get("owner_major"):
                    nmeta["owner_major"] = str(obj.get("owner_major"))
                if obj.get("label_fill", None) is not None:
                    nmeta["label_fill"] = str(obj.get("label_fill"))
                if obj.get("label_font_size", None) is not None:
                    try:
                        nmeta["label_font_size"] = int(round(float(obj.get("label_font_size", 10))))
                    except Exception:
                        pass
                if obj.get("label_font_family", None) is not None:
                    nmeta["label_font_family"] = str(obj.get("label_font_family"))
                if obj.get("outline", None) is not None:
                    nmeta["outline"] = str(obj.get("outline"))
                # Angle and overlay refresh
                try:
                    ang = float(obj.get("angle", 0.0) or 0.0)
                except Exception:
                    ang = 0.0
                nmeta["angle"] = float(ang)
                # Refresh label image and rotated overlay for new rect
                try:
                    x1, y1, x2, y2 = self.s.canvas.bbox(nid)
                    self.s._update_rect_label_image(nid)
                    self.s._update_rect_overlay(nid, nmeta, float(x1), float(y1), float(x2 - x1), float(y2 - y1))
                except Exception:
                    pass
            finally:
                self.s._update_scrollregion()
                self._reorder_by_z()
        # Duplicate plain text items
        elif t == "text":
            try:
                txt_val = str(self.s.canvas.itemcget(cid, "text"))
            except Exception:
                txt_val = ""
            try:
                fill_val = str(obj.get("default_fill", self.s.canvas.itemcget(cid, "fill") or "white"))
            except Exception:
                fill_val = "white"
            try:
                tid = self.s._create_text_at_mm(txt_val, float(obj.get("x_mm", 0.0)), float(obj.get("y_mm", 0.0)), fill=fill_val)
            except Exception:
                return
            if tid in self.s._items:
                tmeta = self.s._items.get(tid, {})
                try:
                    tmeta["amazon_label"] = str(obj.get("amazon_label", "") or "")
                    tmeta["is_options"] = bool(obj.get("is_options", False))
                    tmeta["is_static"] = bool(obj.get("is_static", False))
                    if obj.get("owner_major"):
                        tmeta["owner_major"] = str(obj.get("owner_major"))
                    # Font styling
                    if obj.get("font_family", None) is not None:
                        tmeta["font_family"] = str(obj.get("font_family"))
                    if obj.get("font_size_pt", None) is not None:
                        try:
                            tmeta["font_size_pt"] = int(round(float(obj.get("font_size_pt", 12))))
                        except Exception:
                            pass
                    use_fam = str(tmeta.get("font_family", "Myriad Pro"))
                    use_pt = int(round(float(tmeta.get("font_size_pt", 12))))
                    self.s.canvas.itemconfig(tid, font=(use_fam, self.s._scaled_pt(use_pt), "bold"))
                    # Put on top
                    try:
                        max_z = max(int(m.get("z", 0)) for _cid, m in self.s._items.items()) if self.s._items else 0
                    except Exception:
                        max_z = 0
                    tmeta["z"] = int(max_z + 1)
                    self._reorder_by_z()
                    self.select(tid)
                finally:
                    self.s._update_scrollregion()

    # --- Z-index management ---
    def _reorder_by_z(self) -> None:
        """Apply stacking order with fixed hierarchy and then by z for others.

        Hierarchy (bottom → top): majors → slots → other objects (by ascending z).
        Keep selection border (if any) on top and then re-raise labels above their base.
        """
        try:
            # Build list of (cid, meta) that have a primary canvas id
            items = [(cid, meta) for cid, meta in self.s._items.items() if cid == meta.get("canvas_id")]
            # Partition: majors, slots, and other items.
            major_items = [(cid, meta) for cid, meta in items if meta.get("type") == "major"]
            slot_items = [(cid, meta) for cid, meta in items if meta.get("type") == "slot"]
            other_items = [(cid, meta) for cid, meta in items if meta.get("type") not in ("slot", "major")]
            # Sort non-slot/non-major items by z (ascending). If z is missing, treat as 0
            other_items.sort(key=lambda kv: int(kv[1].get("z", 0)))
            # Reset order by lowering everything
            for cid, _ in items:
                try:
                    self.s.canvas.tag_lower(cid)
                except Exception:
                    logger.exception("Failed to lower canvas item while reordering by z")
            # First raise all majors (they should remain below everything else)
            for cid, _ in major_items:
                try:
                    self.s.canvas.tag_raise(cid)
                except Exception:
                    logger.exception("Failed to raise major while reordering by z")
            # Then raise all slots so they stay above majors but below others
            for cid, _ in slot_items:
                try:
                    self.s.canvas.tag_raise(cid)
                except Exception:
                    logger.exception("Failed to raise slot while reordering by z")
            # Then raise non-slot/non-major in sorted order so later ones end up on top
            for cid, _ in other_items:
                try:
                    self.s.canvas.tag_raise(cid)
                except Exception:
                    logger.exception("Failed to raise canvas item while reordering by z")
            # Ensure rect/barcode overlays (rotated polygon) are above their own base rects
            try:
                for cid, meta in other_items:
                    try:
                        if meta.get("type") in ("rect", "barcode"):
                            rid = int(meta.get("rot_id", 0) or 0)
                            if rid:
                                self.s.canvas.tag_raise(rid, cid)
                                # And ensure the rect's label is above its overlay
                                try:
                                    lbl = meta.get("label_id")
                                    if lbl:
                                        self.s.canvas.tag_raise(lbl, rid)
                                except Exception:
                                    logger.exception("Failed to raise rect/barcode label above overlay")
                    except Exception:
                        logger.exception("Failed while iterating overlays for z-order")
            except Exception:
                logger.exception("Failed to raise rect overlays above their base rects")
            # Ensure slot labels are above their slots but below other labels
            try:
                for cid, meta in slot_items:
                    if meta.get("label_id"):
                        # Bring slot label just above its rect
                        self.s.canvas.tag_raise(meta.get("label_id"), cid)
            except Exception:
                logger.exception("Failed to raise slot label above its slot")
            # Ensure current selection indicator is visible:
            # - images: raise temporary selection border
            # Do not force rect/barcode overlays to top to preserve layout semantics
            if self._selected and self._selected in self.s._items:
                meta = self.s._items.get(self._selected, {})
                if meta.get("type") == "image":
                    bid = meta.get("border_id")
                    if bid:
                        try:
                            self.s.canvas.tag_raise(bid)
                        except Exception:
                            logger.exception("Failed to raise selection border to top")
            # Ensure labels/text squares stay above
            try:
                # Raise standard labels but not above selection border
                self.s._raise_all_labels()
            except Exception:
                logger.exception("Failed to raise labels after z-ordering")
        except Exception:
            logger.exception("Failed to reorder items by z")

    def _normalize_z(self) -> None:
        """Normalize z for 'other' items only (exclude slots and majors), preserving order."""
        try:
            items = [
                (cid, meta)
                for cid, meta in self.s._items.items()
                if (cid == meta.get("canvas_id") and meta.get("type") not in ("slot", "major"))
            ]
            items.sort(key=lambda kv: int(kv[1].get("z", 0)))
            for idx, (cid, meta) in enumerate(items):
                try:
                    meta["z"] = int(idx)
                except Exception:
                    logger.exception("Failed to normalize z value for item")
        except Exception:
            logger.exception("Failed to query canvas bbox during wheel pan")

    def nudge_z(self, delta: int) -> None:
        """Move selected item up (+1) or down (-1) in stacking order."""
        if not self._selected or self._selected not in self.s._items:
            return
        meta = self.s._items[self._selected]
        # Never allow manipulating slot/major z via nudge; they are fixed by hierarchy
        if meta.get("type") in ("slot", "major"):
            return
        try:
            z = int(meta.get("z", 0))
        except Exception:
            z = 0
        # Compute bounds from current items (exclude slots and majors)
        try:
            all_items = [
                (cid, m)
                for cid, m in self.s._items.items()
                if (cid == m.get("canvas_id") and m.get("type") not in ("slot", "major"))
            ]
            if not all_items:
                return
            max_z = max(int(m.get("z", 0)) for _cid, m in all_items)
            min_z = min(int(m.get("z", 0)) for _cid, m in all_items)
        except Exception:
            max_z = 0
            min_z = 0
        new_z = z + int(delta)
        new_z = max(min_z, min(max_z, new_z))
        if new_z == z:
            return
        # Find item currently occupying new_z and swap (exclude slots and majors)
        swap_cid = None
        for cid, m in self.s._items.items():
            try:
                if (
                    cid == m.get("canvas_id")
                    and m.get("type") not in ("slot", "major")
                    and int(m.get("z", 0)) == new_z
                    and cid != self._selected
                ):
                    swap_cid = cid
                    break
            except Exception:
                logger.exception("Failed to swap z values during nudge")
        meta["z"] = int(new_z)
        if swap_cid is not None and swap_cid in self.s._items:
            try:
                self.s._items[swap_cid]["z"] = int(z)
            except Exception:
                logger.exception("Failed to compute angle for rect during resize")
        # Apply and normalize
        self._reorder_by_z()
        self._normalize_z()

    # Middle mouse panning helpers
    def on_pan_start(self, e):
        try:
            self.s.canvas.scan_mark(e.x, e.y)
        except Exception:
            logger.exception("Failed to move canvas view during wheel pan")

    def on_pan_move(self, e):
        try:
            self.s.canvas.scan_dragto(e.x, e.y, gain=1)
        except Exception:
            logger.exception("Failed to scan-drag canvas (pan move)")

    def on_pan_end(self, _e):
        # no-op; keep for symmetry/future logic
        return "break"

    def on_key_pan(self, e):
        """Pan the canvas view with arrow keys similar to middle-mouse drag.

        Uses small pixel-based steps and supports modifiers:
        - Shift: larger step
        - Control: smaller step
        """
        try:
            keysym = getattr(e, "keysym", "")
        except Exception:
            keysym = ""
        if keysym not in ("Left", "Right", "Up", "Down"):
            return
        # Determine step size in pixels
        try:
            base_step = 50
            if getattr(e, "state", 0) & 0x0001:  # Shift
                base_step = 200
            if getattr(e, "state", 0) & 0x0004:  # Control
                base_step = 15
        except Exception:
            base_step = 50
        dx_px = 0
        dy_px = 0
        if keysym == "Left":
            dx_px = -base_step
        elif keysym == "Right":
            dx_px = base_step
        elif keysym == "Up":
            dy_px = -base_step
        elif keysym == "Down":
            dy_px = base_step
        # Convert pixel step to xview/yview fractions
        try:
            bbox = self.s.canvas.bbox("all")
        except Exception:
            bbox = None
        if not bbox:
            return "break"
        x0, y0, x1, y1 = bbox
        total_w = max(1, x1 - x0)
        total_h = max(1, y1 - y0)
        try:
            first_x, last_x = self.s.canvas.xview()
        except Exception:
            first_x, last_x = (0.0, 1.0)
        try:
            first_y, last_y = self.s.canvas.yview()
        except Exception:
            first_y, last_y = (0.0, 1.0)
        new_fx = first_x + (dx_px / float(total_w))
        new_fy = first_y + (dy_px / float(total_h))
        # Clamp within [0, 1]
        new_fx = max(0.0, min(1.0, new_fx))
        new_fy = max(0.0, min(1.0, new_fy))
        try:
            if dx_px != 0:
                self.s.canvas.xview_moveto(new_fx)
            if dy_px != 0:
                self.s.canvas.yview_moveto(new_fy)
        except Exception:
            logger.exception("Failed to move view during key pan")
        return "break"

    def on_wheel_zoom(self, e):
        try:
            delta = int(e.delta)
        except Exception:
            delta = 0
        if delta == 0:
            return "break"
        self.s._zoom_step(1 if delta > 0 else -1)
        return "break"

    def on_wheel_pan(self, e):
        """Pan with mouse wheel / touchpad two-finger scroll.

        - Ctrl + wheel: handled by zoom binding elsewhere; do not pan here
        - Shift + wheel: horizontal pan; otherwise vertical pan
        - Linux: Button-4/5 events are also supported
        """
        # Let Ctrl+wheel fall through to zoom handler
        try:
            if getattr(e, "state", 0) & 0x0004:
                return
        except Exception:
            logger.exception("Failed to read event state for wheel pan ctrl-check")
        dx_px = 0
        dy_px = 0
        # Normalize wheel delta across platforms
        try:
            if hasattr(e, "num") and e.num in (4, 5, 6, 7):
                # X11 style buttons: 4/5 vertical, 6/7 horizontal
                direction = -1 if e.num in (4, 6) else 1
                base_step = 80
                if getattr(e, "state", 0) & 0x0001:  # Shift
                    # Force horizontal if Shift held and vertical event
                    dx_px = direction * base_step
                    dy_px = 0
                else:
                    if e.num in (6, 7):
                        dx_px = direction * base_step
                    else:
                        dy_px = direction * base_step
            else:
                delta = int(getattr(e, "delta", 0))
                if delta == 0:
                    return "break"
                # On Windows/Mac, delta usually is multiples of 120; scale accordingly
                scale = max(1, int(round(abs(delta) / 120)))
                step = 80 * scale
                if getattr(e, "state", 0) & 0x0001:  # Shift -> horizontal
                    dx_px = -step if delta > 0 else step
                else:
                    dy_px = -step if delta > 0 else step
        except Exception:
            return "break"
        # Apply movement as xview/yview fractions
        try:
            bbox = self.s.canvas.bbox("all")
        except Exception:
            bbox = None
        if not bbox:
            return "break"
        x0, y0, x1, y1 = bbox
        total_w = max(1, x1 - x0)
        total_h = max(1, y1 - y0)
        try:
            first_x, _ = self.s.canvas.xview()
        except Exception:
            first_x = 0.0
        try:
            first_y, _ = self.s.canvas.yview()
        except Exception:
            first_y = 0.0
        new_fx = first_x + (dx_px / float(total_w))
        new_fy = first_y + (dy_px / float(total_h))
        new_fx = max(0.0, min(1.0, new_fx))
        new_fy = max(0.0, min(1.0, new_fy))
        try:
            if dx_px != 0:
                self.s.canvas.xview_moveto(new_fx)
            if dy_px != 0:
                self.s.canvas.yview_moveto(new_fy)
        except Exception:
            logger.exception("Failed to move view during wheel pan")
        return "break"

    # Core selection API
    def select(self, cid: Optional[int]):
        """Select or clear selection for a canvas item.

        Args:
            cid: Canvas id to select, or None to clear selection.

        Updates UI controls on the owning screen (size/pos/angle fields), sets
        visual selection rectangles/borders, and prepares drag handles.
        """
        logger.debug("select: requested cid=%s (prev selected=%s)", cid, getattr(self, "_selected", None))
        if getattr(self, "_selected", None) and self._selected in self.s._items:
            prev_meta = self.s._items.get(self._selected, {})
            logger.debug("select: deselecting prev item=%s type=%s", self._selected, prev_meta.get("type"))
            if prev_meta.get("type") in ("rect", "barcode"):
                # For rects/barcodes, keep base rect invisible and recolor overlay to normal outline
                outline_col = prev_meta.get("outline", "#d0d0d0")
                if prev_meta.get("type") == "barcode":
                    outline_col = "black" # Barcodes always have black outline
                try:
                    rid = int(prev_meta.get("rot_id", 0) or 0)
                except Exception:
                    rid = 0
                if rid:
                    try:
                        self.s.canvas.itemconfig(rid, outline=outline_col, width=2)
                        logger.debug("select: deselected rect/barcode overlay rid=%s outline reset to %s", rid, outline_col)
                    except Exception:
                        logger.exception("Failed to reset overlay outline on deselect")
            elif prev_meta.get("type") == "text":
                # restore default text color when deselected
                self.s.canvas.itemconfig(self._selected, fill=prev_meta.get("default_fill", "white"))
                logger.debug("select: deselected text; color reset to default")
            elif prev_meta.get("type") == "image":
                # remove selection border if present
                bid = prev_meta.get("border_id")
                if bid:
                    try:
                        self.s.canvas.delete(bid)
                        logger.debug("select: removed image selection border bid=%s", bid)
                    except Exception:
                        raise
                    prev_meta["border_id"] = None
        self._selected = cid
        if not cid:
            # clear fields when no selection
            try:
                self._suppress_size_trace = True
                self._suppress_pos_trace = True
                self.s.sel_w.set("")
                self.s.sel_h.set("")
                self.s.sel_x.set("")
                self.s.sel_y.set("")
                self.s.sel_angle.set("")
                logger.debug("select: cleared selection UI fields")
                if hasattr(self.s, "sel_amazon_label"):
                    self.s.sel_amazon_label.set("")
                if hasattr(self.s, "sel_is_options"):
                    self.s.sel_is_options.set(False)
                if hasattr(self.s, "sel_is_static"):
                    self.s.sel_is_static.set(False)
                if hasattr(self.s, "sel_export_file"):
                    self.s.sel_export_file.set("")
                if hasattr(self.s, "sel_pen_number"):
                    self.s.sel_pen_number.set("0")
                # Hide custom images block when nothing selected
                if hasattr(self.s, "sel_custom_image_line"):
                    try:
                        self.s.sel_custom_image_line.pack_forget()
                        if hasattr(self.s, "sel_custom_image"):
                            self.s.sel_custom_image.set("")
                    except Exception:
                        logger.exception("Failed to hide custom image selector on deselect")
            finally:
                self._suppress_pos_trace = False
                self._suppress_size_trace = False
            # After deselection, keep global stacking consistent
            self._reorder_by_z()
            logger.debug("select: deselect complete; z-order reapplied")
            # Also refresh screen controls so text menu hides on deselect
            if hasattr(self.s, "_refresh_text_controls"):
                self.s._refresh_text_controls()
            return
        meta = self.s._items.get(cid, {})
        logger.debug("select: selecting item=%s type=%s", cid, meta.get("type"))
        if meta.get("type") == "slot":
            # slots: use base rectangle selection outline
            self.s.canvas.itemconfig(cid, outline="#6ec8ff", width=3)
            logger.debug("select: highlighted slot cid=%s", cid)
        elif meta.get("type") == "major":
            # major: highlight base rect like slots; no overlay
            self.s.canvas.itemconfig(cid, outline="#6ec8ff", width=3)
            try:
                self._suppress_size_trace = True
                self.s.sel_w.set(str(float(meta.get("w_mm", 0.0))))
                self.s.sel_h.set(str(float(meta.get("h_mm", 0.0))))
                self.s.sel_angle.set("0")
                logger.debug("select: set major size w_mm=%s h_mm=%s", meta.get("w_mm"), meta.get("h_mm"))
            finally:
                self._suppress_size_trace = False
            try:
                self._suppress_pos_trace = True
                self.s.sel_x.set(str(float(meta.get("x_mm", 0.0))))
                self.s.sel_y.set(str(float(meta.get("y_mm", 0.0))))
                logger.debug("select: set major position x_mm=%s y_mm=%s", meta.get("x_mm"), meta.get("y_mm"))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") in ("rect", "barcode"):
            # Both rect and barcode use overlay polygon for visual rotation
            try:
                rid = int(meta.get("rot_id", 0) or 0)
            except Exception:
                rid = 0
            if rid:
                try:
                    # Force overlay to reflect selection style now
                    x1, y1, x2, y2 = self.s.canvas.bbox(cid)
                    self.s._update_rect_overlay(cid, meta, x1, y1, x2 - x1, y2 - y1)
                    self.s.canvas.itemconfig(rid, outline="#6ec8ff", width=3)
                    # Keep overlay above its own base rect only (respect global z-order)
                    self.s.canvas.tag_raise(rid, cid)
                    # Ensure label sits above overlay if present
                    try:
                        lbl = meta.get("label_id")
                        if lbl:
                            self.s.canvas.tag_raise(lbl, rid)
                            logger.debug("select: raised label %s above overlay %s", lbl, rid)
                    except Exception:
                        raise
                except Exception:
                    raise
            # set size fields without triggering live resize
            try:
                self._suppress_size_trace = True
                self.s.sel_w.set(str(float(meta.get("w_mm", 0) or 0)))
                self.s.sel_h.set(str(float(meta.get("h_mm", 0) or 0)))
                # angle (if available in UI)
                try:
                    self.s.sel_angle.set(str(abs(int(round(float(meta.get("angle", 0.0) or 0.0))))))
                except Exception:
                    self.s.sel_angle.set("0")
                logger.debug("select: set rect/barcode size w_mm=%s h_mm=%s angle=%s", meta.get("w_mm"), meta.get("h_mm"), meta.get("angle"))
            finally:
                self._suppress_size_trace = False
            # set position from stored mm without triggering move
            try:
                self._suppress_pos_trace = True
                self.s.sel_x.set(str(float(meta.get("x_mm", 0.0))))
                self.s.sel_y.set(str(float(meta.get("y_mm", 0.0))))
                logger.debug("select: set rect/barcode position x_mm=%s y_mm=%s", meta.get("x_mm"), meta.get("y_mm"))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") == "image":
            # draw selection border around image
            try:
                x1, y1, x2, y2 = self.s.canvas.bbox(cid)
                bid = self.s.canvas.create_rectangle(x1, y1, x2, y2, outline="#6ec8ff", width=3)
                meta["border_id"] = bid
                logger.debug("select: created image selection border bid=%s around bbox=%s", bid, (x1, y1, x2, y2))
            except Exception:
                logger.exception("Failed to update rect overlay after resize")
            try:
                self._suppress_size_trace = True
                self.s.sel_w.set(str(float(meta["w_mm"] or 0)))
                self.s.sel_h.set(str(float(meta["h_mm"] or 0)))
                try:
                    self.s.sel_angle.set(str(abs(int(round(float(meta.get("angle", 0.0) or 0.0))))))
                except Exception:
                    self.s.sel_angle.set("0")
                logger.debug("select: set image size w_mm=%s h_mm=%s angle=%s", meta.get("w_mm"), meta.get("h_mm"), meta.get("angle"))
            finally:
                self._suppress_size_trace = False
            try:
                self._suppress_pos_trace = True
                self.s.sel_x.set(str(float(meta.get("x_mm", 0.0))))
                self.s.sel_y.set(str(float(meta.get("y_mm", 0.0))))
                logger.debug("select: set image position x_mm=%s y_mm=%s", meta.get("x_mm"), meta.get("y_mm"))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") == "text":
            # highlight selected text in blue
            self.s.canvas.itemconfig(cid, fill="#6ec8ff")
            logger.debug("select: highlighted text item=%s", cid)

        # Sync amazon label/flags for any selectable type (after branch-specific UI updates)
        # Suppress flag traces while populating UI
        try:
            if hasattr(self.s, "_suppress_flag_traces"):
                self.s._suppress_flag_traces = True
            if hasattr(self.s, "sel_amazon_label"):
                self.s.sel_amazon_label.set(meta.amazon_label)
            if hasattr(self.s, "sel_is_options"):
                self.s.sel_is_options.set(bool(meta.get("is_options", False)))
            if hasattr(self.s, "sel_is_static"):
                self.s.sel_is_static.set(bool(meta.get("is_static", False)))
            # Update export file selector (ignore for slots and majors)
            if hasattr(self.s, "sel_export_file"):
                obj_type = meta.get("type", "")
                if obj_type not in ("slot", "major"):
                    self.s.sel_export_file.set(str(meta.get("export_file", "File 1")))
                else:
                    self.s.sel_export_file.set("")
            # Update pen number selector (ignore for slots and majors)
            if hasattr(self.s, "sel_pen_number"):
                obj_type = meta.get("type", "")
                if obj_type not in ("slot", "major"):
                    self.s.sel_pen_number.set(str(meta.get("pen_number", 0)))
                else:
                    self.s.sel_pen_number.set("0")
            # Show/hide and populate custom image combobox for image type
            if hasattr(self.s, "sel_custom_image_line") and hasattr(self.s, "custom_images"):
                obj_type = meta.get("type", "")
                if obj_type == "image":
                    # Show custom image selector
                    try:
                        self.s.sel_custom_image_line.pack(side="top", anchor="w")
                        # Get custom images from THIS object's metadata
                        custom_imgs = self.s.custom_images.get_custom_images_for_object(meta)
                        logger.info(f"Selection: object cid={cid} has custom_images dict: {custom_imgs}")
                        image_names = sorted(list(custom_imgs.keys())) if custom_imgs else []
                        logger.info(f"Updating combobox for cid={cid} with {len(image_names)} images: {image_names}")
                        self.s._sel_custom_image_combo.configure(values=image_names)
                        # Set current value with trace suppression
                        if hasattr(self.s, "_suppress_custom_image_trace"):
                            self.s._suppress_custom_image_trace = True
                        try:
                            current_custom = str(meta.get("custom_image", "")).strip()
                            self.s.sel_custom_image.set(current_custom)
                            logger.debug("select: set custom_image to '%s' for image cid=%s", current_custom, cid)
                        finally:
                            if hasattr(self.s, "_suppress_custom_image_trace"):
                                self.s._suppress_custom_image_trace = False
                    except Exception:
                        logger.exception("Failed to show/populate custom image selector")
                else:
                    # Hide for non-image types
                    try:
                        self.s.sel_custom_image_line.pack_forget()
                        if hasattr(self.s, "_suppress_custom_image_trace"):
                            self.s._suppress_custom_image_trace = True
                        try:
                            self.s.sel_custom_image.set("")
                        finally:
                            if hasattr(self.s, "_suppress_custom_image_trace"):
                                self.s._suppress_custom_image_trace = False
                    except Exception:
                        logger.exception("Failed to hide custom image selector")
        finally:
            if hasattr(self.s, "_suppress_flag_traces"):
                self.s._suppress_flag_traces = False

        # Re-apply stacking so overlays/labels stay above backgrounds and slots
        self._reorder_by_z()
        logger.debug("select: applied z-order after selection of cid=%s", cid)
        if hasattr(self.s, "_refresh_text_controls"):
            self.s._refresh_text_controls()

    def apply_size_to_selection(self):
        """Apply the size values from the UI controls to the selected object.

        Converts user-entered size values into millimeters, updates the
        object's metadata, and refreshes visual representation on the canvas.
        No-op when nothing is selected.
        """
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "slot", "major", "barcode"):
            return
        # Treat empty inputs as 0mm without overwriting the entry text
        raw_w = (self.s.sel_w.get() or "").strip()
        raw_h = (self.s.sel_h.get() or "").strip()
        try:
            w_mm = 0 if raw_w == "" else self.s._snap_mm(raw_w)
            h_mm = 0 if raw_h == "" else self.s._snap_mm(raw_h)
        except ValueError:
            messagebox.showerror("Invalid size", "Enter numeric X/Y (mm).")
            return
        meta["w_mm"] = float(w_mm)
        meta["h_mm"] = float(h_mm)
        x1, y1, x2, y2 = self.s.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = int(w_mm * MM_TO_PX * self.s._zoom)
        h = int(h_mm * MM_TO_PX * self.s._zoom)
        if meta.get("type") in ("rect", "slot", "major", "barcode"):
            # account for rotation for rects and barcodes using rotated bounds like images
            try:
                ang = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            if meta.get("type") in ("rect", "barcode"):
                rw, rh = self.s._rotated_bounds_px(float(w), float(h), float(ang))
            else:
                rw, rh = w, h
            self.s.canvas.coords(self._selected, cx - rw / 2, cy - rh / 2, cx + rw / 2, cy + rh / 2)
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], cx, cy)
                self.s._raise_all_labels()
            # If overlay polygon exists for rotated rects/barcodes, keep it in sync
            if meta.get("type") in ("rect", "barcode"):
                try:
                    self.s._update_rect_overlay(self._selected, meta, cx - rw / 2, cy - rh / 2, rw, rh)
                    # Also ensure label is raised above new overlay
                    lbl = meta.get("label_id")
                    rid = meta.get("rot_id")
                    if lbl and rid:
                        self.s.canvas.tag_raise(lbl, rid)
                except Exception:
                    raise
        elif meta.get("type") == "image":
            # re-render image at new size and keep center
            photo = self.s._render_photo(meta, max(1, int(w)), max(1, int(h)))
            if photo is not None:
                # compute rotated bounds for placement
                bw, bh = self.s._rotated_bounds_px(float(w), float(h), float(meta.get("angle", 0.0) or 0.0))
                self.s.canvas.coords(self._selected, cx - bw / 2, cy - bh / 2)
                self.s.canvas.itemconfig(self._selected, image=photo)
                bid = meta.get("border_id")
                if bid:
                    self.s.canvas.coords(bid, cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
        self.s._update_scrollregion()
        # update position fields to new top-left after resize
        try:
            self._suppress_pos_trace = True
            bx1, by1, bx2, by2 = self.s.canvas.bbox(self._selected)
            jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
            ox = 0.0
            oy = 0.0
            raw_x_mm = (bx1 - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            raw_y_mm = (by1 - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            sx_mm = self.s._snap_mm(raw_x_mm)
            sy_mm = self.s._snap_mm(raw_y_mm)
            self.s.sel_x.set(str(sx_mm))
            self.s.sel_y.set(str(sy_mm))
            meta["x_mm"] = float(sx_mm)
            meta["y_mm"] = float(sy_mm)
        finally:
            self._suppress_pos_trace = False

    def on_size_change(self, *_):
        """Callback invoked when size control values change in the UI.

        Performs a live preview of size changes and uses _suppress_size_trace
        to avoid recursive updates while programmatically changing fields.
        """
        # live update selection size while typing, best-effort
        if self._suppress_size_trace:
            return
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "slot", "major", "barcode"):
            return
        raw_w = (self.s.sel_w.get() or "").strip()
        raw_h = (self.s.sel_h.get() or "").strip()
        try:
            w_mm = 0 if raw_w == "" else self.s._snap_mm(raw_w)
            h_mm = 0 if raw_h == "" else self.s._snap_mm(raw_h)
        except ValueError:
            return
        meta["w_mm"] = float(w_mm)
        meta["h_mm"] = float(h_mm)
        x1, y1, x2, y2 = self.s.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        if meta.get("type") in ("rect", "slot", "barcode"):
            w = w_mm * MM_TO_PX * self.s._zoom
            h = h_mm * MM_TO_PX * self.s._zoom
            # Respect 90/270 rotation for rect and barcode display bbox
            try:
                ang = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            rw, rh = (h, w) if (meta.get("type") in ("rect", "barcode") and int(abs(ang)) % 180 == 90) else (w, h)
            self.s.canvas.coords(self._selected, cx - rw / 2, cy - rh / 2, cx + rw / 2, cy + rh / 2)
            if meta.get("type") in ("rect", "barcode"):
                try:
                    self.s._update_rect_label_image(self._selected)
                except Exception:
                    raise
            elif meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], cx, cy)
                self.s._raise_all_labels()
            # Keep rotated overlay polygon in sync for rects and barcodes
            if meta.get("type") in ("rect", "barcode"):
                try:
                    self.s._update_rect_overlay(self._selected, meta, cx - rw / 2, cy - rh / 2, rw, rh)
                except Exception:
                    raise
        else:
            # image: re-render at new size and keep center, honoring rotation for border and anchor
            w_px = max(1, int(w_mm * MM_TO_PX * self.s._zoom))
            h_px = max(1, int(h_mm * MM_TO_PX * self.s._zoom))
            photo = self.s._render_photo(meta, w_px, h_px)
            if photo is not None:
                self.s.canvas.itemconfig(self._selected, image=photo)
            # compute rotated bounds for placement and border
            try:
                ang = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            bw, bh = self.s._rotated_bounds_px(float(w_px), float(h_px), ang)
            self.s.canvas.coords(self._selected, cx - bw / 2, cy - bh / 2)
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.coords(bid, cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
        self.s._update_scrollregion()
        # update position fields to new top-left after resize
        try:
            self._suppress_pos_trace = True
            bx1, by1, bx2, by2 = self.s.canvas.bbox(self._selected)
            jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
            ox = self.s._item_outline_half_px(); oy = self.s._item_outline_half_px()
            raw_x_mm = (bx1 - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            raw_y_mm = (by1 - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            sx_mm = self.s._snap_mm(raw_x_mm)
            sy_mm = self.s._snap_mm(raw_y_mm)
            self.s.sel_x.set(str(sx_mm))
            self.s.sel_y.set(str(sy_mm))
            meta["x_mm"], meta["y_mm"] = float(sx_mm), float(sy_mm)
        finally:
            self._suppress_pos_trace = False

    def on_pos_change(self, *_, **kwargs):
        """Callback when position controls change; persist new x/y to the
        selected item's metadata and update canvas coords.

        Reads current values from sel_x/sel_y and clamps/moves the selected
        object accordingly.
        """
        if self._suppress_pos_trace:
            return
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "slot", "barcode"):
            return
        try:
            x_mm = self.s._snap_mm(self.s.sel_x.get())
            y_mm = self.s._snap_mm(self.s.sel_y.get())
        except ValueError:
            return
        w_mm = float(meta.get("w_mm", 0) or 0)
        h_mm = float(meta.get("h_mm", 0) or 0)
        jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
        # Use the same inner offset as during creation/drag
        ox = self.s._item_outline_half_px()
        oy = self.s._item_outline_half_px()
        # desired top-left in px from typed mm
        desired_left = jx0 + ox + float(x_mm) * MM_TO_PX * self.s._zoom
        desired_top = jy0 + oy + float(y_mm) * MM_TO_PX * self.s._zoom
        w = w_mm * MM_TO_PX * self.s._zoom
        h = h_mm * MM_TO_PX * self.s._zoom
        # Use live bbox for clamping to reflect current visual size
        try:
            bx1, by1, bx2, by2 = self.s.canvas.bbox(self._selected)
            clamp_w = float(bx2 - bx1)
            clamp_h = float(by2 - by1)
        except Exception:
            clamp_w, clamp_h = w, h
        # clamp within owning major bounds if present; otherwise jig bounds
        clamp_left = jx0 + ox
        clamp_top = jy0 + oy
        clamp_right = jx1 - ox
        clamp_bottom = jy1 - oy
        try:
            owner = str(meta.get("owner_major", ""))
        except Exception:
            owner = ""
        if owner and hasattr(self.s, "_majors") and owner in getattr(self.s, "_majors", {}):
            try:
                mid = int(self.s._majors.get(owner) or 0)
            except Exception:
                mid = 0
            if mid:
                try:
                    mb = self.s.canvas.bbox(mid)
                except Exception:
                    mb = None
                if mb:
                    clamp_left, clamp_top, clamp_right, clamp_bottom = float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3])
        min_left = clamp_left
        min_top = clamp_top
        max_left = clamp_right - clamp_w
        max_top = clamp_bottom - clamp_h
        new_left = max(min_left, min(desired_left, max_left))
        new_top = max(min_top, min(desired_top, max_top))
        # if clamped, update mm fields to reflect actual placed position
        if new_left != desired_left or new_top != desired_top:
            try:
                self._suppress_pos_trace = True
                x_mm = self.s._snap_mm((new_left - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
                y_mm = self.s._snap_mm((new_top - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
                self.s.sel_x.set(str(x_mm))
                self.s.sel_y.set(str(y_mm))
            finally:
                self._suppress_pos_trace = False
        # move selection and label
        if meta.get("type") == "rect":
            # Use rotated bounds for rect placement and overlay update
            try:
                ang = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            rw, rh = self.s._rotated_bounds_px(float(w), float(h), float(ang))
            self.s.canvas.coords(self._selected, new_left, new_top, new_left + rw, new_top + rh)
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], new_left + rw / 2, new_top + rh / 2)
                self.s._raise_all_labels()
            try:
                self.s._update_rect_overlay(self._selected, meta, new_left, new_top, rw, rh)
            except Exception:
                raise
        elif meta.get("type") == "barcode":
            # Use rotated bounds and overlay for barcode (same as rect)
            try:
                ang = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            rw, rh = self.s._rotated_bounds_px(float(w), float(h), float(ang))
            self.s.canvas.coords(self._selected, new_left, new_top, new_left + rw, new_top + rh)
            try:
                self.s._update_rect_overlay(self._selected, meta, new_left, new_top, rw, rh)
            except Exception:
                pass
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], new_left + rw / 2, new_top + rh / 2)
                self.s._raise_all_labels()
        elif meta.get("type") in ("slot", "major"):
            self.s.canvas.coords(self._selected, new_left, new_top, new_left + w, new_top + h)
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                self.s._raise_all_labels()
        elif meta.get("type") == "image":
            bw, bh = self.s._rotated_bounds_px(float(w), float(h), float(meta.get("angle", 0.0) or 0.0))
            place_left = new_left + (w - bw) / 2.0
            place_top = new_top + (h - bh) / 2.0
            self.s.canvas.coords(self._selected, place_left, place_top)
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.coords(bid, place_left, place_top, place_left + bw, place_top + bh)
        # persist mm
        meta["x_mm"], meta["y_mm"] = float(x_mm), float(y_mm)
        self.s._update_scrollregion()


    def on_angle_change(self, *_):
        """Callback for angle control changes; applies rotation to the
        selected rect/image and updates overlays/rotated bounds accordingly.
        """
        # Apply angle changes to current selection (rect, barcode, or image)
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "barcode"):
            return
        # Parse angle
        raw_a = (self.s.sel_angle.get() or "").strip()
        try:
            angle = 0.0 if raw_a == "" else float(raw_a)
        except ValueError:
            return
        # Invert direction for text blocks (rect) and barcodes when rotating via entry
        if str(meta.get("type", "")) in ("rect", "barcode"):
            if float(angle) < 0:
                meta["angle"] = float(angle)
            else:
                meta["angle"] = -float(angle)
        else:
            meta["angle"] = float(angle)
        # Keep center point, update drawing
        try:
            x1, y1, x2, y2 = self.s.canvas.bbox(self._selected)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
        except Exception:
            logger.exception("Failed to get current bbox during angle change")
            return
        if meta.get("type") in ("rect", "barcode"):
            w = float(meta.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom
            h = float(meta.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom
            
            # Use rotated bounds for the base rectangle bounding box
            bw, bh = self.s._rotated_bounds_px(float(w), float(h), float(angle))
            self.s.canvas.coords(self._selected, cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
            
            # Update label image for rect/barcode
            try:
                self.s._update_rect_label_image(self._selected)
            except Exception:
                pass
            # Update overlay polygon for both rect and barcode
            try:
                self.s._update_rect_overlay(self._selected, meta, cx - bw / 2, cy - bh / 2, bw, bh)
                # Also ensure label is raised above new overlay
                lbl = meta.get("label_id")
                rid = meta.get("rot_id")
                if lbl and rid:
                    self.s.canvas.tag_raise(lbl, rid)
            except Exception:
                pass
        else:
            w_px = int(float(meta.get("w_mm", 0.0)) * MM_TO_PX * self.s._zoom)
            h_px = int(float(meta.get("h_mm", 0.0)) * MM_TO_PX * self.s._zoom)
            # preserve current visual top-left
            try:
                tlx, tly, brx, bry = self.s.canvas.bbox(self._selected)
            except Exception:
                logger.exception("Failed to get image bbox during angle change; falling back to center")
                tlx, tly = cx, cy
            photo = self.s._render_photo(meta, max(1, int(w_px)), max(1, int(h_px)))
            if photo is not None:
                self.s.canvas.itemconfig(self._selected, image=photo)
            bw, bh = self.s._rotated_bounds_px(w_px, h_px, angle)
            self.s.canvas.coords(self._selected, tlx, tly)
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.coords(bid, tlx, tly, tlx + bw, tly + bh)
        # Persist x_mm/y_mm as the visual top-left of the rotated bounds and sync UI
        try:
            jx0, jy0, _jx1, _jy1 = self.s._jig_inner_rect_px()
        except Exception:
            jx0, jy0 = 0.0, 0.0
        # Use the same inner offset as during creation/drag to keep mm consistent
        try:
            ox = self.s._item_outline_half_px(); oy = self.s._item_outline_half_px()
        except Exception:
            ox, oy = 0.0, 0.0
        try:
            ang = float(meta.get("angle", 0.0) or 0.0)
        except Exception:
            ang = 0.0
        try:
            w_mm = float(meta.get("w_mm", 0.0) or 0.0)
            h_mm = float(meta.get("h_mm", 0.0) or 0.0)
        except Exception:
            w_mm, h_mm = 0.0, 0.0
        w_px_f = float(w_mm) * MM_TO_PX * self.s._zoom
        h_px_f = float(h_mm) * MM_TO_PX * self.s._zoom
        bw_f, bh_f = self.s._rotated_bounds_px(float(w_px_f), float(h_px_f), float(ang))
        # Recompute center from current bbox, then derive rotated top-left from center/bounds
        try:
            x1b, y1b, x2b, y2b = self.s.canvas.bbox(self._selected)
            cx_now = (float(x1b) + float(x2b)) / 2.0
            cy_now = (float(y1b) + float(y2b)) / 2.0
        except Exception:
            # Fallback: use current coords top-left + half rotated bounds
            try:
                coords_now = self.s.canvas.coords(self._selected)
                cx_now = float(coords_now[0]) + float(bw_f) / 2.0
                cy_now = float(coords_now[1]) + float(bh_f) / 2.0
            except Exception:
                cx_now, cy_now = 0.0, 0.0
        tlx_f = float(cx_now) - float(bw_f) / 2.0
        tly_f = float(cy_now) - float(bh_f) / 2.0
        x_mm_new = self.s._snap_mm((float(tlx_f) - (float(jx0) + float(ox))) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
        y_mm_new = self.s._snap_mm((float(tly_f) - (float(jy0) + float(oy))) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
        try:
            self._suppress_pos_trace = True
            if hasattr(self.s, "sel_x"):
                self.s.sel_x.set(str(x_mm_new))
            if hasattr(self.s, "sel_y"):
                self.s.sel_y.set(str(y_mm_new))
            meta["x_mm"], meta["y_mm"] = float(x_mm_new), float(y_mm_new)
        finally:
            self._suppress_pos_trace = False
        self.s._update_scrollregion()

    # --- Helpers for moving grouped items within a major ---
    def _shift_children_for_major(self, major_name: str, dx_px: float, dy_px: float, dx_mm: float, dy_mm: float) -> None:
        """Shift all non-slot items owned by the given major by the provided deltas.

        - dx_px/dy_px: pixel deltas applied to canvas coordinates
        - dx_mm/dy_mm: millimeter deltas persisted to object metadata
        """
        try:
            for cid, m in list(self.s._items.items()):
                if int(m.get("canvas_id", 0) or 0) != int(cid):
                    continue
                if str(m.get("type", "")) in ("slot", "major"):
                    continue
                if str(m.get("owner_major", "")) != str(major_name):
                    continue
                t = str(m.get("type", ""))
                if t == "rect":
                    try:
                        x1, y1, x2, y2 = self.s.canvas.bbox(cid)
                        nx1 = float(x1) + dx_px
                        ny1 = float(y1) + dy_px
                        nx2 = float(x2) + dx_px
                        ny2 = float(y2) + dy_px
                        self.s.canvas.coords(cid, nx1, ny1, nx2, ny2)
                        lbl = m.get("label_id")
                        if lbl:
                            self.s.canvas.coords(lbl, (nx1 + nx2) / 2.0, (ny1 + ny2) / 2.0)
                            self.s._raise_all_labels()
                        self.s._update_rect_overlay(cid, m, nx1, ny1, nx2 - nx1, ny2 - ny1)
                    except Exception:
                        logger.exception("Failed to move rect child when shifting major")
                    finally:
                        try:
                            m["x_mm"] = float(m.get("x_mm", 0.0) or 0.0) + float(dx_mm)
                            m["y_mm"] = float(m.get("y_mm", 0.0) or 0.0) + float(dy_mm)
                        except Exception:
                            pass
                elif t == "image":
                    try:
                        coords = self.s.canvas.coords(cid)
                        if coords and len(coords) >= 2:
                            self.s.canvas.coords(cid, float(coords[0]) + dx_px, float(coords[1]) + dy_px)
                        bid = m.get("border_id")
                        if bid:
                            try:
                                bx1, by1, bx2, by2 = self.s.canvas.bbox(bid)
                                self.s.canvas.coords(bid, float(bx1) + dx_px, float(by1) + dy_px, float(bx2) + dx_px, float(by2) + dy_px)
                            except Exception:
                                try:
                                    bcoords = self.s.canvas.coords(bid)
                                    if bcoords and len(bcoords) >= 4:
                                        self.s.canvas.coords(bid, float(bcoords[0]) + dx_px, float(bcoords[1]) + dy_px, float(bcoords[2]) + dx_px, float(bcoords[3]) + dy_px)
                                except Exception:
                                    pass
                    except Exception:
                        logger.exception("Failed to move image child when shifting major")
                    finally:
                        try:
                            m["x_mm"] = float(m.get("x_mm", 0.0) or 0.0) + float(dx_mm)
                            m["y_mm"] = float(m.get("y_mm", 0.0) or 0.0) + float(dy_mm)
                        except Exception:
                            pass
                elif t == "text":
                    try:
                        self.s.canvas.move(cid, dx_px, dy_px)
                    except Exception:
                        logger.exception("Failed to move text child when shifting major")
                    finally:
                        try:
                            m["x_mm"] = float(m.get("x_mm", 0.0) or 0.0) + float(dx_mm)
                            m["y_mm"] = float(m.get("y_mm", 0.0) or 0.0) + float(dy_mm)
                        except Exception:
                            pass
        except Exception:
            logger.exception("Failed while shifting children for major")
