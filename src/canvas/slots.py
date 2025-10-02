from __future__ import annotations

import tkinter as tk
from typing import List, Tuple, Optional

from src.core import MM_TO_PX
from src.canvas.object import CanvasObject


class SlotManager:
    """Create, layout, and renumber slots on the jig."""

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen

    def create_slot_at_mm(self, label: str, w_mm: float, h_mm: float, x_mm: float, y_mm: float, owner_major: Optional[str] = None):
        x0, y0, x1, y1 = self.s._jig_inner_rect_px()
        # For slots, allow touching jig border without the +1px inward offset
        ox = 0.0
        oy = 0.0
        # keep fractional mm inputs
        w_mm_i = self.s._snap_mm(w_mm)
        h_mm_i = self.s._snap_mm(h_mm)
        x_mm_i = self.s._snap_mm(x_mm)
        y_mm_i = self.s._snap_mm(y_mm)
        w = w_mm_i * MM_TO_PX * self.s._zoom
        h = h_mm_i * MM_TO_PX * self.s._zoom
        # clamp top-left within inner jig
        min_left = x0 + ox
        min_top = y0 + oy
        max_left = x1 - ox - w
        max_top = y1 - oy - h
        left = x0 + x_mm_i * MM_TO_PX * self.s._zoom + ox
        top = y0 + y_mm_i * MM_TO_PX * self.s._zoom + oy
        new_left = max(min_left, min(left, max_left))
        new_top = max(min_top, min(top, max_top))
        rect = self.s.canvas.create_rectangle(new_left, new_top, new_left + w, new_top + h, fill="#5a5a5a", outline="#898989", width=1)
        txt = self.s.canvas.create_text(new_left + w / 2, new_top + h / 2, text=label, fill="#898989", font=("Myriad Pro", self.s._scaled_pt(6)), tags=("slot_label",))
        # keep provided mm unless clamped
        if new_left != left or new_top != top:
            x_mm_i = self.s._snap_mm((new_left - (x0 + ox)) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
            y_mm_i = self.s._snap_mm((new_top - (y0 + oy)) / (MM_TO_PX * max(self.s._zoom, 1e-6)))
        # next z: force slots to be at the very bottom. Use (current global min z - 1)
        min_z = min(int(m.get("z", 0)) for _cid, m in self.s._items.items()) if self.s._items else 0
        obj = CanvasObject(
            type="slot",
            w_mm=float(w_mm_i),
            h_mm=float(h_mm_i),
            x_mm=float(x_mm_i),
            y_mm=float(y_mm_i),
            label_id=txt,
            outline="#9a9a9a",
            canvas_id=rect,
            z=int(min_z - 1),
        )
        # Tag ownership by provided owner or currently selected major preset
        try:
            owner = str(owner_major or str(getattr(self.s, "major_name").get())).strip()
        except Exception:
            owner = str(owner_major or "").strip()
        try:
            if owner:
                obj["owner_major"] = owner
        except Exception:
            raise
        self.s._items[rect] = obj
        # Respect visibility by active major
        if hasattr(self.s, "_refresh_major_visibility"):
            try:
                self.s._refresh_major_visibility()
            except Exception:
                raise
        return rect

    def place_slots(self, silent: bool = False):
        # Validate and read inputs
        try:
            jx = float(self.s.jig_x.get()); jy = float(self.s.jig_y.get())
            sw = float(self.s.slot_w.get()); sh = float(self.s.slot_h.get())
            ox = float(self.s.origin_x.get()); oy = float(self.s.origin_y.get())
            sx = float(self.s.step_x.get() or 0.0); sy = float(self.s.step_y.get() or 0.0)
        except Exception:
            if not silent:
                from tkinter import messagebox
                messagebox.showerror("Invalid input", "Enter numeric jig, slot, origin and step values (mm).")
            return
        # Basic validation
        if sw <= 0 or sh <= 0:
            if not silent:
                from tkinter import messagebox
                messagebox.showerror("Invalid slot size", "Slot width and height must be > 0 mm.")
            return
        if sw > jx or sh > jy:
            # If slot doesn't fit the jig, remove any existing slots and stop
            for cid, meta in list(self.s._items.items()):
                if meta.get("type") == "slot":
                    if meta.get("label_id"):
                        self.s.canvas.delete(meta.get("label_id"))
                    self.s.canvas.delete(cid)
                    self.s._items.pop(cid, None)
            self.s._update_scrollregion()
            if not silent:
                from tkinter import messagebox
                messagebox.showerror("Slot too large", "Slot must fit inside the jig size.")
            return
        if ox < 0 or oy < 0:
            if not silent:
                from tkinter import messagebox
                messagebox.showerror("Invalid origin", "Origin offsets must be >= 0 mm from lower-right corner.")
            return
        # Step sizes are center-to-center. Default to slot size if not provided or invalid.
        if sx <= 0:
            sx = sw
        if sy <= 0:
            sy = sh
        # Prevent overlap: step must be at least slot size in each axis
        if sx < sw:
            sx = sw
        if sy < sh:
            sy = sh
        # Starting center at lower-right, offset by origin
        start_cx = jx - ox - sw / 2.0
        start_cy = jy - oy - sh / 2.0
        # Clamp so the first slot fully fits
        start_cx = min(jx - sw / 2.0, max(sw / 2.0, start_cx))
        start_cy = min(jy - sh / 2.0, max(sh / 2.0, start_cy))

        # Remove existing slots before laying out new ones
        for cid, meta in list(self.s._items.items()):
            if meta.get("type") == "slot":
                if meta.get("label_id"):
                    self.s.canvas.delete(meta.get("label_id"))
                self.s.canvas.delete(cid)
                self.s._items.pop(cid, None)

        # Lay out grid row-major from lower-right: left first, then move up
        counter = 1
        row = 0
        while True:
            cy = start_cy - row * sy
            if cy - sh / 2.0 < 0:
                break
            col = 0
            placed_any = False
            while True:
                cx = start_cx - col * sx
                if cx - sw / 2.0 < 0:
                    break
                x_mm = cx - sw / 2.0
                y_mm = cy - sh / 2.0
                # Ensure fully inside jig bounds
                if x_mm >= 0 and y_mm >= 0 and (x_mm + sw) <= jx and (y_mm + sh) <= jy:
                    self.create_slot_at_mm(f"Slot {counter}", sw, sh, x_mm, y_mm)
                    counter += 1
                    placed_any = True
                col += 1
            if not placed_any and row > 0:
                # No more space vertically
                break
            row += 1
        # Finalize visuals
        self.s._update_scrollregion()
        self.s._raise_all_labels()
        self.s.selection._reorder_by_z()
        # Ensure labels are contiguous and ordered right-to-left, bottom-to-top
        self.renumber_slots()

    def renumber_slots(self):
        # Build owner->list of (left_px, top_px, rect_id, label_id)
        groups: dict[str, List[Tuple[float, float, int, Optional[int]]]] = {}
        for cid, meta in self.s._items.items():
            if meta.get("type") != "slot":
                continue
            try:
                x1, y1, x2, y2 = self.s.canvas.bbox(cid)
            except Exception:
                continue
            owner = str(meta.get("owner_major", ""))
            groups.setdefault(owner, []).append((float(x1), float(y1), cid, meta.get("label_id")))
        # For each owner group: sort bottom-to-top (y desc), within row right-to-left (x desc), then number from 1
        for _owner, slots in groups.items():
            slots.sort(key=lambda t: (-t[1], -t[0]))
            for idx, (_lx, _ty, _cid, lbl_id) in enumerate(slots, start=1):
                if lbl_id:
                    self.s.canvas.itemconfig(lbl_id, text=f"Slot {idx}")


