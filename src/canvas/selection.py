from typing import Optional, Tuple
from dataclasses import asdict

import tkinter as tk
from tkinter import messagebox

from src.canvas.object import CanvasObject
from src.core import MM_TO_PX
from .context_menu import CanvasContextPopup


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
                pass

    # --- Event bindings ---
    def on_click(self, e):
        try:
            self.s.canvas.focus_set()
        except Exception:
            pass
        hit = self.s.canvas.find_withtag("current")
        target = None
        if hit:
            cid = hit[0]
            if cid in self.s._items:
                # Ignore slots for selection
                if self.s._items.get(cid, {}).get("type") != "slot":
                    target = cid
            else:
                for rid, meta in self.s._items.items():
                    if meta.get("label_id") == cid:
                        # Ignore slots for selection (even via their label)
                        if meta.get("type") != "slot":
                            target = rid
                            break
        self.select(target)
        if target:
            meta = self.s._items.get(target, {})
            if meta.get("type") in ("rect", "image"):
                x1, y1, x2, y2 = self.s.canvas.bbox(target)
                self._drag_off = (e.x - x1, e.y - y1)
                # Use bbox size for both rects and images
                self._drag_size = (x2 - x1, y2 - y1)
                self._drag_kind = "rect"
            else:
                cx, cy = self.s.canvas.coords(target)
                self._drag_off = (e.x - cx, e.y - cy)
                self._drag_kind = "text"
        else:
            self._drag_kind = None

    def on_drag(self, e):
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if self._drag_kind == "rect":
            x1 = e.x - self._drag_off[0]
            y1 = e.y - self._drag_off[1]
            # constrain to inner jig bounds
            jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
            obj = self.s._items[self._selected]
            w, h = obj["w_mm"] * self.s._zoom, obj["h_mm"] * self.s._zoom
            # clamp to inner jig bounds; allow rects/images/slots to touch jig edge
            ox = 0.0
            oy = 0.0
            x1 = max(jx0 + ox, min(x1, jx1 - ox - w))
            y1 = max(jy0 + oy, min(y1, jy1 - oy - h))
            # compute raw mm from clamped px, then snap to nearest 1mm
            raw_x_mm = (x1 - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            raw_y_mm = (y1 - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            sx_mm = self.s._snap_mm(raw_x_mm)
            sy_mm = self.s._snap_mm(raw_y_mm)
            # clamp snapped mm to allowed integer range
            min_mm_x = (jx0 + ox - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            max_mm_x = (jx1 - ox - w - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            min_mm_y = (jy0 + oy - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            max_mm_y = (jy1 - oy - h - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            sx_mm = int(max(min_mm_x, min(sx_mm, max_mm_x)))
            sy_mm = int(max(min_mm_y, min(sy_mm, max_mm_y)))
            # if snapped mm didn't change, skip redundant updates for smoother feel
            prev_mm_x = int(round(float(meta.get("x_mm", 0))))
            prev_mm_y = int(round(float(meta.get("y_mm", 0))))
            if sx_mm == prev_mm_x and sy_mm == prev_mm_y:
                return
            new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self.s._zoom
            new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self.s._zoom

            if meta.get("type") in ("rect", "slot"):
                # Idk why, but without -4, the rect is slightly larger than the stored mm
                self.s.canvas.coords(self._selected, new_left, new_top, new_left + w, new_top + h)
                if meta.get("label_id"):
                    self.s.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                    self.s._raise_all_labels()
            elif meta.get("type") == "image":
                self.s.canvas.coords(self._selected, new_left, new_top)
                # move selection border if present
                bid = meta.get("border_id")
                if bid:
                    self.s.canvas.coords(bid, new_left, new_top, new_left + w, new_top + h)
            # update integer position fields and persist
            try:
                self._suppress_pos_trace = True
                if self.s.sel_x.get() != str(int(sx_mm)):
                    self.s.sel_x.set(str(int(sx_mm)))
                if self.s.sel_y.get() != str(int(sy_mm)):
                    self.s.sel_y.set(str(int(sy_mm)))
                meta["x_mm"], meta["y_mm"] = float(int(sx_mm)), float(int(sy_mm))
            finally:
                self._suppress_pos_trace = False
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
                pass

    def on_release(self, _):
        self._drag_kind = None

    def destroy_context_popup(self):
        try:
            if self._ctx_popup_obj:
                self._ctx_popup_obj.destroy()
        except Exception:
            pass
        finally:
            self._ctx_popup_obj = None

    def maybe_show_context_menu(self, e):
        # Only show when right-click targets an existing object
        try:
            hit = self.s.canvas.find_withtag("current")
        except Exception:
            hit = None
        target = None
        if hit:
            cid = hit[0]
            if cid in self.s._items:
                # Don't show menu for slots
                if self.s._items.get(cid, {}).get("type") != "slot":
                    target = cid
            else:
                for rid, meta in self.s._items.items():
                    try:
                        if meta.get("label_id") == cid:
                            if meta.get("type") != "slot":
                                target = rid
                                break
                    except Exception:
                        pass
        if not target:
            self.destroy_context_popup()
            return
        try:
            self.select(target)
        except Exception:
            pass
        # Rebuild popup via ContextPopup
        self.destroy_context_popup()
        self._ctx_popup_obj = CanvasContextPopup(
            self.s, 
            buttons=[
                ("Bring Forward", lambda: self.nudge_z(+1)),
                ("Send Backward", lambda: self.nudge_z(-1)),
                ("Duplicate", self.on_duplicate),
                ("Delete", self.on_delete)
            ]
        )
        self._ctx_popup_obj.show(e.x_root, e.y_root, close_bind_widget=self.s.canvas)
        return "break"

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
            pass
        # delete selection border if any
        try:
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.delete(bid)
        except Exception:
            pass
        try:
            lbl_id = meta.get("label_id")
            if lbl_id:
                self.s.canvas.delete(lbl_id)
        except Exception:
            pass
        self._selected = None
        self.s._update_scrollregion()

    def on_duplicate(self, _evt=None):
        if not self._selected:
            return
        cid = self._selected
        obj: CanvasObject = self.s._items.get(cid, {})
        if obj.type == "image":
            self.s.create_image_item(obj.path, obj.w_mm, obj.h_mm, obj.x_mm, obj.y_mm)
        elif obj.type == "rect":
            self.s.create_placeholder("Text", obj.w_mm, obj.h_mm, obj.outline, obj.outline, obj.x_mm, obj.y_mm)

    # --- Z-index management ---
    def _reorder_by_z(self) -> None:
        """Apply stacking order on the Tk canvas based on CanvasObject.z.

        Lower everything to bottom, then raise in ascending z.
        Keep selection border (if any) on top and then re-raise labels.
        """
        try:
            # Build list of (cid, meta) that have a primary canvas id
            items = [(cid, meta) for cid, meta in self.s._items.items() if cid == meta.get("canvas_id")]
            # If z is missing, treat as 0
            items.sort(key=lambda kv: int(kv[1].get("z", 0)))
            # Reset order by lowering everything
            for cid, _ in items:
                try:
                    self.s.canvas.tag_lower(cid)
                except Exception:
                    pass
            # Raise in sorted order (later ones end up on top)
            for cid, _ in items:
                try:
                    self.s.canvas.tag_raise(cid)
                except Exception:
                    pass
            # Ensure slot labels are above their slots but below other labels
            try:
                for cid, meta in items:
                    if meta.get("type") == "slot" and meta.get("label_id"):
                        # Bring slot label just above its rect
                        self.s.canvas.tag_raise(meta.get("label_id"), cid)
            except Exception:
                pass
            # Ensure current selection border is on top
            if self._selected and self._selected in self.s._items:
                meta = self.s._items.get(self._selected, {})
                bid = meta.get("border_id")
                if bid:
                    try:
                        self.s.canvas.tag_raise(bid)
                    except Exception:
                        pass
            # Ensure labels/text squares stay above
            try:
                # Raise standard labels but not above selection border
                self.s._raise_all_labels()
            except Exception:
                pass
        except Exception:
            pass

    def _normalize_z(self) -> None:
        """Normalize z values to a compact 0..N-1 sequence preserving order."""
        try:
            items = [(cid, meta) for cid, meta in self.s._items.items() if cid == meta.get("canvas_id")]
            items.sort(key=lambda kv: int(kv[1].get("z", 0)))
            for idx, (cid, meta) in enumerate(items):
                try:
                    meta["z"] = int(idx)
                except Exception:
                    pass
        except Exception:
            pass

    def nudge_z(self, delta: int) -> None:
        """Move selected item up (+1) or down (-1) in stacking order."""
        if not self._selected or self._selected not in self.s._items:
            return
        meta = self.s._items[self._selected]
        try:
            z = int(meta.get("z", 0))
        except Exception:
            z = 0
        # Compute bounds from current items
        try:
            all_items = [(cid, m) for cid, m in self.s._items.items() if cid == m.get("canvas_id")]
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
        # Find item currently occupying new_z and swap
        swap_cid = None
        for cid, m in self.s._items.items():
            try:
                if cid == m.get("canvas_id") and int(m.get("z", 0)) == new_z and cid != self._selected:
                    swap_cid = cid
                    break
            except Exception:
                pass
        meta["z"] = int(new_z)
        if swap_cid is not None and swap_cid in self.s._items:
            try:
                self.s._items[swap_cid]["z"] = int(z)
            except Exception:
                pass
        # Apply and normalize
        self._reorder_by_z()
        self._normalize_z()

    # Middle mouse panning helpers
    def on_pan_start(self, e):
        try:
            self.s.canvas.scan_mark(e.x, e.y)
        except Exception:
            pass

    def on_pan_move(self, e):
        try:
            self.s.canvas.scan_dragto(e.x, e.y, gain=1)
        except Exception:
            pass

    def on_pan_end(self, _e):
        # no-op; keep for symmetry/future logic
        pass

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
            pass
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
            pass
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
            pass
        return "break"

    # Core selection API
    def select(self, cid: Optional[int]):
        if getattr(self, "_selected", None) and self._selected in self.s._items:
            prev_meta = self.s._items.get(self._selected, {})
            if prev_meta.get("type") == "rect":
                # restore prior outline color for rect on deselect
                outline_col = prev_meta.get("outline", "#d0d0d0")
                self.s.canvas.itemconfig(self._selected, outline=outline_col, width=2)
            elif prev_meta.get("type") == "text":
                # restore default text color when deselected
                self.s.canvas.itemconfig(self._selected, fill=prev_meta.get("default_fill", "white"))
            elif prev_meta.get("type") == "image":
                # remove selection border if present
                bid = prev_meta.get("border_id")
                if bid:
                    try:
                        self.s.canvas.delete(bid)
                    except Exception:
                        pass
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
            finally:
                self._suppress_pos_trace = False
                self._suppress_size_trace = False
            return
        meta = self.s._items.get(cid, {})
        if meta.get("type") in ("rect", "slot"):
            self.s.canvas.itemconfig(cid, outline="#6ec8ff", width=3)
            # set size fields without triggering live resize
            try:
                self._suppress_size_trace = True
                self.s.sel_w.set(str(int(round(float(meta["w_mm"] or 0)))))
                self.s.sel_h.set(str(int(round(float(meta["h_mm"] or 0)))))
            finally:
                self._suppress_size_trace = False
            # set position from stored mm without triggering move
            try:
                self._suppress_pos_trace = True
                self.s.sel_x.set(str(int(round(float(meta.get("x_mm", 0.0))))))
                self.s.sel_y.set(str(int(round(float(meta.get("y_mm", 0.0))))))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") == "image":
            # draw selection border around image
            try:
                x1, y1, x2, y2 = self.s.canvas.bbox(cid)
                bid = self.s.canvas.create_rectangle(x1, y1, x2, y2, outline="#6ec8ff", width=3)
                meta["border_id"] = bid
            except Exception:
                pass
            try:
                self._suppress_size_trace = True
                self.s.sel_w.set(str(int(round(float(meta["w_mm"] or 0)))))
                self.s.sel_h.set(str(int(round(float(meta["h_mm"] or 0)))))
            finally:
                self._suppress_size_trace = False
            try:
                self._suppress_pos_trace = True
                self.s.sel_x.set(str(int(round(float(meta.get("x_mm", 0.0))))))
                self.s.sel_y.set(str(int(round(float(meta.get("y_mm", 0.0))))))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") == "text":
            # highlight selected text in blue
            self.s.canvas.itemconfig(cid, fill="#6ec8ff")

    def apply_size_to_selection(self):
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "slot"):
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
        w = int(round(w_mm * MM_TO_PX * self.s._zoom))
        h = int(round(h_mm * MM_TO_PX * self.s._zoom))
        if meta.get("type") in ("rect", "slot"):
            self.s.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], cx, cy)
                self.s._raise_all_labels()
        elif meta.get("type") == "image":
            # re-render image at new size and keep center
            photo = self.s._render_photo(meta, max(1, int(w)), max(1, int(h)))
            if photo is not None:
                # move to top-left to keep same center
                self.s.canvas.coords(self._selected, cx - w / 2, cy - h / 2)
                self.s.canvas.itemconfig(self._selected, image=photo)
                bid = meta.get("border_id")
                if bid:
                    self.s.canvas.coords(bid, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
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
            self.s.sel_x.set(str(int(sx_mm)))
            self.s.sel_y.set(str(int(sy_mm)))
            meta["x_mm"] = float(int(sx_mm))
            meta["y_mm"] = float(int(sy_mm))
        finally:
            self._suppress_pos_trace = False

    def on_size_change(self, *_):
        # live update selection size while typing, best-effort
        if self._suppress_size_trace:
            return
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "slot"):
            return
        raw_w = (self.s.sel_w.get() or "").strip()
        raw_h = (self.s.sel_h.get() or "").strip()
        try:
            w_mm = 0 if raw_w == "" else self.s._snap_mm(raw_w)
            h_mm = 0 if raw_h == "" else self.s._snap_mm(raw_h)
        except ValueError:
            return
        # Reflect integer values only if user did not clear the input
        try:
            self._suppress_size_trace = True
            if raw_w != "":
                self.s.sel_w.set(str(int(w_mm)))
            if raw_h != "":
                self.s.sel_h.set(str(int(h_mm)))
        finally:
            self._suppress_size_trace = False
        meta["w_mm"] = float(w_mm)
        meta["h_mm"] = float(h_mm)
        x1, y1, x2, y2 = self.s.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        if meta.get("type") in ("rect", "slot"):
            w = w_mm * MM_TO_PX * self.s._zoom
            h = h_mm * MM_TO_PX * self.s._zoom
            self.s.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], cx, cy)
                self.s._raise_all_labels()
        else:
            # image: re-render at new size and keep center
            w_px = max(1, int(round(w_mm * MM_TO_PX * self.s._zoom)))
            h_px = max(1, int(round(h_mm * MM_TO_PX * self.s._zoom)))
            photo = self.s._render_photo(meta, w_px, h_px)
            if photo is not None:
                self.s.canvas.itemconfig(self._selected, image=photo)
            # move image so center remains the same
            self.s.canvas.coords(self._selected, cx - w_px / 2, cy - h_px / 2)
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.coords(bid, cx - w_px / 2, cy - h_px / 2, cx + w_px / 2, cy + h_px / 2)
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
            self.s.sel_x.set(str(int(sx_mm)))
            self.s.sel_y.set(str(int(sy_mm)))
            meta["x_mm"], meta["y_mm"] = float(int(sx_mm)), float(int(sy_mm))
        finally:
            self._suppress_pos_trace = False

    def on_pos_change(self, *_):
        if self._suppress_pos_trace:
            return
        if not self._selected:
            return
        meta = self.s._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image", "slot"):
            return
        try:
            x_mm = self.s._snap_mm(self.s.sel_x.get())
            y_mm = self.s._snap_mm(self.s.sel_y.get())
        except ValueError:
            return
        w_mm = float(meta.get("w_mm", 0) or 0)
        h_mm = float(meta.get("h_mm", 0) or 0)
        jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
        ox = 0.0
        oy = 0.0
        ox = 0.0
        oy = 0.0
        # desired top-left in px from typed mm
        desired_left = jx0 + ox + int(x_mm) * MM_TO_PX * self.s._zoom
        desired_top = jy0 + oy + int(y_mm) * MM_TO_PX * self.s._zoom
        w = w_mm * MM_TO_PX * self.s._zoom
        h = h_mm * MM_TO_PX * self.s._zoom
        # clamp within jig bounds
        min_left = jx0 + ox
        min_top = jy0 + oy
        max_left = jx1 - ox - w
        max_top = jy1 - oy - h
        new_left = max(min_left, min(desired_left, max_left))
        new_top = max(min_top, min(desired_top, max_top))
        # if clamped, update mm fields to reflect actual placed position
        if new_left != desired_left or new_top != desired_top:
            try:
                self._suppress_pos_trace = True
                x_mm = self.s._snap_mm((new_left - (jx0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
                y_mm = self.s._snap_mm((new_top - (jy0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
                self.s.sel_x.set(str(int(x_mm)))
                self.s.sel_y.set(str(int(y_mm)))
            finally:
                self._suppress_pos_trace = False
        # move selection and label
        if meta.get("type") in ("rect", "slot"):
            self.s.canvas.coords(self._selected, new_left, new_top, new_left + w, new_top + h)
            if meta.get("label_id"):
                self.s.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                self.s._raise_all_labels()
        elif meta.get("type") == "image":
            self.s.canvas.coords(self._selected, new_left, new_top)
            bid = meta.get("border_id")
            if bid:
                self.s.canvas.coords(bid, new_left, new_top, new_left + w, new_top + h)
        # persist mm
        meta["x_mm"], meta["y_mm"] = float(int(x_mm)), float(int(y_mm))
        self.s._update_scrollregion()


