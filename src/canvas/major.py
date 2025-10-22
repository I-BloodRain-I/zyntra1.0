from __future__ import annotations

import logging
from typing import Optional

import tkinter as tk
from tkinter import messagebox

from src.canvas.object import CanvasObject
from src.core import MM_TO_PX

logger = logging.getLogger(__name__)


class MajorManager:
    """Manage Major rectangles and their per-major slot grids.

    This controller operates on the owning screen raiseed at construction time.
    It mirrors the previous in-class methods and uses the screen's helpers
    (jig geometry, selection, slot creation, etc.).
    """

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen

    def update_major_rect(self, name: Optional[str] = None) -> None:
        """Create or update one or more major rectangles on the canvas.

        If `name` is provided, updates only that preset. Otherwise iterates
        over all configured major size presets found in
        `self.s._major_sizes` in a stable numeric order.

        Behavior and side-effects:
        - Clamps preset width/height to the available jig inner area.
        - Persists clamped dimensions back into the preset dict.
        - Creates or updates the canvas rectangle and its label.
        - Stores metadata in `self.s._items` and registers the canvas id in
            `self.s._majors` for future lookups.
        - When a major is moved, shifts child items that report the same
            `owner_major` by the delta to keep relative placement.
        - After completing updates it refreshes canvas labels, scrollregion
            and selection z-order.

        Args:
                name: Optional preset name to update. If omitted, all presets are
                            processed.
        """
        try:
            def _order_key(k: str) -> tuple:
                import re as __re
                m = __re.search(r"(\d+)$", k)
                n = int(m.group(1)) if m else 10**9
                return (n, k)
            ordered_names = sorted(list(self.s._major_sizes.keys()), key=_order_key)
        except Exception:
            ordered_names = list(self.s._major_sizes.keys())
        targets = [name] if name else ordered_names
        outline_col = "#ffff00"
        label_col = "#ffff00"
        jx0, jy0, jx1, jy1 = self.s._jig_inner_rect_px()
        for nm in targets:
            vals = self.s._major_sizes.get(nm)
            if not vals:
                continue
            try:
                mx = float(vals.get("x", 0.0)); my = float(vals.get("y", 0.0))
                mw = float(vals.get("w", 0.0)); mh = float(vals.get("h", 0.0))
            except Exception:
                continue
            # Clamp major width/height to jig inner size minus current x,y offsets (in mm)
            try:
                jig_w_mm = (jx1 - jx0) / (MM_TO_PX * max(self.s._zoom, 1e-6))
                jig_h_mm = (jy1 - jy0) / (MM_TO_PX * max(self.s._zoom, 1e-6))
            except Exception:
                jig_w_mm = max(0.0, (jx1 - jx0) / max(self.s._zoom, 1e-6))
                jig_h_mm = max(0.0, (jy1 - jy0) / max(self.s._zoom, 1e-6))
            # Respect current x,y: max width = jig_width - x; max height = jig_height - y
            try:
                w_max_mm = max(0.0, float(jig_w_mm) - max(0.0, float(mx)))
            except Exception:
                w_max_mm = max(0.0, float(jig_w_mm))
            try:
                h_max_mm = max(0.0, float(jig_h_mm) - max(0.0, float(my)))
            except Exception:
                h_max_mm = max(0.0, float(jig_h_mm))
            mw = float(max(0.0, min(mw, w_max_mm)))
            mh = float(max(0.0, min(mh, h_max_mm)))
            # Persist clamped dimensions back to preset for consistency
            try:
                vals["w"] = str(mw)
                vals["h"] = str(mh)
            except Exception:
                raise
            wpx = max(0.0, mw) * MM_TO_PX * self.s._zoom
            hpx = max(0.0, mh) * MM_TO_PX * self.s._zoom
            try:
                max_x_mm = max(0.0, (jx1 - jx0) / (MM_TO_PX * max(self.s._zoom, 1e-6)) - max(0.0, mw))
                max_y_mm = max(0.0, (jy1 - jy0) / (MM_TO_PX * max(self.s._zoom, 1e-6)) - max(0.0, mh))
            except Exception:
                # Fallback without constants if needed
                max_x_mm = max(0.0, (jx1 - jx0) / max(self.s._zoom, 1e-6) - max(0.0, mw))
                max_y_mm = max(0.0, (jy1 - jy0) / max(self.s._zoom, 1e-6) - max(0.0, mh))
            mx = float(max(0.0, min(mx, max_x_mm)))
            my = float(max(0.0, min(my, max_y_mm)))
            left = jx0 + mx * MM_TO_PX * self.s._zoom
            top = jy0 + my * MM_TO_PX * self.s._zoom
            # Use stable preset name as on-canvas label to avoid renaming on layout
            label_text = str(nm)
            rect_id = self.s._majors.get(nm)
            if rect_id and rect_id in self.s._items:
                self.s.canvas.coords(rect_id, left, top, left + wpx, top + hpx)
                try:
                    self.s.canvas.itemconfig(rect_id, outline=outline_col, width=2)
                except Exception:
                    raise
                meta = self.s._items.get(rect_id, {})
                # Compute delta for movement-only (x/y) to shift owned objects
                try:
                    prev_x_mm = float(meta.get("x_mm", 0.0) or 0.0)
                    prev_y_mm = float(meta.get("y_mm", 0.0) or 0.0)
                except Exception:
                    prev_x_mm = 0.0; prev_y_mm = 0.0
                try:
                    lbl = int(meta.get("label_id", 0) or 0)
                except Exception:
                    lbl = 0
                if lbl:
                    try:
                        self.s.canvas.coords(lbl, left + wpx / 2.0, top + hpx / 2.0)
                        self.s.canvas.itemconfig(lbl, text=label_text, fill=label_col, font=("Myriad Pro", self.s._scaled_pt(8), "bold"))
                    except Exception:
                        raise
                # Persist new geometry
                meta["x_mm"], meta["y_mm"], meta["w_mm"], meta["h_mm"] = float(mx), float(my), float(mw), float(mh)
                # If this was a positional move, shift children owned by this major by the same delta
                try:
                    dx_mm = float(mx) - float(prev_x_mm)
                    dy_mm = float(my) - float(prev_y_mm)
                    if (
                        (abs(dx_mm) > 1e-9 or abs(dy_mm) > 1e-9)
                        and hasattr(self.s, "selection")
                        and not getattr(self.s, "_suppress_major_child_shift", False)
                    ):
                        dx_px = float(dx_mm) * MM_TO_PX * self.s._zoom
                        dy_px = float(dy_mm) * MM_TO_PX * self.s._zoom
                        self.s.selection._shift_children_for_major(str(nm), dx_px, dy_px, dx_mm, dy_mm)
                except Exception:
                    # Non-fatal: child shift best-effort
                    pass
                meta["outline"] = outline_col
            else:
                rect_id = self.s.canvas.create_rectangle(left, top, left + wpx, top + hpx, fill="", outline=outline_col, width=2)
                lbl_id = self.s.canvas.create_text(left + wpx / 2.0, top + hpx / 2.0, text=label_text, fill=label_col, font=("Myriad Pro", self.s._scaled_pt(8), "bold"))
                min_z = min(int(m.get("z", 0)) for _cid, m in self.s._items.items()) if self.s._items else 0
                self.s._items[rect_id] = CanvasObject(
                    type="major",
                    w_mm=float(mw),
                    h_mm=float(mh),
                    x_mm=float(mx),
                    y_mm=float(my),
                    label_id=int(lbl_id),
                    outline=outline_col,
                    canvas_id=int(rect_id),
                    z=int(min_z - 2),
                )
                self.s._majors[nm] = rect_id
                # Keep majors always visible and refresh visibility of owned items
                try:
                    if hasattr(self.s, "_refresh_major_visibility"):
                        self.s._refresh_major_visibility()
                except Exception:
                    raise
        for nm in list(self.s._majors.keys()):
            if nm not in self.s._major_sizes:
                cid = self.s._majors.pop(nm, None)
                if cid and cid in self.s._items:
                    try:
                        lbl = self.s._items[cid].get("label_id")
                        if lbl:
                            self.s.canvas.delete(lbl)
                    except Exception:
                        raise
                    try:
                        self.s.canvas.delete(cid)
                    except Exception:
                        raise
                    self.s._items.pop(cid, None)
        self.s._raise_all_labels()
        self.s._update_scrollregion()
        self.s.selection._reorder_by_z()

    def update_all_majors(self) -> None:
        """Convenience: re-create or refresh all major rectangles.

        Delegates to `update_major_rect(name=None)` which performs the full
        clamp/create/update cycle for every preset in `self.s._major_sizes`.
        """
        self.update_major_rect(name=None)

    def place_slots_all_majors(self, silent: bool = False) -> None:
        """Populate every major with a grid of slots according to presets.

        This removes any existing slot items and regenerates slot rectangles
        for each major in a deterministic order. Per-major parameters are
        read from `self.s._major_sizes[nm]` with fallbacks to the global
        controls on the screen (e.g. `self.s.slot_w`, `self.s.step_x`).

        The grid fills from the major's origin values (origin_x/origin_y)
        and steps by `step_x`/`step_y` (or defaults to slot size). Generated
        slot names follow the pattern "Slot N" and the method will trigger
        UI refreshes (scrollregion, labels, z-order) and a final
        `self.s._renumber_slots()` call.

        Args:
            silent: If True suppresses user-facing error dialogs when a
                    major's numeric parameters are invalid.
        """
        try:
            for cid, meta in list(self.s._items.items()):
                if meta.get("type") == "slot":
                    if meta.get("label_id"):
                        try:
                            self.s.canvas.delete(meta.get("label_id"))
                        except Exception:
                            raise
                    try:
                        self.s.canvas.delete(cid)
                    except Exception:
                        raise
                    self.s._items.pop(cid, None)

            def _order_key(k: str) -> tuple:
                import re as __re
                m = __re.search(r"(\d+)$", k)
                n = int(m.group(1)) if m else 10**9
                return (n, k)
            ordered_names = sorted(list(self.s._major_sizes.keys()), key=_order_key)

            counter = 1
            for nm in ordered_names:
                vals = self.s._major_sizes.get(nm) or {}
                try:
                    mx = float(vals.get("x", 0.0)); my = float(vals.get("y", 0.0))
                    mw = float(vals.get("w", 0.0)); mh = float(vals.get("h", 0.0))
                except Exception:
                    continue
                try:
                    sw = float(vals.get("slot_w", self.s.slot_w.get()))
                    sh = float(vals.get("slot_h", self.s.slot_h.get()))
                    ox = float(vals.get("origin_x", self.s.origin_x.get()))
                    oy = float(vals.get("origin_y", self.s.origin_y.get()))
                    sx = float(vals.get("step_x", self.s.step_x.get() or 0.0))
                    sy = float(vals.get("step_y", self.s.step_y.get() or 0.0))
                except Exception:
                    continue
                if sw <= 0 or sh <= 0:
                    continue
                if sx <= 0: sx = sw
                if sy <= 0: sy = sh
                if sx < sw: sx = sw
                if sy < sh: sy = sh
                if mw <= 0 or mh <= 0 or sw > mw or sh > mh:
                    continue
                start_cx = mx + mw - ox - sw / 2.0
                start_cy = my + mh - oy - sh / 2.0
                start_cx = min(mx + mw - sw / 2.0, max(mx + sw / 2.0, start_cx))
                start_cy = min(my + mh - sh / 2.0, max(my + sh / 2.0, start_cy))

                row = 0
                while True:
                    cy = start_cy - row * sy
                    if cy - sh / 2.0 < my:
                        break
                    col = 0
                    placed_any = False
                    while True:
                        cx = start_cx - col * sx
                        if cx - sw / 2.0 < mx:
                            break
                        x_mm = cx - sw / 2.0
                        y_mm = cy - sh / 2.0
                        if x_mm >= mx and y_mm >= my and (x_mm + sw) <= (mx + mw) and (y_mm + sh) <= (my + mh):
                            self.s._create_slot_at_mm(f"Slot {counter}", sw, sh, x_mm, y_mm, owner_major=str(nm))
                            counter += 1
                            placed_any = True
                        col += 1
                    if not placed_any and row > 0:
                        break
                    row += 1
            self.s._update_scrollregion()
            self.s._raise_all_labels()
            self.s.selection._reorder_by_z()
            self.s._renumber_slots()
        except Exception:
            logger.exception("Failed to place slots inside majors")

    def remove_slots_for_major(self, major_name: Optional[str]) -> None:
        """Remove slot items owned by a specific major or all majors.

        This deletes both the slot rectangle items and their optional label
        canvas objects and removes them from `self.s._items`.

        Args:
            major_name: If None, removes every item with type == 'slot'. If a
                        string is given, removes only slots with matching
                        `owner_major` metadata.
        """
        try:
            if major_name is None:
                to_remove = [cid for cid, meta in self.s._items.items() if meta.get("type") == "slot"]
            else:
                owner = str(major_name)
                # Remove by owner tag to handle moves/resizes reliably
                to_remove = [cid for cid, meta in self.s._items.items()
                             if meta.get("type") == "slot" and str(meta.get("owner_major", "")) == owner]
            for cid in to_remove:
                try:
                    lbl = self.s._items[cid].get("label_id")
                    if lbl:
                        self.s.canvas.delete(lbl)
                except Exception:
                    raise
                try:
                    self.s.canvas.delete(cid)
                except Exception:
                    raise
                self.s._items.pop(cid, None)
        except Exception:
            logger.exception("Failed to remove slots for major")

    def place_slots_for_major(self, major_name: str, silent: bool = False) -> None:
        """Recreate the slot grid for a single major using current parameters.

        Reads slot size, origin and step parameters from the major preset and
        generates slot items restricted to the major rectangle. Existing slots
        for that major are removed first.

        Args:
            major_name: Name of the major preset to populate.
            silent: If True, suppresses dialogs on invalid numeric input.
        """
        if not major_name:
            return
        vals = self.s._major_sizes.get(major_name)
        if not vals:
            return
        try:
            sw = float(vals.get("slot_w", self.s.slot_w.get()))
            sh = float(vals.get("slot_h", self.s.slot_h.get()))
            ox = float(vals.get("origin_x", self.s.origin_x.get()))
            oy = float(vals.get("origin_y", self.s.origin_y.get()))
            sx = float(vals.get("step_x", self.s.step_x.get() or 0.0))
            sy = float(vals.get("step_y", self.s.step_y.get() or 0.0))
            mx = float(vals.get("x", 0.0)); my = float(vals.get("y", 0.0))
            mw = float(vals.get("w", 0.0)); mh = float(vals.get("h", 0.0))
        except Exception:
            if not silent:
                messagebox.showerror("Invalid input", "Enter numeric slot, origin and step values (mm).")
            return
        if sw <= 0 or sh <= 0 or mw <= 0 or mh <= 0:
            return
        if sx <= 0: sx = sw
        if sy <= 0: sy = sh
        if sx < sw: sx = sw
        if sy < sh: sy = sh
        self.remove_slots_for_major(major_name)
        counter = 1
        start_cx = mx + mw - ox - sw / 2.0
        start_cy = my + mh - oy - sh / 2.0
        start_cx = min(mx + mw - sw / 2.0, max(mx + sw / 2.0, start_cx))
        start_cy = min(my + mh - sh / 2.0, max(my + sh / 2.0, start_cy))
        row = 0
        while True:
            cy = start_cy - row * sy
            if cy - sh / 2.0 < my:
                break
            col = 0
            placed_any = False
            while True:
                cx = start_cx - col * sx
                if cx - sw / 2.0 < mx:
                    break
                x_mm = cx - sw / 2.0
                y_mm = cy - sh / 2.0
                if x_mm >= mx and y_mm >= my and (x_mm + sw) <= (mx + mw) and (y_mm + sh) <= (my + mh):
                    self.s._create_slot_at_mm(f"Slot {counter}", sw, sh, x_mm, y_mm, owner_major=str(major_name))
                    counter += 1
                    placed_any = True
                col += 1
            if not placed_any and row > 0:
                break
            row += 1
        self.s._update_scrollregion()
        self.s._raise_all_labels()
        self.s.selection._reorder_by_z()


