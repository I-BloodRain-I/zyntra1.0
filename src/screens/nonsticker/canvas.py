import os
import re
import json
import shutil
import struct
import logging
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from src.core import Screen, vcmd_float, COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL, MM_TO_PX, IMAGES_PATH, TEMP_FOLDER
from src.core.app import COLOR_BG_SCREEN
from src.utils import *
from src.core.state import ALL_PRODUCTS, FONTS_PATH, PRODUCTS_PATH, state
from src.canvas import CanvasObject, CanvasSelection, MajorManager, JigController, SlotManager, ImageManager, PdfExporter, FontsManager
from .results_download import NStickerResultsDownloadScreen

logger = logging.getLogger(__name__)

DEFAULT_JIG_SIZE   = (296.0, 394.5831)
DEFAULT_SLOT_SIZE  = (40.66, 28.9)
DEFAULT_ORIGIN_POS = (11.76, 12.52)
DEFAULT_STEP_SIZE  = (72.55, 47.85)
# Major must be at least as large as a single slot to render slots
DEFAULT_MAJOR_SIZE = tuple((int(DEFAULT_SLOT_SIZE[i] + (DEFAULT_ORIGIN_POS[i]*2)) for i in range(2)))
DEFAULT_MAJOR_POS  = (12, 15)


class NStickerCanvasScreen(Screen):
    """Non-sticker designer: SKU, jig, import, place, size."""
    def __init__(self, master, app):
        super().__init__(master, app)

        # App title + left-aligned header row with SKU input
        self.brand_bar(self)
        if not self.app.is_fullscreen:
            self.app.toggle_fullscreen()

        state.is_failed = False
        state.error_message = ""

        self.jig = JigController(self)
        self.slots = SlotManager(self)
        self.majors = MajorManager(self)
        self.images = ImageManager(self)
        self.exporter = PdfExporter(self)
        # Delegate helpers to keep existing call sites
        self._scaled_pt = self.jig.scaled_pt
        self._update_all_text_fonts = self.jig.update_all_text_fonts
        self._update_rect_overlay = self.jig.update_rect_overlay
        self._jig_rect_px = self.jig.jig_rect_px
        self._jig_inner_rect_px = self.jig.jig_inner_rect_px
        self._item_outline_half_px = self.jig.item_outline_half_px
        self._update_scrollregion = self.jig.update_scrollregion
        self._center_view = self.jig.center_view
        self._redraw_jig = self.jig.redraw_jig
        self._zoom_step = self.jig.zoom_step
        self._rotated_bounds_px = self.images.rotated_bounds_px
        self._rotated_bounds_mm = self.images.rotated_bounds_mm
        self._render_photo = self.images.render_photo
        self.create_image_item = self.images.create_image_item
        self._create_slot_at_mm = self.slots.create_slot_at_mm
        self._place_slots = self.slots.place_slots
        self._renumber_slots = self.slots.renumber_slots
        # Major delegates
        self._update_major_rect = self.majors.update_major_rect
        self._update_all_majors = self.majors.update_all_majors
        self._place_slots_all_majors = self.majors.place_slots_all_majors
        self._remove_slots_for_major = self.majors.remove_slots_for_major
        self._place_slots_for_major = self.majors.place_slots_for_major
        self._render_scene_to_pdf = self.exporter.render_scene_to_pdf
        self._render_jig_to_svg = self.exporter.render_jig_to_svg
        self._render_single_pattern_svg = self.exporter.render_single_pattern_svg

        # Core state maps used across handlers (must exist before any traces/callbacks run)
        self._items: dict[int, CanvasObject] = {}
        self._majors: dict[str, int] = {}
        self._scene_store: dict[str, list[dict]] = {"front": [], "back": []}
        self._current_side: str = "front"

        # Top row: Write SKU (primary SKU field)
        header_row_top = ttk.Frame(self, style="Screen.TFrame")
        header_row_top.pack(padx=0, pady=(35, 8))
        tk.Label(header_row_top, text=" Write ASIN ", bg="#737373", fg=COLOR_TEXT,
                 font=("Myriad Pro", 22), width=20).pack(side="left", padx=(8, 0))
        self.sku_var = tk.StringVar(value=state.sku or "")
        input_wrap_top = tk.Frame(header_row_top, bg="#000000")
        input_wrap_top.pack(side="left") 
        tk.Frame(input_wrap_top, width=15, height=1, bg="#000000").pack(side="left")
        sku_entry_top = tk.Entry(input_wrap_top, textvariable=self.sku_var, width=22,
                                 bg="#000000", fg="#ffffff", insertbackground="#ffffff",
                                 relief="flat", bd=0, highlightthickness=0,
                                 font=("Myriad Pro", 22))
        sku_entry_top.pack(side="left", ipady=2)

        # Second row: Write name for SKU (independent, labels aligned by fixed width)
        header_row_bottom = ttk.Frame(self, style="Screen.TFrame")
        header_row_bottom.pack(padx=0, pady=(0, 25))
        tk.Label(header_row_bottom, text=" Write name for ASIN ", bg="#737373", fg=COLOR_TEXT,
                 font=("Myriad Pro", 22), width=20).pack(side="left", padx=(8, 0))
        self.sku_name_var = tk.StringVar(value=state.sku_name or "")
        input_wrap_bottom = tk.Frame(header_row_bottom, bg="#000000")
        input_wrap_bottom.pack(side="left")
        tk.Frame(input_wrap_bottom, width=15, height=1, bg="#000000").pack(side="left")
        sku_entry_bottom = tk.Entry(input_wrap_bottom, textvariable=self.sku_name_var, width=22,
                                    bg="#000000", fg="#ffffff", insertbackground="#ffffff",
                                    relief="flat", bd=0, highlightthickness=0,
                                    font=("Myriad Pro", 22))
        sku_entry_bottom.pack(side="left", ipady=2)

        # Left vertical sidebar for Slot size, Origin Pos, Step Size
        left_bar = tk.Frame(self, bg="black")
        left_bar.pack(side="left", fill="y", padx=10, pady=(7, 75))

        # Top horizontal bar for Import, Jig size, tools, and shortcuts
        bar = tk.Frame(self, bg="black")
        bar.pack(fill="x", padx=10, pady=(6, 10))

        # (Replaced) Old Import Image pill removed in favor of tool tile in tools section

        # 2) Jig size label and fields
        tk.Label(bar, text="Jig size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(16, 6))
        self.jig_x = tk.StringVar(value=state.pkg_x or "296.0")
        self.jig_y = tk.StringVar(value=state.pkg_y or "394.5831")
        jig_col = tk.Frame(bar, bg="black")
        jig_col.pack(side="left", padx=8, pady=8)
        # Jig X row
        _jxbox = tk.Frame(jig_col, bg="#6f6f6f")
        _jxbox.pack(side="top", pady=2)
        tk.Label(_jxbox, text="Width: ", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_jxbox, textvariable=self.jig_x, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_jxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Jig Y row
        _jybox = tk.Frame(jig_col, bg="#6f6f6f")
        _jybox.pack(side="top", pady=2)
        tk.Label(_jybox, text="Height:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_jybox, textvariable=self.jig_y, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_jybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # live redraw and slot re-create when jig size changes
        self.jig_x.trace_add("write", self._on_jig_change)
        self.jig_y.trace_add("write", self._on_jig_change)

        # 4) White vertical separator (between jig and tools)
        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)

        # Major Size columns: label | presets | x,y | w,h | vertical separator
        tk.Label(bar, text="Major Info:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(16, 6))

        # Column 2: Preset combobox + buttons stacked
        ms_preset_col = tk.Frame(bar, bg="black")
        ms_preset_col.pack(side="left", padx=8, pady=8)
        ms_wrap = tk.Frame(ms_preset_col, bg="#6f6f6f")
        ms_wrap.pack(side="top", pady=2)
        tk.Label(ms_wrap, text="Preset:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        self._major_sizes = {
            "Major size 1": {
                "x": str(DEFAULT_MAJOR_POS[0]), "y": str(DEFAULT_MAJOR_POS[1]),
                "w": str(DEFAULT_MAJOR_SIZE[0]), "h": str(DEFAULT_MAJOR_SIZE[1]),
                "step_x": str(DEFAULT_STEP_SIZE[0]), "step_y": str(DEFAULT_STEP_SIZE[1]),
                "origin_x": str(DEFAULT_ORIGIN_POS[0]), "origin_y": str(DEFAULT_ORIGIN_POS[1]),
                "slot_w": str(DEFAULT_SLOT_SIZE[0]), "slot_h": str(DEFAULT_SLOT_SIZE[1]),
            },
        }
        self.major_name = tk.StringVar(value="Major size 1")
        self._major_combo = ttk.Combobox(ms_wrap, textvariable=self.major_name, state="readonly", values=list(self._major_sizes.keys()), justify="center", width=13)
        self._major_combo.pack(side="left")

        # Fields state
        self.major_x = tk.StringVar(value="0")
        self.major_y = tk.StringVar(value="0")
        self.major_w = tk.StringVar(value="0")
        self.major_h = tk.StringVar(value="0")

        # Column 3: X on top, Y under it (styled like Jig size rows)
        ms_xy = tk.Frame(bar, bg="black")
        ms_xy.pack(side="left", padx=8, pady=8)
        _mxbox = tk.Frame(ms_xy, bg="#6f6f6f")
        _mxbox.pack(side="top", pady=2)
        tk.Label(_mxbox, text="X:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_mxbox, textvariable=self.major_x, width=8, bg="#d9d9d9", justify="center", validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_mxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        _mybox = tk.Frame(ms_xy, bg="#6f6f6f")
        _mybox.pack(side="top", pady=2)
        tk.Label(_mybox, text="Y:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_mybox, textvariable=self.major_y, width=8, bg="#d9d9d9", justify="center", validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_mybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # Column 4: Width on top, Height under it (styled like Jig size rows)
        ms_wh = tk.Frame(bar, bg="black")
        ms_wh.pack(side="left", padx=8, pady=8)
        _mwbox = tk.Frame(ms_wh, bg="#6f6f6f")
        _mwbox.pack(side="top", pady=2)
        tk.Label(_mwbox, text="Width: ", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_mwbox, textvariable=self.major_w, width=8, bg="#d9d9d9", justify="center", validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_mwbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        _mhbox = tk.Frame(ms_wh, bg="#6f6f6f")
        _mhbox.pack(side="top", pady=2)
        tk.Label(_mhbox, text="Height:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_mhbox, textvariable=self.major_h, width=8, bg="#d9d9d9", justify="center", validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_mhbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # Add/Remove buttons (end of column 2)
        def _ms_refresh_values():
            self._major_combo.configure(values=list(self._major_sizes.keys()))
            # Enable/disable Remove based on count
            if len(self._major_sizes) <= 1:
                self._ms_btn_remove.configure(state="disabled")
            else:
                self._ms_btn_remove.configure(state="normal")

        # Suppress updates when loading from preset
        self._suppress_major_traces = False

        def _ms_load_from_combo(_e=None):
            try:
                sel = self.major_name.get()
                vals = self._major_sizes.get(sel)
                if vals:
                    # Suppress traces for the full batch update
                    self._suppress_major_traces = True
                    try:
                        self.major_x.set(str(vals.get("x", "0")))
                        self.major_y.set(str(vals.get("y", "0")))
                        # Clamp major size to current jig size on preset load
                        try:
                            jx = float(self.jig_x.get() or 0.0)
                            jy = float(self.jig_y.get() or 0.0)
                        except Exception:
                            jx, jy = DEFAULT_JIG_SIZE
                        try:
                            w_val = float((vals.get("w", "0") or "0").strip())
                        except Exception:
                            w_val = 0.0
                        try:
                            h_val = float((vals.get("h", "0") or "0").strip())
                        except Exception:
                            h_val = 0.0
                        # Respect current x,y for this preset when clamping
                        try:
                            x_val = float((vals.get("x", "0") or "0").strip())
                        except Exception:
                            x_val = 0.0
                        try:
                            y_val = float((vals.get("y", "0") or "0").strip())
                        except Exception:
                            y_val = 0.0
                        w_max = max(0.0, float(jx) - max(0.0, x_val))
                        h_max = max(0.0, float(jy) - max(0.0, y_val))
                        w_clamped = max(0.0, min(w_val, w_max))
                        h_clamped = max(0.0, min(h_val, h_max))
                        self.major_w.set(str(w_clamped))
                        self.major_h.set(str(h_clamped))
                        # Persist clamped values back to preset
                        vals["w"] = str(w_clamped)
                        vals["h"] = str(h_clamped)
                        # Load per-major parameters into left bar fields
                        if hasattr(self, "step_x"):
                            self.step_x.set(str(vals.get("step_x", self.step_x.get())))
                        if hasattr(self, "step_y"):
                            self.step_y.set(str(vals.get("step_y", self.step_y.get())))
                        if hasattr(self, "origin_x"):
                            self.origin_x.set(str(vals.get("origin_x", self.origin_x.get())))
                        if hasattr(self, "origin_y"):
                            self.origin_y.set(str(vals.get("origin_y", self.origin_y.get())))
                        if hasattr(self, "slot_w"):
                            self.slot_w.set(str(vals.get("slot_w", self.slot_w.get())))
                        if hasattr(self, "slot_h"):
                            self.slot_h.set(str(vals.get("slot_h", self.slot_h.get())))
                    finally:
                        self._suppress_major_traces = False
                    # After loading preset values, update drawing only if screen is ready
                    if getattr(self, "_screen_ready", False) and hasattr(self, "canvas"):
                        try:
                            self._update_all_majors()
                        except Exception:
                            raise
                        try:
                            if hasattr(self, "_place_slots_all_majors"):
                                self._place_slots_all_majors(silent=True)
                                if hasattr(self, "_refresh_major_visibility"):
                                    self._refresh_major_visibility()
                                if hasattr(self, "_renumber_slots"):
                                    self._renumber_slots()
                        except Exception:
                            raise
            except Exception:
                raise

        def _ms_add():
            try:
                # First, persist current UI values into the currently selected preset
                try:
                    cur_name = (self.major_name.get() or "").strip()
                    if cur_name and cur_name in self._major_sizes:
                        cur = self._major_sizes.get(cur_name) or {}
                        # Avoid overwriting a valid preset with zero/blank fields when adding
                        def _to_f(s):
                            try:
                                return float((s or "0").strip())
                            except Exception:
                                return 0.0
                        ui_x = _to_f(getattr(self, "major_x", tk.StringVar(value="0")).get())
                        ui_y = _to_f(getattr(self, "major_y", tk.StringVar(value="0")).get())
                        ui_w = _to_f(getattr(self, "major_w", tk.StringVar(value="0")).get())
                        ui_h = _to_f(getattr(self, "major_h", tk.StringVar(value="0")).get())
                        cur_x = _to_f(cur.get("x", "0"))
                        cur_y = _to_f(cur.get("y", "0"))
                        cur_w = _to_f(cur.get("w", "0"))
                        cur_h = _to_f(cur.get("h", "0"))
                        ui_has_meaning = any(v != 0.0 for v in (ui_x, ui_y, ui_w, ui_h))
                        cur_is_zero = all(v == 0.0 for v in (cur_x, cur_y, cur_w, cur_h))
                        if ui_has_meaning or cur_is_zero:
                            cur["x"] = (self.major_x.get() or "0").strip()
                            cur["y"] = (self.major_y.get() or "0").strip()
                            cur["w"] = (self.major_w.get() or "0").strip()
                            cur["h"] = (self.major_h.get() or "0").strip()
                            if hasattr(self, "step_x"): cur["step_x"] = (self.step_x.get() or "0").strip()
                            if hasattr(self, "step_y"): cur["step_y"] = (self.step_y.get() or "0").strip()
                            if hasattr(self, "origin_x"): cur["origin_x"] = (self.origin_x.get() or "0").strip()
                            if hasattr(self, "origin_y"): cur["origin_y"] = (self.origin_y.get() or "0").strip()
                            if hasattr(self, "slot_w"): cur["slot_w"] = (self.slot_w.get() or "0").strip()
                            if hasattr(self, "slot_h"): cur["slot_h"] = (self.slot_h.get() or "0").strip()
                            self._major_sizes[cur_name] = cur
                except Exception:
                    raise
                # Compute next available unique name: "Major size N"
                idx = 1
                while True:
                    cand = f"Major size {idx}"
                    if cand not in self._major_sizes:
                        name = cand
                        break
                    idx += 1
                # Create new preset with defaults based on current scene defaults (do not overwrite existing)
                self._major_sizes.setdefault(name, {
                    "x": str(DEFAULT_MAJOR_POS[0]), "y": str(DEFAULT_MAJOR_POS[1]),
                    "w": str(DEFAULT_MAJOR_SIZE[0]), "h": str(DEFAULT_MAJOR_SIZE[1]),
                    "step_x": str(DEFAULT_STEP_SIZE[0]), "step_y": str(DEFAULT_STEP_SIZE[1]),
                    "origin_x": str(DEFAULT_ORIGIN_POS[0]), "origin_y": str(DEFAULT_ORIGIN_POS[1]),
                    "slot_w": str(DEFAULT_SLOT_SIZE[0]), "slot_h": str(DEFAULT_SLOT_SIZE[1]),
                })
                # Refresh list and select the new preset
                _ms_refresh_values()
                self.major_name.set(name)
                try:
                    self._major_combo.set(name)
                except Exception:
                    raise
                # Load saved values into the UI fields for the selected preset
                _ms_load_from_combo()
                # Draw majors after adding
                try:
                    self._update_all_majors()
                except Exception:
                    raise
                # Force brand-new preset to default per-major slot/step/origin values
                try:
                    d = self._major_sizes.get(name) or {}
                    d["step_x"] = str(DEFAULT_STEP_SIZE[0]); d["step_y"] = str(DEFAULT_STEP_SIZE[1])
                    d["origin_x"] = str(DEFAULT_ORIGIN_POS[0]); d["origin_y"] = str(DEFAULT_ORIGIN_POS[1])
                    d["slot_w"] = str(DEFAULT_SLOT_SIZE[0]); d["slot_h"] = str(DEFAULT_SLOT_SIZE[1])
                    self._major_sizes[name] = d
                    # Reflect in UI for immediate clarity
                    self._suppress_major_traces = True
                    try:
                        self.step_x.set(d["step_x"]); self.step_y.set(d["step_y"])
                        self.origin_x.set(d["origin_x"]); self.origin_y.set(d["origin_y"])
                        self.slot_w.set(d["slot_w"]); self.slot_h.set(d["slot_h"])
                    finally:
                        self._suppress_major_traces = False
                except Exception:
                    raise
                # Rebuild slots for all majors so others redraw consistently
                try:
                    self._place_slots_all_majors(silent=True)
                    if hasattr(self, "_refresh_major_visibility"):
                        self._refresh_major_visibility()
                except Exception:
                    raise
                # Inform user
                try:
                    messagebox.showinfo("Major Size", f"Added preset '{name}'.")
                except Exception:
                    raise
            except Exception:
                raise

        def _ms_remove():
            try:
                # Guard: keep at least one preset
                if len(self._major_sizes) <= 1:
                    _ms_refresh_values()
                    return
                name = (self.major_name.get() or "").strip()
                # Remove this major's slots before dropping the preset
                if hasattr(self, "_remove_slots_for_major"):
                    self._remove_slots_for_major(name)
                # Remove all objects (images, rects, text, etc.) owned by this major
                try:
                    owned_object_ids = [
                        cid for cid, meta in list(self._items.items())
                        if str(meta.get("owner_major", "")) == str(name)
                        and str(meta.get("type", "")) not in ("slot", "major")
                    ]
                    for cid in owned_object_ids:
                        meta = self._items.get(cid, {})
                        # Remove rotated overlay polygon for rects
                        try:
                            rid = int(meta.get("rot_id", 0) or 0)
                        except Exception:
                            rid = 0
                        if rid:
                            try:
                                self.canvas.delete(rid)
                            except Exception:
                                pass
                            meta["rot_id"] = None
                        # Remove selection border for images
                        try:
                            bid = int(meta.get("border_id", 0) or 0)
                        except Exception:
                            bid = 0
                        if bid:
                            try:
                                self.canvas.delete(bid)
                            except Exception:
                                pass
                            meta["border_id"] = None
                        try:
                            lbl = meta.get("label_id")
                            if lbl:
                                self.canvas.delete(lbl)
                        except Exception:
                            pass
                        try:
                            self.canvas.delete(cid)
                        except Exception:
                            pass
                        self._items.pop(cid, None)
                except Exception:
                    raise
                # Also purge owned objects from stored scenes for both sides so they don't reappear on toggle
                try:
                    for side in ("front", "back"):
                        items = list(self._scene_store.get(side) or [])
                        self._scene_store[side] = [it for it in items if str(it.get("owner_major", "") or "") != str(name)]
                except Exception:
                    raise
                if name in self._major_sizes:
                    self._major_sizes.pop(name, None)
                    names = list(self._major_sizes.keys())
                    next_name = names[0] if names else ""
                    self.major_name.set(next_name)
                    _ms_refresh_values()
                    _ms_load_from_combo()
                    try:
                        self._update_all_majors()
                    except Exception:
                        raise
                    # Keep visual order sane after deletions
                    try:
                        self._raise_all_labels()
                        self.selection._reorder_by_z()
                    except Exception:
                        pass
                    # After removal, keep other majors as-is; just renumber groups
                    try:
                        self._renumber_slots()
                    except Exception:
                        raise
            except Exception:
                raise

        # On selection change: save current values into previous preset, then load new
        def _on_ms_combo(_e=None):
            try:
                prev = getattr(self, "_major_prev_name", None)
                if prev:
                    # Save UI values into previous preset
                    try:
                        p = self._major_sizes.get(prev)
                        if p is not None:
                            p["x"] = (self.major_x.get() or "0").strip()
                            p["y"] = (self.major_y.get() or "0").strip()
                            p["w"] = (self.major_w.get() or "0").strip()
                            p["h"] = (self.major_h.get() or "0").strip()
                            p["step_x"] = (self.step_x.get() or "0").strip()
                            p["step_y"] = (self.step_y.get() or "0").strip()
                            p["origin_x"] = (self.origin_x.get() or "0").strip()
                            p["origin_y"] = (self.origin_y.get() or "0").strip()
                            p["slot_w"] = (self.slot_w.get() or "0").strip()
                            p["slot_h"] = (self.slot_h.get() or "0").strip()
                    except Exception:
                        raise
            finally:
                self._major_prev_name = (self.major_name.get() or "").strip()
                _ms_load_from_combo()
                # Update active major and visibility when selection changes
                try:
                    self._active_major = (self.major_name.get() or "").strip()
                    if hasattr(self, "_refresh_major_visibility"):
                        self._refresh_major_visibility()
                except Exception:
                    raise

        self._major_combo.bind("<<ComboboxSelected>>", _on_ms_combo)
        # Also react when the variable changes programmatically
        self.major_name.trace_add("write", lambda *_: (_on_ms_combo(), setattr(self, "_active_major", (self.major_name.get() or "")), (getattr(self, "_screen_ready", False) and hasattr(self, "_refresh_major_visibility") and self._refresh_major_visibility()) or None))

        ms_btns = tk.Frame(ms_preset_col, bg="black")
        ms_btns.pack(side="top", pady=0, anchor="w")
        _small_btn_style = ttk.Style()
        _small_btn_style.configure("Small.TButton", font=("Myriad Pro", 9), padding=(0, 1))
        self._ms_btn_add = ttk.Button(ms_btns, text="Add", command=_ms_add, style="Small.TButton", width=6, padding=(10, 0, 10, 0))
        self._ms_btn_add.pack(side="left")
        self._ms_btn_remove = ttk.Button(ms_btns, text="Remove", command=_ms_remove, style="Small.TButton", width=8, padding=(8, 0, 8, 0))
        self._ms_btn_remove.pack(side="left", padx=(5, 0))
        # Initialize remove button state
        _ms_refresh_values()

        # Keep preset in sync with field changes
        def _ms_on_field_change(*_):
            if getattr(self, "_suppress_major_traces", False):
                return
            try:
                name = (self.major_name.get() or "").strip()
                if not name:
                    return
                vals = self._major_sizes.get(name)
                if vals is None:
                    return
                # Clamp width/height to current jig size before persisting
                try:
                    jx = float(self.jig_x.get() or 0.0)
                    jy = float(self.jig_y.get() or 0.0)
                except Exception:
                    jx, jy = DEFAULT_JIG_SIZE
                x_txt = (self.major_x.get() or "0").strip()
                y_txt = (self.major_y.get() or "0").strip()
                w_txt = (self.major_w.get() or "0").strip()
                h_txt = (self.major_h.get() or "0").strip()
                try:
                    w_val = float(w_txt)
                except Exception:
                    w_val = 0.0
                try:
                    h_val = float(h_txt)
                except Exception:
                    h_val = 0.0
                # Respect the current x,y entries when clamping w,h
                try:
                    x_val = float(x_txt)
                except Exception:
                    x_val = 0.0
                try:
                    y_val = float(y_txt)
                except Exception:
                    y_val = 0.0
                w_max = max(0.0, float(jx) - max(0.0, x_val))
                h_max = max(0.0, float(jy) - max(0.0, y_val))
                w_clamped = max(0.0, min(w_val, w_max))
                h_clamped = max(0.0, min(h_val, h_max))
                # Avoid recursive trace triggers while normalizing
                self._suppress_major_traces = True
                try:
                    if str(w_clamped) != w_txt:
                        self.major_w.set(str(w_clamped))
                    if str(h_clamped) != h_txt:
                        self.major_h.set(str(h_clamped))
                finally:
                    self._suppress_major_traces = False
                vals["x"] = x_txt
                vals["y"] = y_txt
                vals["w"] = str(w_clamped)
                vals["h"] = str(h_clamped)
                # live update the one that changed
                self._update_major_rect(name)
            except Exception:
                raise
            # Also reflect updates on the scene major rectangle
            try:
                self._update_major_rect()
            except Exception:
                raise
            # Recreate slots for the active major only on field change; other majors intact
            if hasattr(self, "_place_slots_for_major"):
                self._place_slots_for_major(name, silent=True)
                if hasattr(self, "_renumber_slots"):
                    self._renumber_slots()


        def _ms_on_scene_param_change(*_):
            if getattr(self, "_suppress_major_traces", False):
                return

            name = (self.major_name.get() or "").strip()
            if not name:
                return
            vals = self._major_sizes.get(name)
            if vals is None:
                return
            # If values are empty, seed with defaults for this major instead of copying previous preset
            sx = (self.step_x.get() or "").strip(); sy = (self.step_y.get() or "").strip()
            ox = (self.origin_x.get() or "").strip(); oy = (self.origin_y.get() or "").strip()
            sw = (self.slot_w.get() or "").strip(); sh = (self.slot_h.get() or "").strip()
            vals["step_x"] = sx if sx != "" else str(DEFAULT_STEP_SIZE[0])
            vals["step_y"] = sy if sy != "" else str(DEFAULT_STEP_SIZE[1])
            vals["origin_x"] = ox if ox != "" else str(DEFAULT_ORIGIN_POS[0])
            vals["origin_y"] = oy if oy != "" else str(DEFAULT_ORIGIN_POS[1])
            vals["slot_w"] = sw if sw != "" else str(DEFAULT_SLOT_SIZE[0])
            vals["slot_h"] = sh if sh != "" else str(DEFAULT_SLOT_SIZE[1])


        # Bind after all inputs exist; guard missing attrs for early init paths
        try:
            self.major_x.trace_add("write", _ms_on_field_change)
            self.major_y.trace_add("write", _ms_on_field_change)
            self.major_w.trace_add("write", _ms_on_field_change)
            self.major_h.trace_add("write", _ms_on_field_change)
        except Exception:
            raise
        def _bind_scene_param_traces():
            for _var_name in ("step_x", "step_y", "origin_x", "origin_y", "slot_w", "slot_h"):
                _var = getattr(self, _var_name, None)
                if _var is not None:
                    try:
                        _var.trace_add("write", _ms_on_scene_param_change)
                    except Exception:
                        raise
        # Defer binding until after all StringVars are created
        self.after(0, _bind_scene_param_traces)
        # Also persist on focus-out to be extra safe
        try:
            # Bind globally on self to catch focus changes without referencing vars early
            self.bind_all("<FocusOut>", lambda _e: _ms_on_scene_param_change(), add="+")
        except Exception:
            raise
        # Mark screen as ready after canvas and managers are initialized
        self._screen_ready = True
        # Ensure current preset values populate the UI once all fields exist and screen is ready
        try:
            _ms_load_from_combo()
        except Exception:
            raise

        # Column 5: white vertical separator after Major Size block
        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)

        # Slot size label and fields
        tk.Label(left_bar, text="Slot size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="top", anchor="w", padx=(20, 6), pady=(10, 0))
        self.slot_w = tk.StringVar(value="40.66")
        self.slot_h = tk.StringVar(value="28.9")
        slot_col = tk.Frame(left_bar, bg="black")
        slot_col.pack(side="top", padx=8, pady=8, anchor="w")
        # Slot Width row
        _swbox = tk.Frame(slot_col, bg="#6f6f6f")
        _swbox.pack(side="top", pady=2)
        tk.Label(_swbox, text="Width: ", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_swbox, textvariable=self.slot_w, width=12, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_swbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Slot Height row
        _shbox = tk.Frame(slot_col, bg="#6f6f6f")
        _shbox.pack(side="top", pady=2)
        tk.Label(_shbox, text="Height:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_shbox, textvariable=self.slot_h, width=12, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_shbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # Horizontal separator
        tk.Frame(left_bar, bg="white", height=2).pack(side="top", fill="x", padx=8, pady=6)

        # Origin Pos label and fields
        tk.Label(left_bar, text="Origin Pos:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="top", anchor="w", padx=(8, 6))
        self.origin_x = tk.StringVar(value="11.76")
        self.origin_y = tk.StringVar(value="12.52")
        origin_col = tk.Frame(left_bar, bg="black")
        origin_col.pack(side="top", padx=8, pady=8, anchor="w")
        # Origin X row
        _oxbox = tk.Frame(origin_col, bg="#6f6f6f")
        _oxbox.pack(side="top", pady=2)
        tk.Label(_oxbox, text="X:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_oxbox, textvariable=self.origin_x, width=12, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_oxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Origin Y row
        _oybox = tk.Frame(origin_col, bg="#6f6f6f")
        _oybox.pack(side="top", pady=2)
        tk.Label(_oybox, text="Y:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_oybox, textvariable=self.origin_y, width=12, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_oybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        tk.Frame(left_bar, bg="white", height=2).pack(side="top", fill="x", padx=8, pady=6)
        # Step Size label and fields
        tk.Label(left_bar, text="Step Size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="top", anchor="w", padx=(20, 6))
        self.step_x = tk.StringVar(value="72.55")
        self.step_y = tk.StringVar(value="47.85")
        step_col = tk.Frame(left_bar, bg="black")
        step_col.pack(side="top", padx=8, pady=8, anchor="w")
        # Step X row
        _sxbox = tk.Frame(step_col, bg="#6f6f6f")
        _sxbox.pack(side="top", pady=2)
        tk.Label(_sxbox, text="X:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_sxbox, textvariable=self.step_x, width=12, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_sxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Step Y row
        _sybox = tk.Frame(step_col, bg="#6f6f6f")
        _sybox.pack(side="top", pady=2)
        tk.Label(_sybox, text="Y:", bg="#6f6f6f", fg="white", width=5).pack(side="left", padx=6)
        tk.Entry(_sybox, textvariable=self.step_y, width=12, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_sybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # Ensure first preset mirrors current default scene values (not zeros)
        try:
            if hasattr(self, "_major_sizes") and isinstance(self._major_sizes, dict):
                base = self._major_sizes.get("Major size 1") or {}
                base["step_x"] = (self.step_x.get() or "0").strip()
                base["step_y"] = (self.step_y.get() or "0").strip()
                base["origin_x"] = (self.origin_x.get() or "0").strip()
                base["origin_y"] = (self.origin_y.get() or "0").strip()
                base["slot_w"] = (self.slot_w.get() or "0").strip()
                base["slot_h"] = (self.slot_h.get() or "0").strip()
                # Keep existing major x/y/w/h if present
                base.setdefault("x", (self.major_x.get() if hasattr(self, "major_x") else "0") or "0")
                base.setdefault("y", (self.major_y.get() if hasattr(self, "major_y") else "0") or "0")
                base.setdefault("w", (self.major_w.get() if hasattr(self, "major_w") else "0") or "0")
                base.setdefault("h", (self.major_h.get() if hasattr(self, "major_h") else "0") or "0")
                self._major_sizes["Major size 1"] = base
                try:
                    _ms_refresh_values()
                    _ms_load_from_combo()
                except Exception:
                    raise
                # Ensure initial majors are drawn after defaults
                self._update_all_majors()
        except Exception:
            pass

        # 5) Tools next to the separator
        tools = tk.Frame(bar, bg="black")
        tools.pack(side="left", pady=(8, 0))

        # Load tool icons (keep references on self to avoid GC)
        self._img_cursor = None
        self._img_stick = None
        self._img_image = None
        try:
            self._img_cursor = tk.PhotoImage(file=str(IMAGES_PATH / "cursor.png"))
        except Exception:
            self._img_cursor = None
        try:
            self._img_stick = tk.PhotoImage(file=str(IMAGES_PATH / "stick.png"))
        except Exception:
            self._img_stick = None
        try:
            self._img_image = tk.PhotoImage(file=str(IMAGES_PATH / "image.png"))
        except Exception:
            self._img_image = None

        # Tool tiles like in the screenshot
        # self._create_tool_tile(
        #     tools,
        #     icon_image=self._img_cursor,
        #     icon_text=None,
        #     label_text="Select tool",
        #     command=lambda: None,
        # )
        # New Image import tool tile
        self._create_tool_tile(
            tools,
            icon_image=self._img_image,
            icon_text=None,
            label_text="Image",
            command=self._import_image,
        )
        # Slots are auto-created from inputs; no manual button needed
        self._create_tool_tile(
            tools,
            icon_image=None,
            icon_text="T",
            label_text="Text",
            command=self._drop_text,
        )
        self._create_tool_tile(
            tools,
            icon_image=self._img_stick,
            icon_text=None,
            label_text="Arrange\nobjects",
            command=self._ai_arrange_objects,
        )
        self._create_tool_tile(
            tools,
            icon_image=self._img_stick,
            icon_text=None,
            label_text="Arrange\nmajors",
            command=self._arrange_majors,
        )
        # Help/shortcuts on the right end of the first line
        # Shortcuts on the right end of the top bar
        shortcuts = tk.Frame(bar, bg="black")
        shortcuts.pack(side="right", padx=8, pady=8)
        # 2 columns x 3 rows grid of shortcuts
        shortcuts.grid_columnconfigure(0, weight=0)
        shortcuts.grid_columnconfigure(1, weight=0)

        tk.Label(shortcuts, text="+ / -", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=0, column=0, sticky="e", padx=(0, 0))
        tk.Label(shortcuts, text="→    Zoom in/out", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=0, column=1, sticky="w")

        tk.Label(shortcuts, text="CTRL + Middle Mouse", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=1, column=0, sticky="e", padx=(0, 0))
        tk.Label(shortcuts, text="→    Zoom in/out", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=1, column=1, sticky="w")

        tk.Label(shortcuts, text="Delete", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=2, column=0, sticky="e", padx=(0, 0))
        tk.Label(shortcuts, text="→ Remove object", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=2, column=1, sticky="w")


        row2 = tk.Frame(self, bg="black")
        row2.pack(fill="x", padx=10, pady=(0, 6))
        # Image size label at start of the line
        tk.Label(row2, text="Object:", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(2, 8))
        # Position fields (X, Y) in mm (restored)
        self.sel_x = tk.StringVar(value="0")
        self.sel_y = tk.StringVar(value="0")
        _xb = self._chip(row2, "X:", self.sel_x, width=8)
        tk.Label(_xb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        _yb = self._chip(row2, "Y:", self.sel_y, width=8)
        tk.Label(_yb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Width/Height controls
        self.sel_w = tk.StringVar(value=state.pkg_x or "296.0")
        self.sel_h = tk.StringVar(value=state.pkg_y or "394.5831")
        _wb = self._chip(row2, "Width:", self.sel_w, width=8)
        tk.Label(_wb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        _hb = self._chip(row2, "Height:", self.sel_h, width=8)
        tk.Label(_hb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Angle control (degrees)
        self.sel_angle = tk.StringVar(value="0")
        _ab = self._chip(row2, "Angle:", self.sel_angle, width=6)
        tk.Label(_ab, text="deg", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # Separator and label before Name input
        tk.Frame(row2, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)
        tk.Label(row2, text="Amazon:", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(2, 8))
        # Name control (free text) – added after Angle
        self.sel_amazon_label = tk.StringVar(value="")
        _nb = tk.Frame(row2, bg="#6f6f6f")
        _nb.pack(side="left", padx=6, pady=8)
        tk.Label(_nb, text="Label:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_nb, textvariable=self.sel_amazon_label, width=18, bg="#d9d9d9", justify="center").pack(side="left")
        # Options checkboxes placed after Amazon label
        _flags = tk.Frame(row2, bg="black")
        _flags.pack(side="left", padx=8)
        # Suppress trace callbacks while programmatically updating checkboxes
        self._suppress_flag_traces = False
        self.sel_is_options = tk.BooleanVar(value=False)
        self.sel_is_static = tk.BooleanVar(value=False)
        # ttk.Checkbutton(_flags, variable=self.sel_is_options, text="Is Options").pack(side="left", pady=6, padx=(0,6))
        # ttk.Checkbutton(_flags, variable=self.sel_is_static, text="Is Static").pack(side="left", pady=6)
        # Persist flags into selected object
        def _on_flags_change(*_):
            # Ignore programmatic updates
            if getattr(self, "_suppress_flag_traces", False):
                return
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
        
            self._items[sel]["is_options"] = bool(self.sel_is_options.get())
            self._items[sel]["is_static"] = bool(self.sel_is_static.get())
        self.sel_is_options.trace_add("write", _on_flags_change)
        self.sel_is_static.trace_add("write", _on_flags_change)
        # Persist name into selected object's metadata
        def _on_name_change(*_):
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            self._items[sel]["amazon_label"] = str(self.sel_amazon_label.get() or "").strip()
        self.sel_amazon_label.trace_add("write", _on_name_change)

        # ------- Text styling controls on the last black line -------
        # Moved to FontsManager (UI + logic + storage)
        self.fonts = FontsManager(self)

        # Selection controller (must be created before traces/bindings)
        self._zoom: float = 1.5
        self.selection = CanvasSelection(self)

        # live updates when size/position change
        self.sel_x.trace_add("write", self.selection.on_pos_change)
        self.sel_y.trace_add("write", self.selection.on_pos_change)
        self.sel_w.trace_add("write", self.selection.on_size_change)
        self.sel_h.trace_add("write", self.selection.on_size_change)
        self.sel_angle.trace_add("write", self.selection.on_angle_change)

        right = tk.Frame(row2, bg="black")
        right.pack(side="right", padx=10)
        tk.Label(right, text="Backside", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(0, 6))
        self.backside = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, variable=self.backside).pack(side="left", pady=8)
        # Switch front/back scenes on toggle
        self.backside.trace_add("write", self._on_backside_toggle)

        self.board = tk.Frame(self, bg="black")
        self.board.pack(expand=True, fill="both", padx=10, pady=10)
        # canvas without visible scrollbars
        self.canvas = tk.Canvas(self.board, bg="#5a5a5a", highlightthickness=0, takefocus=1)
        self.canvas.pack(expand=True, fill="both")
        # Managers and method delegations (must be set before bindings)
        # Core state maps used across handlers (must be initialized before any scheduled callbacks)
        self._items: dict[int, CanvasObject] = {}   # canvas_id -> CanvasObject
        # Track major rectangles by preset name -> canvas id
        self._majors: dict[str, int] = {}
        # Per-side scene storage
        self._scene_store: dict[str, list[dict]] = {"front": [], "back": []}
        self._current_side: str = "front"
        # Active major name to filter visibility (items/slots belong to their major)
        self._active_major: str = (self.major_name.get() if hasattr(self, "major_name") else "") or ""
        # Now bind using delegated methods
        self.canvas.bind("<Configure>", self._redraw_jig)
        self.canvas.bind("<Button-1>", self.selection.on_click)
        self.canvas.bind("<Button-1>", lambda _e: self.canvas.focus_set(), add="+")
        # After selection changes, refresh text controls
        self.canvas.bind("<ButtonRelease-1>", lambda _e: self._refresh_text_controls(), add="+")
        self.canvas.bind("<B1-Motion>", self.selection.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.selection.on_release)
        # delete selected with keyboard Delete
        self.canvas.bind("<Delete>", self.selection.on_delete)
        # middle-mouse panning
        self.canvas.bind("<Button-2>", self.selection.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.selection.on_pan_move)
        self.canvas.bind("<ButtonRelease-2>", self.selection.on_pan_end)
        # zoom via Ctrl + MouseWheel / Ctrl + Button-4/5 (Linux)
        self.canvas.bind("<Control-MouseWheel>", self.selection.on_wheel_zoom)
        self.canvas.bind("<Control-Button-4>", lambda _e: self._zoom_step(+1))
        self.canvas.bind("<Control-Button-5>", lambda _e: self._zoom_step(-1))
        # touchpad/scroll wheel panning (vertical + horizontal with Shift)
        self.canvas.bind("<MouseWheel>", self.selection.on_wheel_pan)
        self.canvas.bind("<Button-4>", self.selection.on_wheel_pan)   # Linux up
        self.canvas.bind("<Button-5>", self.selection.on_wheel_pan)   # Linux down
        self.canvas.bind("<Shift-MouseWheel>", self.selection.on_wheel_pan)
        # Zoom via +/- keys only when canvas has focus
        for seq in ("<KeyPress-plus>", "<KeyPress-equal>", "<KP_Add>"):
            self.canvas.bind(seq, lambda _e: self._zoom_step(1))
        for seq in ("<KeyPress-minus>", "<KeyPress-KP_Subtract>"):
            self.canvas.bind(seq, lambda _e: self._zoom_step(-1))
        # initial jig draw (also sets _update_scrollregion delegate before any slot placement)
        self.after(0, self._redraw_jig)
        # initialize jig size from Size fields when no saved size
        self._did_autosize = False
        self.after(0, self._ensure_initial_jig_size)
        # Auto-recreate slots: only for selected major to keep configs per major
        def _recreate_slots_for_selected_major(*_):
            # Skip while preset fields are batch-updated to avoid wiping others
            if getattr(self, "_suppress_major_traces", False):
                return
            try:
                sel = (self.major_name.get() or "").strip()
                if not sel:
                    return
                # Update the selected preset's per-major params
                vals = self._major_sizes.get(sel) or {}
                vals["step_x"] = (self.step_x.get() or "0").strip()
                vals["step_y"] = (self.step_y.get() or "0").strip()
                vals["origin_x"] = (self.origin_x.get() or "0").strip()
                vals["origin_y"] = (self.origin_y.get() or "0").strip()
                vals["slot_w"] = (self.slot_w.get() or "0").strip()
                vals["slot_h"] = (self.slot_h.get() or "0").strip()
                self._major_sizes[sel] = vals
            except Exception:
                raise
            # Recreate slots only for this major
            try:
                self._place_slots_for_major(sel, silent=True)
                self._renumber_slots()
                if hasattr(self, "_refresh_major_visibility"):
                    self._refresh_major_visibility()
            except Exception:
                raise
        self.slot_w.trace_add("write", _recreate_slots_for_selected_major)
        self.slot_h.trace_add("write", _recreate_slots_for_selected_major)
        self.origin_x.trace_add("write", _recreate_slots_for_selected_major)
        self.origin_y.trace_add("write", _recreate_slots_for_selected_major)
        self.step_x.trace_add("write", _recreate_slots_for_selected_major)
        self.step_y.trace_add("write", _recreate_slots_for_selected_major)
        # Draw majors first, then place per-major slots after jig draw/delegates are ready
        def _after_jig_ready():
            self._update_all_majors()
            if hasattr(self, "_update_scrollregion"):
                self._place_slots_all_majors(silent=True)
            # Enforce initial visibility after majors/slots created
            try:
                self._active_major = (self.major_name.get() or "").strip()
            except Exception:
                self._active_major = ""
            if hasattr(self, "_refresh_major_visibility"):
                try:
                    self._refresh_major_visibility()
                except Exception:
                    raise
        self.after(15, _after_jig_ready)

        # Show popup on right-click only when an object is under cursor
        self.canvas.bind("<Button-3>", self.selection.maybe_show_context_menu)

        # Key bindings moved to canvas-level to require focus
        
        
    def _refresh_major_visibility(self) -> None:
        """Keep all majors and all owned items visible; do not hide by active major.
        """
        try:
            for cid, meta in self._items.items():
                t = str(meta.get("type", ""))
                # Majors always visible
                if t == "major":
                    self.canvas.itemconfigure(cid, state="normal")
                    lid = meta.get("label_id")
                    if lid:
                        self.canvas.itemconfigure(lid, state="normal")
                    continue
                # Show everything regardless of owner
                self.canvas.itemconfigure(cid, state="normal")
                lid = meta.get("label_id")
                if lid:
                    self.canvas.itemconfigure(lid, state="normal")
                bid = meta.get("border_id")
                if bid:
                    self.canvas.itemconfigure(bid, state="normal")
                rid = meta.get("rot_id")
                if rid:
                    self.canvas.itemconfigure(rid, state="normal")
            # Maintain label stacking and Z order
            self._raise_all_labels()
            self.selection._reorder_by_z()
        except Exception:
            raise
        # Ensure bottom buttons exist only once
        if not getattr(self, "_bottom_buttons_ready", False):
            back_btn = create_button(
                ButtonInfo(
                    parent=self,
                    text_info=TextInfo(
                        text="Go Back",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    button_color=COLOR_BG_DARK,
                    hover_color="#3f3f3f",
                    active_color=COLOR_BG_DARK,
                    padding_x=20,
                    padding_y=12,
                    command=self.app.go_back,
                )
            )
            back_btn.place(relx=0.005, rely=0.99, anchor="sw")

            proceed_btn = create_button(
                ButtonInfo(
                    parent=self,
                    text_info=TextInfo(
                        text="Proceed",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    button_color=COLOR_BG_DARK,
                    hover_color="#3f3f3f",
                    active_color=COLOR_BG_DARK,
                    padding_x=20,
                    padding_y=12,
                    command=self._proceed,
                )
            )
            proceed_btn.place(relx=0.995, rely=0.99, anchor="se")
            self._bottom_buttons_ready = True

        # Schedule product restore only once to avoid event-loop recursion
        if not getattr(self, "_did_schedule_restore", False):
            self.after(0, self._maybe_load_saved_product)
            self._did_schedule_restore = True

    def _refresh_text_controls(self):
        return self.fonts.refresh_text_controls()

    # UI helpers
    def _snap_mm(self, value: float) -> float:
        """Normalize a millimeter value; allow fractional mm (no integer snapping)."""
        try:
            return float(value)
        except Exception:
            return 0.0

    def _as_bool(self, v) -> bool:
        try:
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0
            s = str(v).strip().lower()
            return s in ("1", "true", "yes", "y", "on")
        except Exception:
            return False

    
    def _raise_all_labels(self):
        # Raise each item's label just above its own base item (not above all items)
        try:
            for cid, meta in self._items.items():
                try:
                    if cid == meta.get("canvas_id") and meta.get("label_id"):
                        lbl_id = meta.get("label_id")
                        if meta.get("type") in ("rect", "major"):
                            # For rects, overlay polygon sits above base; raise label above overlay
                            try:
                                rid = int(meta.get("rot_id", 0) or 0)
                            except Exception:
                                rid = 0
                            if rid:
                                self.canvas.tag_raise(lbl_id, rid)
                            else:
                                self.canvas.tag_raise(lbl_id, cid)
                        elif meta.get("type") == "slot":
                            # For slots, raise label just above slot rect
                            self.canvas.tag_raise(lbl_id, cid)
                        else:
                            # Other types: keep label above their base item
                            self.canvas.tag_raise(lbl_id, cid)
                except Exception as e:
                    logger.exception(f"Failed to raise label above base item: {e}")
        except Exception as e:
            logger.exception(f"Failed to raise all labels: {e}")

    def _find_font_path(self, family: str) -> Optional[str]:
        return self.fonts.find_font_path(family)

    def _update_rect_label_image(self, rect_cid: int) -> None:
        """Render/update a rect's label as a rotated image and center it inside the rect."""
        try:
            meta = self._items.get(rect_cid, {})
            if meta.get("type") != "rect":
                return
            # Current displayed rect bbox and center
            bx = self.canvas.bbox(rect_cid)
            if not bx:
                return
            x1, y1, x2, y2 = bx
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            # Style
            label_text = str(meta.get("label", "Text"))
            try:
                base_pt = int(round(float(meta.get("label_font_size", 10))))
            except Exception:
                base_pt = 10
            size_px = self._scaled_pt(base_pt)
            fill = str(meta.get("label_fill", "#ffffff"))
            family = str(meta.get("label_font_family", "Myriad Pro"))
            try:
                angle = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                angle = 0.0
            try:
                from PIL import Image, ImageDraw, ImageFont, ImageTk  # type: ignore
            except Exception:
                return
            font_path = self._find_font_path(family)
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, max(1, int(size_px)))
                else:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            # Measure text
            tmp = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tmp)
            try:
                tb = draw.textbbox((0, 0), label_text, font=font)
                tw = max(1, tb[2] - tb[0])
                th = max(1, tb[3] - tb[1])
                off_x = -tb[0]
                off_y = -tb[1]
            except Exception:
                try:
                    tw = int(draw.textlength(label_text, font=font))
                    th = max(1, int(size_px * 1.4))
                except Exception:
                    tw, th = max(1, int(size_px * 2)), max(1, int(size_px * 1.4))
                off_x = 0
                off_y = 0
            pad = 0
            img_w = int(tw + 2 * pad)
            img_h = int(th + 2 * pad)
            img = Image.new("RGBA", (max(1, img_w), max(1, img_h)), (0, 0, 0, 0))
            d2 = ImageDraw.Draw(img)
            # Parse hex color
            try:
                if fill.startswith("#") and len(fill) == 7:
                    r = int(fill[1:3], 16); g = int(fill[3:5], 16); b = int(fill[5:7], 16)
                    color_rgba = (r, g, b, 255)
                else:
                    color_rgba = (255, 255, 255, 255)
            except Exception:
                color_rgba = (255, 255, 255, 255)
            d2.text((pad + off_x, pad + off_y), label_text, font=font, fill=color_rgba)
            try:
                # Rotate label image in the same (clockwise) direction as overlay math
                rotated = img.rotate(angle, expand=True, resample=Image.BICUBIC)
            except Exception:
                rotated = img
            try:
                from PIL import ImageTk  # type: ignore
                photo = ImageTk.PhotoImage(rotated)
            except Exception:
                return
            meta["label_photo"] = photo
            lid = int(meta.get("label_id", 0) or 0)
            if lid and str(self.canvas.type(lid)) == "image":
                try:
                    self.canvas.itemconfig(lid, image=photo)
                except Exception:
                    raise
                self.canvas.coords(lid, cx, cy)
            else:
                if lid:
                    try:
                        self.canvas.delete(lid)
                    except Exception:
                        raise
                new_lid = self.canvas.create_image(cx, cy, image=photo, anchor="center")
                meta["label_id"] = new_lid
            # Keep above overlay/base
            try:
                rid = int(meta.get("rot_id", 0) or 0)
            except Exception:
                rid = 0
            try:
                lbl_id = int(meta.get("label_id", 0) or 0)
                if lbl_id:
                    if rid:
                        self.canvas.tag_raise(lbl_id, rid)
                    else:
                        self.canvas.tag_raise(lbl_id, rect_cid)
            except Exception:
                raise
        except Exception:
            logger.exception("Failed to update rotated label image")

    def _chip(self, parent, label, var, width=8):
        box = tk.Frame(parent, bg="#6f6f6f")
        box.pack(side="left", padx=6, pady=8)
        tk.Label(box, text=label, bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(box, textvariable=var, width=width, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        return box

    def _create_tool_tile(self, parent, icon_image: Optional[tk.PhotoImage], icon_text: Optional[str], label_text: str, command):
        """Create a square tile with an icon (image or text) and a label underneath."""
        wrap = tk.Frame(parent, bg="black")
        wrap.pack(side="left", padx=6, pady=6)

        tile_size = 40
        tile = tk.Frame(wrap, bg="#c7c7c7", width=tile_size, height=tile_size, relief="flat", bd=0)
        tile.pack()
        tile.pack_propagate(False)

        if icon_image is not None:
            icon_lbl = tk.Label(tile, image=icon_image, bg="#c7c7c7")
            icon_lbl.pack(expand=True)
        else:
            icon_lbl = tk.Label(tile, text=(icon_text or ""), bg="#c7c7c7", fg="#000000", font=("Myriad Pro", 24, "bold"))
            icon_lbl.pack(expand=True)

        lbl = tk.Label(wrap, text=label_text, fg="white", bg="black", font=("Myriad Pro", 8))
        lbl.pack(pady=(0, 0))

        # Click behavior on tile and its children
        def _on_click(_e=None):
            original_bg = tile.cget("bg")
            pack_info = {}
            pack_info = icon_lbl.pack_info()
            orig_padx = int(pack_info.get("padx", 0) if isinstance(pack_info.get("padx", 0), (int, str)) else 0)
            orig_pady = int(pack_info.get("pady", 0) if isinstance(pack_info.get("pady", 0), (int, str)) else 0)

            def _press():
                tile.configure(bg="#bdbdbd", relief="sunken", bd=1)
                icon_lbl.configure(bg="#bdbdbd")
                icon_lbl.pack_configure(padx=orig_padx + 2, pady=orig_pady + 2)
                tile.after(90, _release)

            def _release():
                tile.configure(bg=original_bg, relief="flat", bd=0)
                icon_lbl.configure(bg=original_bg)
                icon_lbl.pack_configure(padx=orig_padx, pady=orig_pady)
                command()

            _press()

        tile.bind("<Button-1>", _on_click)
        icon_lbl.bind("<Button-1>", _on_click)
        lbl.bind("<Button-1>", _on_click)

        # Improve affordance
        tile.configure(cursor="hand2")
        lbl.configure(cursor="hand2")

    def _import_image(self):
        # Allow selecting and importing multiple images at once
        paths = filedialog.askopenfilenames(
            title="Import Images",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.svg")
            ],
        )
        if not paths:
            return
        # Default size if intrinsic size cannot be inferred
        try:
            default_size = (float(self.sel_w.get()), float(self.sel_h.get()))
        except Exception:
            default_size = (40.0, 50.0)

        for path in paths:
            try:
                if not path or not os.path.exists(path):
                    continue
                size = self._compute_import_size_mm(path) or default_size
                # Create actual image items for all supported formats, including SVG
                self.create_image_item(path, size[0], size[1])
            except Exception as e:
                # Ignore failures per-file to allow batch import to proceed
                logger.exception(f"Failed to import image {path}: {e}")
                continue
        # Refresh ordering/labels after batch import
        self._update_scrollregion()
        self._raise_all_labels()
        self.selection._reorder_by_z()

    def _on_jig_change(self, *_):
        # Redraw jig and re-create slots to fill new area
        self._redraw_jig()
        # Clamp all majors to the new jig size and refresh layout
        try:
            try:
                jx = float(self.jig_x.get() or 0.0)
                jy = float(self.jig_y.get() or 0.0)
            except Exception:
                jx, jy = DEFAULT_JIG_SIZE
            for nm, vals in list(self._major_sizes.items()):
                try:
                    w_val = float((vals.get("w", "0") or "0").strip())
                except Exception:
                    w_val = 0.0
                try:
                    h_val = float((vals.get("h", "0") or "0").strip())
                except Exception:
                    h_val = 0.0
                # Respect each preset's x,y
                try:
                    x_val = float((vals.get("x", "0") or "0").strip())
                except Exception:
                    x_val = 0.0
                try:
                    y_val = float((vals.get("y", "0") or "0").strip())
                except Exception:
                    y_val = 0.0
                w_max = max(0.0, float(jx) - max(0.0, x_val))
                h_max = max(0.0, float(jy) - max(0.0, y_val))
                w_clamped = max(0.0, min(w_val, w_max))
                h_clamped = max(0.0, min(h_val, h_max))
                if str(w_clamped) != str(vals.get("w", "0")) or str(h_clamped) != str(vals.get("h", "0")):
                    vals["w"] = str(w_clamped)
                    vals["h"] = str(h_clamped)
            # Refresh all majors and re-place slots respecting new bounds
            if hasattr(self, "_update_all_majors"):
                self._update_all_majors()
            if hasattr(self, "_place_slots_all_majors"):
                self._place_slots_all_majors(silent=True)
                if hasattr(self, "_renumber_slots"):
                    self._renumber_slots()
        except Exception:
            pass
        # Recreate slots; prefer active major only
        try:
            sel = (self.major_name.get() or "").strip()
        except Exception:
            sel = ""
        if sel and hasattr(self, "_place_slots_for_major"):
            self._place_slots_for_major(sel, silent=True)
            if hasattr(self, "_renumber_slots"):
                self._renumber_slots()
        else:
            self._place_slots_all_majors(silent=True)
            self._renumber_slots()
        # Keep major rectangles clamped within jig
        try:
            self._update_all_majors()
        except Exception:
            raise

    def _maybe_recreate_slots(self):
        try:
            sel = (self.major_name.get() or "").strip()
        except Exception:
            sel = ""
        if sel and hasattr(self, "_place_slots_for_major"):
            self._place_slots_for_major(sel, silent=True)
            if hasattr(self, "_renumber_slots"):
                self._renumber_slots()
        else:
            self._place_slots_all_majors(silent=True)

    def create_placeholder(
        self, 
        label: str, 
        w_mm: float, 
        h_mm: float,
        text_fill: str = "white",
        outline: str = "#d0d0d0",
        x_mm: Optional[float] = None,
        y_mm: Optional[float] = None
    ):
        # place at the center of selected major if available; otherwise center of viewport
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        cx = self.canvas.canvasx(cw // 2)
        cy = self.canvas.canvasy(ch // 2)
        # keep fractional millimeters as provided
        qw_mm = self._snap_mm(w_mm)
        qh_mm = self._snap_mm(h_mm)
        base_w = float(qw_mm) * MM_TO_PX
        base_h = float(qh_mm) * MM_TO_PX
        # honor current zoom when drawing
        scaled_w = base_w * self._zoom
        scaled_h = base_h * self._zoom
        # Ensure top-left sits just inside jig accounting for our item outline
        ox = self._item_outline_half_px()
        oy = self._item_outline_half_px()
        # Base rect is invisible; overlay polygon handles visuals and rotation
        rect = self.canvas.create_rectangle(
            cx - scaled_w / 2 + ox, cy - scaled_h / 2 + oy, cx + scaled_w / 2 - ox, cy + scaled_h / 2 - oy,
            fill="", outline="", width=0
        )
        # Persist position in mm relative to jig for stability on jig resize
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        clamp_left, clamp_top, clamp_right, clamp_bottom = jx0, jy0, jx1, jy1
        # If a major is selected, clamp and center inside it
        owner_try = ""
        try:
            owner_try = str(self.major_name.get()).strip()
        except Exception:
            owner_try = ""
        if owner_try and owner_try in getattr(self, "_majors", {}):
            try:
                mid = int(self._majors.get(owner_try) or 0)
            except Exception:
                mid = 0
            if mid:
                try:
                    mb = self.canvas.bbox(mid)
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
            x_mm = (desired_left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            y_mm = (desired_top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
        # keep fractional mm and align rectangle to provided grid
        sx_mm = self._snap_mm(x_mm)
        sy_mm = self._snap_mm(y_mm)
        new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
        new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
        self.canvas.coords(rect, new_left, new_top, new_left + scaled_w, new_top + scaled_h)
        
        # compute next z to keep newer items above older ones
        max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        obj = CanvasObject(
            type="rect",
            w_mm=float(qw_mm),
            h_mm=float(qh_mm),
            x_mm=float(sx_mm),
            y_mm=float(sy_mm),
            label_id=None,
            outline=outline,
            canvas_id=rect,
            z=int(max_z + 1),
        )
        # Tag ownership: prioritize the selected major; fallback to major under initial placement
        try:
            center_x = new_left + scaled_w / 2.0
            center_y = new_top + scaled_h / 2.0
            owner_hit = ""
            for nm, rid in getattr(self, "_majors", {}).items():
                try:
                    mb = self.canvas.bbox(rid)
                except Exception:
                    mb = None
                if not mb:
                    continue
                mx0, my0, mx1, my1 = float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3])
                if center_x >= mx0 and center_x <= mx1 and center_y >= my0 and center_y <= my1:
                    owner_hit = str(nm)
                    break
            try:
                owner_sel = str(self.major_name.get()).strip()
            except Exception:
                owner_sel = ""
            # Prefer explicitly selected major to avoid wrong ownership when majors overlap
            final_owner = owner_sel or owner_hit
            if final_owner:
                obj["owner_major"] = final_owner
        except Exception:
            raise
        self._items[rect] = obj
        try:
            self._items[rect]["label"] = str(label)
        except Exception:
            raise
        # Create rotated label image now
        try:
            self._update_rect_label_image(rect)
        except Exception:
            logger.exception("Failed to create rotated label image for placeholder")
        # Create initial overlay polygon to visualize rotation/selection consistently
        try:
            self._update_rect_overlay(rect, self._items[rect], new_left, new_top, scaled_w, scaled_h)
        except Exception as e:
            logger.exception(f"Failed to create/update rect overlay: {e}")
        self.selection.select(rect)
        self._update_scrollregion()
        self._raise_all_labels()
        self.selection._reorder_by_z()
        # Enforce visibility per active major
        if hasattr(self, "_refresh_major_visibility"):
            try:
                self._refresh_major_visibility()
            except Exception:
                raise

    def _drop_text(self):
        # Create a square rectangle with a text label inside, so it behaves like images
        default_w = 40.0
        default_h = 40.0
        # Text rectangles use green outline
        self.create_placeholder("Text", default_w, default_h, text_fill="#17a24b", outline="#17a24b")

    def _ai_arrange(self):
        # For backward compatibility, delegate to objects-only arrange within selected major
        return self._ai_arrange_objects()

    def _ai_arrange_objects(self):
        # Hide text menu and clear selection before arranging
        try:
            self.selection.select(None)
        except Exception:
            logger.exception("Failed to deselect before AI arrange")
        try:
            self.text_bar.pack_forget()
            self.row_text.place_forget()
        except Exception:
            logger.exception("Failed to hide text menu before AI arrange")
        # Arrange non-slot items into existing slots.
        # Order for both slots and items: right-to-left within a row, bottom-to-top across rows
        # so the first item goes to the lower-right slot, then leftwards, then rows upwards.

        # Determine active/selected major for scoping
        try:
            active_major = str(self.major_name.get() or "").strip()
        except Exception:
            active_major = ""
        # Collect and order slots by current canvas position, filtered by owner_major
        slot_entries: List[Tuple[float, float, int, CanvasObject]] = []  # (left_px, top_px, slot_cid, slot_meta)
        for scid, smeta in self._items.items():
            if smeta.get("type") != "slot":
                continue
            try:
                if active_major and str(smeta.get("owner_major", "")) != active_major:
                    continue
            except Exception:
                continue
            try:
                bx = self.canvas.bbox(scid)
            except Exception as e:
                logger.exception(f"Failed to get bbox for slot: {e}")
                bx = None
            if not bx:
                continue
            sx, sy, _sx2, _sy2 = bx
            slot_entries.append((float(sx), float(sy), scid, smeta))
        # Sort rows bottom->top (y desc), within row right->left (x desc)
        slot_entries.sort(key=lambda t: (-t[1], -t[0]))

        if not slot_entries:
            return

        # --- New behavior: if slot 1 (by label) in the current major has objects,
        # copy those objects to all other slots in the current major preserving
        # their relative position inside the slot ---
        try:
            slot1_entry = None
            slot1_numeric_candidates: list[tuple[int, tuple]] = []
            for entry in slot_entries:
                _sx, _sy, sid, smeta = entry
                try:
                    lbl_id = smeta.get("label_id")
                    lbl_txt = self.canvas.itemcget(lbl_id, "text") if lbl_id else ""
                except Exception:
                    lbl_txt = ""
                lbl_txt_s = str(lbl_txt).strip()
                num = None
                try:
                    # allow labels like "01"
                    num = int(lbl_txt_s)
                except Exception:
                    num = None
                if num is not None:
                    slot1_numeric_candidates.append((num, entry))
                    if num == 1:
                        slot1_entry = entry
                        break
            if slot1_entry is None and slot1_numeric_candidates:
                # choose the smallest numeric label if no explicit "1" exists
                slot1_entry = sorted(slot1_numeric_candidates, key=lambda p: p[0])[0][1]
            if slot1_entry is None and slot_entries:
                # fallback: first in visual order
                slot1_entry = slot_entries[0]
        except Exception:
            slot1_entry = slot_entries[0] if slot_entries else None

        # Collect template objects currently inside slot 1 (rect/image only)
        did_duplicate = False
        if slot1_entry is not None:
            try:
                _sx, _sy, slot1_id, slot1_meta = slot1_entry
                s1_x = float(slot1_meta.get("x_mm", 0.0))
                s1_y = float(slot1_meta.get("y_mm", 0.0))
                s1_w = float(slot1_meta.get("w_mm", 0.0))
                s1_h = float(slot1_meta.get("h_mm", 0.0))

                # Prefer pixel-space bbox to respect rotation and actual rendered bounds
                try:
                    slot1_bbox_px = self.canvas.bbox(slot1_id)
                except Exception:
                    slot1_bbox_px = None

                def _inside_slot_by_bbox_px(obj_cid: int) -> bool:
                    try:
                        if not slot1_bbox_px:
                            return False
                        bx = self.canvas.bbox(obj_cid)
                        if not bx:
                            return False
                        ox0, oy0, ox1, oy1 = float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])
                        sx0, sy0, sx1, sy1 = float(slot1_bbox_px[0]), float(slot1_bbox_px[1]), float(slot1_bbox_px[2]), float(slot1_bbox_px[3])
                        cx = (ox0 + ox1) / 2.0
                        cy = (oy0 + oy1) / 2.0
                        # Pixel epsilon
                        eps_px = 1.0
                        return (cx >= sx0 - eps_px) and (cx <= sx1 + eps_px) and (cy >= sy0 - eps_px) and (cy <= sy1 + eps_px)
                    except Exception:
                        return False

                template: list[tuple[int, CanvasObject]] = []  # (cid, meta)
                for cid, meta in self._items.items():
                    # Consider only real placeable objects
                    if meta.get("type") not in ("rect", "image", "text"):
                        continue
                    # Duplicate any object whose center lies inside slot 1,
                    # regardless of its current owner_major (some items might
                    # have missing or mismatched ownership).
                    if _inside_slot_by_bbox_px(cid):
                        template.append((cid, meta))

                if template:
                    # Duplicate each template object into all other slots of this major
                    jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
                    oxp = self._item_outline_half_px(); oyp = self._item_outline_half_px()
                    # Preserve relative z-index differences from the template
                    try:
                        template_min_z = min(int(m.get("z", 0)) for _cid, m in template)
                    except Exception:
                        template_min_z = 0
                    try:
                        template_max_z = max(int(m.get("z", 0)) for _cid, m in template)
                    except Exception:
                        template_max_z = template_min_z
                    # Track the current global maximum z to avoid collisions across groups
                    global_max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
                    for _dx, _dy, dest_sid, dest_meta in slot_entries:
                        if dest_sid != slot1_id:
                            # Base z for this destination group; clones will keep their relative diffs
                            base_z = int(global_max_z + 1)
                            dx = float(dest_meta.get("x_mm", 0.0))
                            dy = float(dest_meta.get("y_mm", 0.0))
                            # Clear existing non-slot objects inside this destination slot before cloning
                            # Use destination slot's canvas bounding box in pixels for accurate containment
                            try:
                                dest_bbox_px = self.canvas.bbox(dest_sid)
                            except Exception:
                                dest_bbox_px = None
                            if not dest_bbox_px:
                                logger.exception("Destination slot bbox not available before clearing")
                                raise RuntimeError("Destination slot bbox not available")
                            try:
                                dsx0, dsy0, dsx1, dsy1 = float(dest_bbox_px[0]), float(dest_bbox_px[1]), float(dest_bbox_px[2]), float(dest_bbox_px[3])
                            except Exception:
                                logger.exception("Failed to parse destination slot bbox before clearing")
                                raise
                            try:
                                to_delete_ids: list[int] = []
                                for del_cid, del_meta in list(self._items.items()):
                                    t = del_meta.get("type")
                                    # Only consider objects, not slots or majors. Clear regardless of owner.
                                    consider = (t == "rect") or (t == "image") or (t == "text")
                                    if consider:
                                        try:
                                            bx = self.canvas.bbox(del_cid)
                                            if not bx:
                                                continue
                                            ox0, oy0, ox1, oy1 = float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])
                                            cx = (ox0 + ox1) / 2.0
                                            cy = (oy0 + oy1) / 2.0
                                            # Pixel tolerance
                                            eps_px = 1.0
                                            inside = (cx >= dsx0 - eps_px) and (cx <= dsx1 + eps_px) and (cy >= dsy0 - eps_px) and (cy <= dsy1 + eps_px)
                                        except Exception as e:
                                            logger.exception("Failed to check object position against destination slot")
                                            raise
                                        if inside:
                                            to_delete_ids.append(del_cid)
                                for del_id in to_delete_ids:
                                    m = self._items.get(del_id, {})
                                    try:
                                        # Remove rotated overlay polygon for rects
                                        try:
                                            rid = int(m.get("rot_id", 0) or 0)
                                        except Exception:
                                            rid = 0
                                        if rid:
                                            try:
                                                self.canvas.delete(rid)
                                            except Exception as e:
                                                logger.exception("Failed to delete rect overlay during slot clear")
                                                raise
                                        # Remove selection border for images
                                        try:
                                            bid = int(m.get("border_id", 0) or 0)
                                        except Exception:
                                            bid = 0
                                        if bid:
                                            try:
                                                self.canvas.delete(bid)
                                            except Exception as e:
                                                logger.exception("Failed to delete image border during slot clear")
                                                raise
                                        # Remove label image if exists
                                        try:
                                            lbl = m.get("label_id")
                                            if lbl:
                                                self.canvas.delete(lbl)
                                        except Exception as e:
                                            logger.exception("Failed to delete label during slot clear")
                                            raise
                                        # Remove base item and purge from registry
                                        self.canvas.delete(del_id)
                                        self._items.pop(del_id, None)
                                    except Exception as e:
                                        logger.exception("Failed to clear object inside destination slot")
                                        raise
                            except Exception as e:
                                logger.exception("Failed while clearing destination slot before cloning")
                                raise
                            for _cid, om in template:
                                try:
                                    try:
                                        orig_z = int(om.get("z", 0))
                                    except Exception:
                                        orig_z = 0
                                    assigned_z = int(base_z + (orig_z - template_min_z))
                                    rel_x = float(om.get("x_mm", 0.0)) - s1_x
                                    rel_y = float(om.get("y_mm", 0.0)) - s1_y
                                    nx_mm = dx + rel_x
                                    ny_mm = dy + rel_y
                                    if om.get("type") == "image":
                                        # Create image clone at nx_mm, ny_mm with same size/angle/path
                                        path = str(om.get("path", ""))
                                        if not path:
                                            logger.error("Image source path missing during duplication")
                                            raise RuntimeError("Image source path missing during duplication")
                                        w_mm = float(om.get("w_mm", 0.0))
                                        h_mm = float(om.get("h_mm", 0.0))
                                        ang = float(om.get("angle", 0.0) or 0.0)
                                        w_px = int(round(w_mm * MM_TO_PX * self._zoom))
                                        h_px = int(round(h_mm * MM_TO_PX * self._zoom))
                                        left = jx0 + oxp + nx_mm * MM_TO_PX * self._zoom
                                        top = jy0 + oyp + ny_mm * MM_TO_PX * self._zoom
                                        new_meta = CanvasObject(
                                            type="image",
                                            path=path,
                                            w_mm=float(self._snap_mm(w_mm)),
                                            h_mm=float(self._snap_mm(h_mm)),
                                            x_mm=float(self._snap_mm(nx_mm)),
                                            y_mm=float(self._snap_mm(ny_mm)),
                                            angle=float(ang),
                                        )
                                        # Optional mask
                                        try:
                                            if om.get("mask_path"):
                                                new_meta["mask_path"] = str(om.get("mask_path", ""))
                                        except Exception as e:
                                            logger.exception("Failed to copy mask_path for image clone")
                                            raise
                                        new_meta["amazon_label"] = str(om.get("amazon_label", "") or "")
                                        try:
                                            new_meta["is_options"] = bool(om.get("is_options", False))
                                            new_meta["is_static"] = bool(om.get("is_static", False))
                                        except Exception as e:
                                            logger.exception("Failed to copy image flags for clone")
                                            raise
                                        new_meta["owner_major"] = active_major
                                        photo = self._render_photo(new_meta, max(1, int(w_px)), max(1, int(h_px)))
                                        if photo is None:
                                            logger.error("Failed to render photo for cloned image")
                                            raise RuntimeError("Failed to render photo for cloned image")
                                        try:
                                            bw, bh = self._rotated_bounds_px(w_px, h_px, ang)
                                        except Exception as e:
                                            logger.exception("Failed to compute rotated bounds for cloned image")
                                            raise
                                        place_left = left + (w_px - bw) / 2.0
                                        place_top = top + (h_px - bh) / 2.0
                                        img_id = self.canvas.create_image(place_left, place_top, image=photo, anchor="nw")
                                        new_meta.canvas_id = img_id
                                        new_meta["z"] = assigned_z
                                        self._items[img_id] = new_meta
                                        did_duplicate = True
                                    elif om.get("type") == "text":
                                        # Plain text label clone (center-based coordinates)
                                        try:
                                            txt_val = str(self.canvas.itemcget(_cid, "text"))
                                        except Exception as e:
                                            logger.exception("Failed to read source text for cloning")
                                            raise
                                        try:
                                            fill_val = str(om.get("default_fill", self.canvas.itemcget(_cid, "fill") or "white"))
                                        except Exception:
                                            fill_val = "white"
                                        tid = self._create_text_at_mm(
                                            txt_val,
                                            nx_mm,
                                            ny_mm,
                                            fill=fill_val,
                                        )
                                        if tid in self._items:
                                            try:
                                                self._items[tid]["amazon_label"] = str(om.get("amazon_label", "") or "")
                                                self._items[tid]["is_options"] = bool(om.get("is_options", False))
                                                self._items[tid]["is_static"] = bool(om.get("is_static", False))
                                            except Exception as e:
                                                logger.exception("Failed to copy text flags for clone")
                                                raise
                                            self._items[tid]["owner_major"] = active_major
                                            # Copy font styling if present on source
                                            try:
                                                fam = str(om.get("font_family", "Myriad Pro")) if om.get("font_family", None) is not None else None
                                                fpt = int(round(float(om.get("font_size_pt", 12)))) if om.get("font_size_pt", None) is not None else None
                                                if fam is not None:
                                                    self._items[tid]["font_family"] = fam
                                                if fpt is not None:
                                                    self._items[tid]["font_size_pt"] = int(fpt)
                                                if fam is not None or fpt is not None:
                                                    use_fam = fam if fam is not None else self._items[tid].get("font_family", "Myriad Pro")
                                                    use_pt = fpt if fpt is not None else int(self._items[tid].get("font_size_pt", 12))
                                                    self.canvas.itemconfig(tid, font=(use_fam, self._scaled_pt(use_pt), "bold"))
                                            except Exception as e:
                                                logger.exception("Failed to apply text font on clone")
                                                raise
                                            # z-order: preserve relative offset
                                            self._items[tid]["z"] = assigned_z
                                            did_duplicate = True
                                    else:
                                        # Rectangle/text block clone
                                        try:
                                            label_text = str(om.get("label", "Text"))
                                        except Exception:
                                            label_text = "Text"
                                        outline = str(om.get("outline", "#d0d0d0"))
                                        ang = float(om.get("angle", 0.0) or 0.0)
                                        rw = float(om.get("w_mm", 0.0))
                                        rh = float(om.get("h_mm", 0.0))
                                        rid = self._create_rect_at_mm(
                                            label_text,
                                            rw,
                                            rh,
                                            nx_mm,
                                            ny_mm,
                                            outline=outline,
                                            text_fill=str(om.get("label_fill", "#ffffff")),
                                            angle=ang,
                                        )
                                        if rid in self._items:
                                            self._items[rid]["z"] = assigned_z
                                            self._items[rid]["amazon_label"] = str(om.get("amazon_label", "") or "")
                                            try:
                                                self._items[rid]["is_options"] = bool(om.get("is_options", False))
                                                self._items[rid]["is_static"] = bool(om.get("is_static", False))
                                            except Exception as e:
                                                logger.exception("Failed to copy rect flags for clone")
                                                raise
                                            self._items[rid]["owner_major"] = active_major
                                            # Copy label styling for text-rects
                                            try:
                                                label_fill_val = om.get("label_fill", None)
                                                if label_fill_val is not None:
                                                    self._items[rid]["label_fill"] = str(label_fill_val)
                                                label_font_size_val = om.get("label_font_size", None)
                                                if label_font_size_val is not None:
                                                    self._items[rid]["label_font_size"] = int(round(float(label_font_size_val)))
                                                label_font_family_val = om.get("label_font_family", None)
                                                if label_font_family_val is not None:
                                                    self._items[rid]["label_font_family"] = str(label_font_family_val)
                                                # Also copy rect outline color
                                                outline_val = om.get("outline", None)
                                                if outline_val is not None:
                                                    self._items[rid]["outline"] = str(outline_val)
                                                self._update_rect_label_image(rid)
                                            except Exception as e:
                                                logger.exception("Failed to copy rect styling for clone")
                                                raise
                                        did_duplicate = True
                                except Exception:
                                    logger.exception("Failed while duplicating an object into a slot")
                                    raise
                            # Update global_max_z after finishing this group, to avoid z collisions for the next group
                            try:
                                global_max_z = max(global_max_z, int(base_z + (template_max_z - template_min_z)))
                            except Exception:
                                global_max_z = max(global_max_z, base_z)
            except Exception:
                did_duplicate = False

        if did_duplicate:
            self._update_scrollregion()
            self._raise_all_labels()
            self.selection._reorder_by_z()
            self._redraw_jig(center=False)
            # Keep text menu hidden
            self.text_bar.pack_forget()
            self.row_text.place_forget()
            return

        # Collect placeable items (rect or image), ordered bottom->top, right->left, filtered by owner_major
        item_entries: List[Tuple[float, float, int, CanvasObject]] = []  # (left_px, top_px, cid, meta)
        for cid, meta in self._items.items():
            if meta.get("type") not in ("rect", "image"):
                continue
            try:
                if active_major and str(meta.get("owner_major", "")) != active_major:
                    continue
            except Exception:
                continue
            try:
                bx = self.canvas.bbox(cid)
            except Exception as e:
                logger.exception(f"Failed to get bbox for item {cid}: {e}")
                bx = None
            if not bx:
                # For images sometimes bbox can be None until drawn; use coords as fallback
                try:
                    cx, cy = self.canvas.coords(cid)
                    bx = (float(cx), float(cy), float(cx), float(cy))
                except Exception as e:
                    logger.exception(f"Failed to get coords for item {cid}: {e}")
                    continue
            ix, iy, _ix2, _iy2 = bx
            item_entries.append((float(ix), float(iy), cid, meta))
        item_entries.sort(key=lambda t: (-t[1], -t[0]))

        # Map items to slots one-to-one
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        ox = self._item_outline_half_px()
        oy = self._item_outline_half_px()
        for idx, (_ix, _iy, cid, meta) in enumerate(item_entries):
            if idx >= len(slot_entries):
                break
            _sx_px, _sy_px, slot_cid, slot_meta = slot_entries[idx]
            item_w_mm = float(meta.get("w_mm", 0.0))
            item_h_mm = float(meta.get("h_mm", 0.0))
            x_mm = float(slot_meta.get("x_mm", 0.0))
            y_mm = float(slot_meta.get("y_mm", 0.0))

            # Slot size in mm
            slot_w_mm = float(slot_meta.get("w_mm", 0.0))
            slot_h_mm = float(slot_meta.get("h_mm", 0.0))
            
            # Consider rotation when fitting and centering (work in mm)
            try:
                ang = float(meta.get("angle", 0.0) or 0.0)
            except Exception:
                ang = 0.0
            # Force images and text blocks (rect) to be rotated to 270 degrees before processing/placement
            if meta.get("type") == "image":
                ang = 270.0
                meta["angle"] = 270.0
            elif meta.get("type") == "rect":
                ang = -270.0
                meta["angle"] = -270.0

            if meta.get("type") == "image":
                # Fit rotated bbox into slot in mm
                bw_mm, bh_mm = self._rotated_bounds_mm(item_w_mm, item_h_mm, ang)
                if bw_mm > slot_w_mm or bh_mm > slot_h_mm:
                    scale = min(slot_w_mm / float(max(1e-6, bw_mm)), slot_h_mm / float(max(1e-6, bh_mm)))
                    item_w_mm *= scale
                    item_h_mm *= scale
                    meta["w_mm"] = float(item_w_mm)
                    meta["h_mm"] = float(item_h_mm)
                    bw_mm, bh_mm = self._rotated_bounds_mm(item_w_mm, item_h_mm, ang)
                left_mm = x_mm + (slot_w_mm - bw_mm) / 2.0
                top_mm = y_mm + (slot_h_mm - bh_mm) / 2.0
                # Clamp within jig in mm (jx/jy are jig size in mm)
                try:
                    jx = float(self.jig_x.get() or 0.0)
                    jy = float(self.jig_y.get() or 0.0)
                except Exception:
                    jx, jy = 296.0, 394.5831
                left_mm = max(0.0, min(left_mm, (jx - bw_mm)))
                top_mm = max(0.0, min(top_mm, (jy - bh_mm)))
                # Convert to px for drawing
                w_px = int(round(item_w_mm * MM_TO_PX * self._zoom))
                h_px = int(round(item_h_mm * MM_TO_PX * self._zoom))
                bw_px = int(round(bw_mm * MM_TO_PX * self._zoom))
                bh_px = int(round(bh_mm * MM_TO_PX * self._zoom))
                left = jx0 + ox + left_mm * MM_TO_PX * self._zoom
                top = jy0 + oy + top_mm * MM_TO_PX * self._zoom
                # Render and place using visual top-left
                photo = self._render_photo(meta, max(1, int(w_px)), max(1, int(h_px)))
                if photo is not None:
                    self.canvas.itemconfig(cid, image=photo)
                self.canvas.coords(cid, left, top)
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, left, top, left + bw_px, top + bh_px)
                # Persist mm top-left
                meta.x_mm = float(left_mm)
                meta.y_mm = float(top_mm)
            else:
                # Rect/text block - display dims swap at 90/270
                disp_w_mm = item_w_mm
                disp_h_mm = item_h_mm
                if int(abs(ang)) % 180 == 90:
                    disp_w_mm, disp_h_mm = item_h_mm, item_w_mm
                # Fit if needed
                if disp_w_mm > slot_w_mm or disp_h_mm > slot_h_mm:
                    scale = min(slot_w_mm / float(max(1e-6, disp_w_mm)), slot_h_mm / float(max(1e-6, disp_h_mm)))
                    item_w_mm *= scale
                    item_h_mm *= scale
                    meta["w_mm"] = float(item_w_mm)
                    meta["h_mm"] = float(item_h_mm)
                    disp_w_mm, disp_h_mm = (item_h_mm, item_w_mm) if (int(abs(ang)) % 180 == 90) else (item_w_mm, item_h_mm)
                left_mm = x_mm + (slot_w_mm - disp_w_mm) / 2.0
                top_mm = y_mm + (slot_h_mm - disp_h_mm) / 2.0
                try:
                    jx = float(self.jig_x.get() or 0.0)
                    jy = float(self.jig_y.get() or 0.0)
                except Exception:
                    jx, jy = DEFAULT_JIG_SIZE
                left_mm = max(0.0, min(left_mm, jx - disp_w_mm))
                top_mm = max(0.0, min(top_mm, jy - disp_h_mm))
                # Draw with px
                disp_w = int(round(disp_w_mm * MM_TO_PX * self._zoom))
                disp_h = int(round(disp_h_mm * MM_TO_PX * self._zoom))
                left = jx0 + ox + left_mm * MM_TO_PX * self._zoom
                top = jy0 + oy + top_mm * MM_TO_PX * self._zoom
                self.canvas.coords(cid, left, top, left + disp_w, top + disp_h)
                lbl_id = meta.get("label_id")
                if lbl_id:
                    self.canvas.coords(lbl_id, left + disp_w / 2.0, top + disp_h / 2.0)
                # update overlay
                self._update_rect_overlay(cid, meta, left, top, disp_w, disp_h)
                # re-render label image to reflect new rotation
                try:
                    self._update_rect_label_image(cid)
                except Exception:
                    raise
                self._raise_all_labels()
                # Persist mm top-left
                meta.x_mm = float(left_mm)
                meta.y_mm = float(top_mm)

        self._redraw_jig(center=False)
        self.selection._reorder_by_z()
        # Ensure text controls remain hidden after arrange
        try:
            self.text_bar.pack_forget()
            self.row_text.place_forget()
        except Exception:
            logger.exception("Failed to hide text menu after AI arrange")

    def _arrange_majors(self):
        """Pack major rectangles within the jig area to minimize wasted space and refresh per-major slots.

        Strategy: skyline bottom-left packing with 5mm jig margin and 2mm inter-major padding.
        Keeps each major's width/height, only updates x/y.
        """
        # Deselect and hide text controls for clarity
        try:
            self.selection.select(None)
        except Exception:
            pass
        try:
            self.text_bar.pack_forget()
            self.row_text.place_forget()
        except Exception:
            pass
        # Read jig size in mm
        try:
            jx = float(self.jig_x.get() or 0.0)
            jy = float(self.jig_y.get() or 0.0)
        except Exception:
            jx, jy = 296.0, 394.5831
        if jx <= 0.0 or jy <= 0.0:
            return
        # Jig boundary margin and inter-major padding (mm)
        margin = 5.0
        pad = 2.0

        # Effective container for packing (inner jig minus margins). To allow majors to be flush
        # to the inner boundary without extra padding, extend container by `pad` because we inflate
        # each major by `pad` while packing.
        inner_w = max(0.0, jx - 2.0 * margin)
        inner_h = max(0.0, jy - 2.0 * margin)
        if inner_w <= 0.0 or inner_h <= 0.0:
            return
        W = inner_w + pad
        H = inner_h + pad

        # Gather majors (skip invalid sizes)
        try:
            def _order_key(k: str) -> tuple:
                import re as __re
                m = __re.search(r"(\d+)$", k)
                n = int(m.group(1)) if m else 10**9
                return (n, k)
            ordered = sorted(list(self._major_sizes.keys()), key=_order_key)
        except Exception:
            ordered = list(self._major_sizes.keys())
        if not ordered:
            return

        rects: list[tuple[str, float, float]] = []
        for nm in ordered:
            vals = self._major_sizes.get(nm) or {}
            try:
                mw = float(vals.get("w", 0.0) or 0.0)
                mh = float(vals.get("h", 0.0) or 0.0)
            except Exception:
                mw, mh = 0.0, 0.0
            if mw > 0.0 and mh > 0.0 and mw <= inner_w and mh <= inner_h:
                rects.append((nm, mw, mh))

        if not rects:
            return

        # Sort by height desc, then width desc for better shelf utilization with skyline
        rects.sort(key=lambda it: (-it[2], -it[1]))

        # Skyline nodes: list of (x, y); initially floor line
        skyline: list[tuple[float, float]] = [(0.0, 0.0), (W, 0.0)]

        def _find_position(w_in: float, h_in: float) -> Optional[tuple[float, float, int, float]]:
            """Find bottom-left position for rectangle of size (w_in, h_in).
            Returns (x, y, start_index, right_height) or None if not fit.
            Uses inflated sizes (w_in, h_in) which already include `pad`.
            """
            best_y = float("inf"); best_x = 0.0
            best_idx = -1; best_right_h = 0.0
            # Scan each skyline node as potential start
            for i in range(len(skyline) - 1):
                x0, y0 = skyline[i]
                # Early prune if x0 beyond packing width
                if x0 + w_in > W + 1e-9:
                    continue
                j = i
                width_left = w_in
                y_pos = y0
                # Walk segments until we cover needed width
                while width_left > 0.0:
                    if j >= len(skyline) - 1:
                        y_pos = float("inf"); break
                    seg_w = skyline[j + 1][0] - skyline[j][0]
                    y_pos = max(y_pos, skyline[j][1])
                    if y_pos + h_in > H + 1e-9:
                        y_pos = float("inf"); break
                    if seg_w >= width_left:
                        # Fits within current and following segments
                        right_h = skyline[j][1]
                        break
                    width_left -= seg_w
                    j += 1
                if y_pos == float("inf"):
                    continue
                # Bottom-left rule: choose the lowest y, then leftmost x
                if y_pos < best_y - 1e-9 or (abs(y_pos - best_y) <= 1e-9 and x0 < best_x - 1e-9):
                    best_y = y_pos; best_x = x0; best_idx = i; best_right_h = skyline[j][1]
            if best_idx < 0:
                return None
            return (best_x, best_y, best_idx, best_right_h)

        def _merge_skyline() -> None:
            # Remove consecutive nodes with the same height
            k = 0
            while k < len(skyline) - 1:
                if abs(skyline[k][1] - skyline[k + 1][1]) <= 1e-9:
                    skyline.pop(k + 1)
                else:
                    k += 1

        # Overlap check in inner coords (mm), padding applies to the moving rect only
        def _overlaps(ax: float, ay: float, aw: float, ah: float,
                      bx: float, by: float, bw: float, bh: float,
                      pad_mm: float = 0.0) -> bool:
            ax0, ay0, ax1, ay1 = ax - pad_mm, ay - pad_mm, ax + aw + pad_mm, ay + ah + pad_mm
            bx0, by0, bx1, by1 = bx, by, bx + bw, by + bh
            return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)

        # Discrete candidate search using edges of placed rects (bottom-left order)
        def _edge_search(mw: float, mh: float, placed: list[tuple[float, float, float, float]]) -> tuple[float, float] | None:
            xs = {0.0}
            ys = {0.0}
            for px, py, pw, ph in placed:
                xs.add(px)
                xs.add(px + pw + pad)
                ys.add(py)
                ys.add(py + ph + pad)
            for y in sorted(ys):
                for x in sorted(xs):
                    if x + mw + pad > W + 1e-9 or y + mh + pad > H + 1e-9:
                        continue
                    ok = True
                    for ox, oy, ow, oh in placed:
                        if _overlaps(x, y, mw, mh, ox, oy, ow, oh, pad_mm=pad):
                            ok = False
                            break
                    if ok:
                        return (x, y)
            return None

        placements: dict[str, tuple[float, float, float, float]] = {}
        placed_list: list[tuple[float, float, float, float]] = []  # inner coords mm
        for nm, mw, mh in rects:
            w_in = mw + pad
            h_in = mh + pad
            pos = _find_position(w_in, h_in)
            if pos is None:
                # Try discrete edge-based search before giving up
                found = _edge_search(mw, mh, placed_list)
                if found is None:
                    # As a last resort, keep old position only if it does not collide with already placed
                    vals = self._major_sizes.get(nm) or {}
                    try:
                        ox = float(vals.get("x", margin) or margin)
                        oy = float(vals.get("y", margin) or margin)
                    except Exception:
                        ox, oy = margin, margin
                    # Convert to inner coords
                    oxi = max(0.0, min(ox - margin, inner_w - mw))
                    oyi = max(0.0, min(oy - margin, inner_h - mh))
                    collided = any(_overlaps(oxi, oyi, mw, mh, px, py, pw, ph, pad_mm=pad) for (px, py, pw, ph) in placed_list)
                    if collided:
                        # Cannot place safely; preserve old position but include it in occupancy
                        ax = margin + oxi
                        ay = margin + oyi
                        placements[nm] = (ax, ay, mw, mh)
                        placed_list.append((oxi, oyi, mw, mh))
                        continue
                    x0, y0 = oxi, oyi
                    # No skyline update when using fallback; just record placement
                    ax = margin + x0
                    ay = margin + y0
                    placements[nm] = (ax, ay, mw, mh)
                    placed_list.append((x0, y0, mw, mh))
                    continue
                else:
                    x0, y0 = found
                    # No precomputed skyline indices for edge search; we won't modify skyline but record placement
                    ax = margin + x0
                    ay = margin + y0
                    placements[nm] = (ax, ay, mw, mh)
                    placed_list.append((x0, y0, mw, mh))
                    continue
            else:
                x0, y0, idx, right_h = pos
                # Update skyline: insert node at x0 with height y0 + h_in, remove covered, then add node at x1
                new_h = y0 + h_in
                x1 = x0 + w_in
                # Insert/replace at position idx
                if abs(skyline[idx][0] - x0) <= 1e-9:
                    skyline[idx] = (x0, new_h)
                else:
                    skyline.insert(idx + 1, (x0, new_h))
                    idx += 1
                # Remove nodes fully covered by [x0, x1)
                k = idx + 1
                while k < len(skyline) and skyline[k][0] <= x1 + 1e-9:
                    k += 1
                skyline[idx + 1:k] = []
                # Ensure a node at x1 with the previous right-side height
                if idx + 1 < len(skyline) and abs(skyline[idx + 1][0] - x1) <= 1e-9:
                    skyline[idx + 1] = (x1, right_h)
                else:
                    skyline.insert(idx + 1, (x1, right_h))
                _merge_skyline()
                # Record actual mm placement (remove padding, add jig margin)
                ax = margin + x0
                ay = margin + y0
                placements[nm] = (ax, ay, mw, mh)
                placed_list.append((x0, y0, mw, mh))

        # Capture old positions in mm BEFORE persisting new ones
        old_mm: dict[str, tuple[float, float]] = {}
        for nm in [nm for (nm, _w, _h) in rects]:
            try:
                v0 = self._major_sizes.get(nm) or {}
                ox = float(v0.get("x", 0.0) or 0.0)
                oy = float(v0.get("y", 0.0) or 0.0)
            except Exception:
                ox, oy = 0.0, 0.0
            old_mm[nm] = (ox, oy)

        # Persist updated positions back to presets
        for nm, (px, py, mw, mh) in placements.items():
            vals = self._major_sizes.get(nm) or {}
            # Clamp within jig bounds just in case
            px = max(margin, min(px, jx - margin - mw))
            py = max(margin, min(py, jy - margin - mh))
            vals["x"], vals["y"] = str(float(px)), str(float(py))
            self._major_sizes[nm] = vals

        # Apply updates to canvas and refresh slots per major
        try:
            # Temporarily suppress child shifts while we reposition majors in bulk
            self._suppress_major_child_shift = True
            self._update_all_majors()
        finally:
            try:
                self._suppress_major_child_shift = False
            except Exception:
                pass

        # Shift children of each major by the delta we applied to the major
        try:
            if hasattr(self, "selection") and hasattr(self.selection, "_shift_children_for_major"):
                from src.core import MM_TO_PX as __MM_TO_PX
                for nm, (nx, ny, _mw, _mh) in placements.items():
                    ox, oy = old_mm.get(nm, (nx, ny))
                    dx_mm = float(nx) - float(ox)
                    dy_mm = float(ny) - float(oy)
                    if abs(dx_mm) < 1e-9 and abs(dy_mm) < 1e-9:
                        continue
                    dx_px = float(dx_mm) * float(__MM_TO_PX) * float(getattr(self, "_zoom", 1.0))
                    dy_px = float(dy_mm) * float(__MM_TO_PX) * float(getattr(self, "_zoom", 1.0))
                    self.selection._shift_children_for_major(str(nm), dx_px, dy_px, dx_mm, dy_mm)
        except Exception:
            pass

        # Update entries for currently selected major to reflect new x/y
        try:
            active_major = str(self.major_name.get() or "").strip()
        except Exception:
            active_major = ""
        if active_major and active_major in self._major_sizes:
            try:
                vals = self._major_sizes.get(active_major) or {}
                nx = str(vals.get("x", "0"))
                ny = str(vals.get("y", "0"))
                self._suppress_major_traces = True
                if hasattr(self, "major_x"):
                    self.major_x.set(str(nx))
                if hasattr(self, "major_y"):
                    self.major_y.set(str(ny))
            except Exception:
                pass
            finally:
                try:
                    self._suppress_major_traces = False
                except Exception:
                    pass
        try:
            if hasattr(self, "_place_slots_all_majors"):
                self._place_slots_all_majors(silent=True)
                if hasattr(self, "_renumber_slots"):
                    self._renumber_slots()
        except Exception:
            pass
        try:
            if hasattr(self, "_refresh_major_visibility"):
                self._refresh_major_visibility()
        except Exception:
            pass
        self.selection._reorder_by_z()

    def _compute_import_size_mm(self, path: str) -> Optional[Tuple[float, float]]:
        """Infer intrinsic image size in mm.
        - SVG: parse viewBox or width/height attributes
        - Raster: prefer Pillow; fallback to tk.PhotoImage; final fallback parses PNG header
        Returns (w_mm, h_mm) or None.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg":
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"viewBox\s*=\s*\"\s*[\d\.-]+\s+[\d\.-]+\s+([\d\.-]+)\s+([\d\.-]+)\s*\"", text)
                if m:
                    w_px = float(m.group(1))
                    h_px = float(m.group(2))
                    return (w_px / MM_TO_PX, h_px / MM_TO_PX)
                mw = re.search(r"width\s*=\s*\"\s*([\d\.]+)\s*(px|mm|cm|in)?\s*\"", text)
                mh = re.search(r"height\s*=\s*\"\s*([\d\.]+)\s*(px|mm|cm|in)?\s*\"", text)
                if mw and mh:
                    w_val, w_unit = float(mw.group(1)), (mw.group(2) or "px")
                    h_val, h_unit = float(mh.group(1)), (mh.group(2) or "px")
                    if w_unit == "mm" and h_unit == "mm":
                        return (w_val, h_val)
                    if w_unit == "cm" and h_unit == "cm":
                        return (w_val * 10.0, h_val * 10.0)
                    if w_unit == "in" and h_unit == "in":
                        return (w_val * 25.4, h_val * 25.4)
                    # assume px
                    return (w_val / MM_TO_PX, h_val / MM_TO_PX)
            except Exception as e:
                logger.exception(f"Failed to parse SVG dimensions: {e}")
            return None
        # Raster: Pillow first
        try:
            from PIL import Image  # type: ignore
            with Image.open(path) as im:
                w_px, h_px = im.size
            return (float(w_px) / MM_TO_PX, float(h_px) / MM_TO_PX)
        except Exception as e:
            logger.exception(f"Failed to get image size with Pillow: {e}")
        # Fallback to tk.PhotoImage (PNG/GIF)
        try:
            img = tk.PhotoImage(file=path)
            w_px, h_px = int(img.width()), int(img.height())
            return (float(w_px) / MM_TO_PX, float(h_px) / MM_TO_PX)
        except Exception as e:
            logger.exception(f"Failed to get image size with tk.PhotoImage: {e}")
        # Last resort: parse PNG IHDR
        try:
            with open(path, 'rb') as f:
                sig = f.read(8)
                if sig == b'\x89PNG\r\n\x1a\n':
                    chunk_len = struct.unpack('>I', f.read(4))[0]
                    chunk_type = f.read(4)
                    if chunk_type == b'IHDR' and chunk_len >= 8:
                        w_px, h_px = struct.unpack('>II', f.read(8))
                        return (float(w_px) / MM_TO_PX, float(h_px) / MM_TO_PX)
        except Exception as e:
            logger.exception(f"Failed to parse PNG header: {e}")
        return None

    

    def _ensure_initial_jig_size(self):
        # If no saved jig size, initialize from Size fields (defaults 59x80)
        if self._did_autosize:
            return
        if state.pkg_x or state.pkg_y:
            self._did_autosize = True
            return
        try:
            jx = float(self.sel_w.get())
            jy = float(self.sel_h.get())
        except Exception as e:
            logger.exception(f"Failed to get jig size from fields: {e}")
            # fallback to safe defaults
            jx, jy = 296.0, 394.5831
        # Preserve fractional values; avoid coercing to integers
        self.jig_x.set(str(jx))
        self.jig_y.set(str(jy))
        self._did_autosize = True

    def _proceed(self):
        # Сохраняем актуальные значения перед переходом
        # 2/3 mirrored for non-sticker flow
        sku_val = self.sku_var.get().strip()
        if not sku_val:
            messagebox.showwarning("Missing SKU", "Please select an SKU before proceeding.")
            return
        if len(sku_val) < 3:
            messagebox.showwarning("Invalid SKU", "SKU doesn't exist.")
            return
        state.sku = sku_val
        
        sku_name_val = self.sku_name_var.get().strip()
        if not sku_name_val:
            messagebox.showwarning("Missing SKU", "Please select an SKU name before proceeding.")
            return
        if len(sku_name_val) < 3:
            messagebox.showwarning("Invalid SKU", "SKU doesn't exist.")
            return

        state.sku_name = sku_name_val
        state.pkg_x = self.jig_x.get().strip()
        state.pkg_y = self.jig_y.get().strip()
        # Count only image items. Text items are stored with type 'text'
        # Snapshot current side (exclude slots) so both sides are up-to-date
        current_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
        self._scene_store[self._current_side] = current_no_slots
        # Collect slots from the current canvas (slots are shared across sides)
        slots_only = [it for it in self._serialize_scene() if it.get("type") == "slot"]
        # Prepare background job to render PDFs and write JSON without blocking UI
        p_jig = os.path.join(TEMP_FOLDER, "Cut_jig.svg")
        p_pattern = os.path.join(TEMP_FOLDER, "Single_pattern.svg")
        p_front = os.path.join(TEMP_FOLDER, "Test_file_frontside.pdf")
        p_back = os.path.join(TEMP_FOLDER, "Test_file_backside.pdf")
        try:
            jx = float(self.jig_x.get() or 0.0)
            jy = float(self.jig_y.get() or 0.0)
        except Exception:
            jx, jy = 296.0, 394.5831
        front_items = list(slots_only) + list(self._scene_store.get("front") or [])
        back_items = list(slots_only) + list(self._scene_store.get("back") or [])

        # Ensure images are stored internally per product and update paths
        try:
            import shutil as _shutil
            from pathlib import Path as _Path
            product_folder = PRODUCTS_PATH / (state.sku_name or "Product")
            product_folder.mkdir(parents=True, exist_ok=True)

            def _rewrite_and_copy_images(items_list: list[dict]) -> None:
                for _it in items_list:
                    try:
                        if str(_it.get("type", "")) != "image":
                            continue
                        src_path_str = str(_it.get("path", "") or "").strip()
                        if not src_path_str:
                            continue
                        src_path = _Path(src_path_str)
                        if not src_path.exists():
                            continue
                        # Copy if not under products, or under a different product folder
                        try:
                            is_under_products = str(src_path).startswith(str(PRODUCTS_PATH))
                        except Exception:
                            is_under_products = False
                        needs_copy = (not is_under_products) or (src_path.parent != product_folder)
                        if needs_copy:
                            dst_path = product_folder / src_path.name
                            try:
                                # Attempt atomic copy via temp then move
                                _shutil.copy2(src_path, dst_path / "_new")
                                _shutil.move(dst_path / "_new", dst_path)
                                logger.debug(f"Copied image to product folder: %s -> %s", src_path, dst_path)
                            except Exception:
                                logger.exception(f"Failed to first copy image to product folder: {src_path}")
                                try:
                                    _shutil.copyfile(src_path, dst_path)
                                except shutil.SameFileError:
                                    logger.debug(f"Image already exists in product folder: %s", dst_path)
                                except Exception:
                                    logger.exception(f"Failed to second copy image to product folder: {src_path}")
                                    continue
                            _it["path"] = str(dst_path)
                        # Optional mask copy if present and valid
                        try:
                            mask_path_str = str(_it.get("mask_path", "") if _it.get("mask_path", "") is not None else "").strip()
                        except Exception:
                            mask_path_str = ""
                        if mask_path_str and mask_path_str.lower() != "none":
                            msrc = _Path(mask_path_str)
                            if msrc.exists():
                                try:
                                    # Copy if not under products, or under a different product folder
                                    try:
                                        m_under_products = str(msrc).startswith(str(PRODUCTS_PATH))
                                    except Exception:
                                        m_under_products = False
                                    m_needs_copy = (not m_under_products) or (msrc.parent != product_folder)
                                    if m_needs_copy:
                                        mdst = product_folder / msrc.name
                                        try:
                                            _shutil.copy2(msrc, mdst / "_new")
                                            _shutil.move(mdst / "_new", mdst)
                                        except Exception:
                                            try:
                                                _shutil.copyfile(msrc, mdst)
                                            except Exception:
                                                logger.exception(f"Failed to copy mask to product folder: {msrc}")
                                            else:
                                                _it["mask_path"] = str(mdst) if str(mdst) is not None else ""
                                        else:
                                            _it["mask_path"] = str(mdst) if str(mdst) is not None else ""
                                    else:
                                        # Already in current product folder
                                        _it["mask_path"] = str(msrc) if str(msrc) is not None else ""
                                except Exception:
                                    logger.exception("Failed processing mask for internalization")
                    except Exception as e:
                        logger.exception(f"Failed processing image item for internalization: {e}")

            _rewrite_and_copy_images(front_items)
            _rewrite_and_copy_images(back_items)
        except Exception:
            logger.exception("Failed to prepare internal product images and update paths")

        # Validate that all non-slot objects have a non-empty amazon_label
        try:
            def _missing_label(obj: dict) -> bool:
                try:
                    if str(obj.get("type", "")) == "slot":
                        return False
                    return str(obj.get("amazon_label", "") or "").strip() == ""
                except Exception:
                    return True
            if any(_missing_label(it) for it in (front_items + back_items)):
                messagebox.showwarning(
                    "Missing Amazon label",
                    "One or more objects have empty Amazon Label. Please fill all labels before proceeding.",
                )
                return
        except Exception:
            # If validation fails for any reason, be conservative and stop
            messagebox.showwarning(
                "Validation error",
                "Could not validate Amazon labels. Please ensure all objects have a label.",
            )
            return

        # Build combined JSON payload on UI thread (safe to read widgets here)
        try:
            # Common scene parameters
            try:
                step_x = float(self.step_x.get() or 0.0)
                step_y = float(self.step_y.get() or 0.0)
            except Exception:
                step_x, step_y = 0.0, 0.0
            try:
                origin_x = float(self.origin_x.get() or 0.0)
                origin_y = float(self.origin_y.get() or 0.0)
            except Exception:
                origin_x, origin_y = 0.0, 0.0
            try:
                slot_w = float(self.slot_w.get() or 0.0)
                slot_h = float(self.slot_h.get() or 0.0)
            except Exception:
                slot_w, slot_h = 0.0, 0.0

            # Build z-index maps from current canvas items
            slot_z_map: dict[tuple[str, float, float, float, float], int] = {}
            image_z_map: dict[tuple[str, float, float, float, float], int] = {}
            text_z_map: dict[tuple[str, float, float], int] = {}
            text_rect_z_map: dict[tuple[str, float, float, float, float], int] = {}
            for cid, meta in self._items.items():
                t = meta.get("type")
                if t == "slot":
                    try:
                        label_id = meta.get("label_id")
                        label_text = self.canvas.itemcget(label_id, "text") if label_id else ""
                        key = (
                            str(label_text),
                            float(meta.get("x_mm", 0.0)),
                            float(meta.get("y_mm", 0.0)),
                            float(meta.get("w_mm", 0.0)),
                            float(meta.get("h_mm", 0.0)),
                        )
                        slot_z_map[key] = int(meta.get("z", 0))
                    except Exception as e:
                        logger.exception(f"Failed to process slot item {cid}: {e}")
                        continue
                elif t == "image":
                    try:
                        key = (
                            str(meta.get("path", "")),
                            float(meta.get("x_mm", 0.0)),
                            float(meta.get("y_mm", 0.0)),
                            float(meta.get("w_mm", 0.0)),
                            float(meta.get("h_mm", 0.0)),
                        )
                        image_z_map[key] = int(meta.get("z", 0))
                    except Exception as e:
                        logger.exception(f"Failed to process image item {cid}: {e}")
                        continue
                elif t == "text":
                    try:
                        key = (
                            float(meta.get("x_mm", 0.0)),
                            float(meta.get("y_mm", 0.0)),
                            0.0,
                        )
                        text_z_map[key] = int(meta.get("z", 0))
                    except Exception as e:
                        logger.exception(f"Failed to process text item {cid}: {e}")
                        continue
                elif t == "rect":
                    try:
                        outline = str(meta.get("outline", ""))
                        if outline == "#17a24b":
                            key = (
                                str(meta.get("label", "")),
                                float(meta.get("x_mm", 0.0)),
                                float(meta.get("y_mm", 0.0)),
                                float(meta.get("w_mm", 0.0)),
                                float(meta.get("h_mm", 0.0)),
                            )
                            text_rect_z_map[key] = int(meta.get("z", 0))
                    except Exception as e:
                        logger.exception(f"Failed to process rect item {cid}: {e}")
                        continue

            # Before composing, normalize z across current non-slot items to ensure unique, compact values
            self.selection._normalize_z()

            # Helper to store relative paths in JSON while keeping absolute paths in memory
            def _to_rel(p: str) -> str:
                try:
                    from pathlib import Path as __Path
                    if not p:
                        return ""
                    pp = __Path(p)
                    if not pp.is_absolute():
                        return str(pp).replace("\\", "/")
                    rel = pp.relative_to(PRODUCTS_PATH)
                    return str(rel).replace("\\", "/")
                except Exception:
                    try:
                        # Fallback to sku_name/filename if not under products
                        from pathlib import Path as __Path
                        return str(__Path(state.sku_name) / __Path(p).name).replace("\\", "/")
                    except Exception:
                        return p

            def _compose_side(items_for_side: list[dict], sku_name: str, prev_sku_name: str) -> dict:
                slot_descs: list[dict] = []
                for it in items_for_side:
                    if str(it.get("type", "")) == "slot":
                        try:
                            slot_entry = {
                                "label": str(it.get("label", "")),
                                "x_mm": float(it.get("x_mm", 0.0)),
                                "y_mm": float(it.get("y_mm", 0.0)),
                                "w_mm": float(it.get("w_mm", 0.0)),
                                "h_mm": float(it.get("h_mm", 0.0)),
                                # Use the z value directly from the item to avoid key-mismatch defaulting to 0
                                "z": int(it.get("z", 0)),
                                # Preserve owner for grouping; will be removed in final JSON grouping
                                "owner_major": str(it.get("owner_major", "") or ""),
                                "objects": [],
                            }
                            slot_descs.append(slot_entry)
                        except Exception as e:
                            logger.exception(f"Failed to process slot entry: {e}")
                            continue

                def _center_in_slot(img: dict, sl: dict) -> bool:
                    try:
                        cx = float(img.get("x_mm", 0.0)) + float(img.get("w_mm", 0.0)) / 2.0
                        cy = float(img.get("y_mm", 0.0)) + float(img.get("h_mm", 0.0)) / 2.0
                        sx = float(sl.get("x_mm", 0.0))
                        sy = float(sl.get("y_mm", 0.0))
                        sw = float(sl.get("w_mm", 0.0))
                        sh = float(sl.get("h_mm", 0.0))
                        # Use small tolerance for boundary to avoid missing near-edge items
                        eps = 1e-3
                        return (cx >= sx - eps) and (cx <= sx + sw + eps) and (cy >= sy - eps) and (cy <= sy + sh + eps)
                    except Exception as e:
                        logger.exception(f"Failed to check if image is centered in slot: {e}")
                        return False

                for it in items_for_side:
                    if str(it.get("type", "")) != "image":
                        continue
                    try:
                        path_parts = [part_ if part_ != prev_sku_name else sku_name for part_ in Path(str(it.get("path", ""))).parts]
                        mask_path_parts = [part_ if part_ != prev_sku_name else sku_name for part_ in Path(str(it.get("mask_path", "") if it.get("mask_path", "") is not None else "")).parts]
                        obj = {
                            "type": "image",
                            "path": _to_rel(str(Path(*path_parts))),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "w_mm": float(it.get("w_mm", 0.0)),
                            "h_mm": float(it.get("h_mm", 0.0)),
                            "angle": float(it.get("angle", 0.0) or 0.0),
                            # Use direct z from item; maps can miss due to float rounding
                            "z": int(it.get("z", 0)),
                            "amazon_label": it.get("amazon_label", ""),
                            "is_options": bool(it.get("is_options", False)),
                            "is_static": bool(it.get("is_static", False)),
                            # Optional mask path for image
                            "mask_path": _to_rel(str(Path(*mask_path_parts))) if mask_path_parts else "",
                        }
                    except Exception as e:
                        logger.exception(f"Failed to process image for slot: {e}")
                        continue
                    for sl in slot_descs:
                        if _center_in_slot(obj, sl):
                            sl["objects"].append(obj)
                            break

                # Plain text labels (no size): include styling
                for it in items_for_side:
                    if str(it.get("type", "")) != "text":
                        continue
                    # Skip sized text blocks; handled below
                    if ("w_mm" in it) or ("h_mm" in it):
                        continue
                    try:
                        obj = {
                            "type": "text",
                            "text": str(it.get("text", "")),
                            "fill": str(it.get("fill", "white")),
                            "font_family": str(it.get("font_family", "Myriad Pro")),
                            "font_size_pt": int(round(float(it.get("font_size_pt", 12)))),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "z": int(it.get("z", 0)),
                            "amazon_label": it.get("amazon_label", ""),
                            "is_options": bool(it.get("is_options", False)),
                            "is_static": bool(it.get("is_static", False)),
                        }
                    except Exception as e:
                        logger.exception(f"Failed to process text for slot: {e}")
                        continue
                    for sl in slot_descs:
                        try:
                            sx = float(sl.get("x_mm", 0.0))
                            sy = float(sl.get("y_mm", 0.0))
                            sw = float(sl.get("w_mm", 0.0))
                            sh = float(sl.get("h_mm", 0.0))
                            cx = float(obj.get("x_mm", 0.0))
                            cy = float(obj.get("y_mm", 0.0))
                            eps = 1e-3
                            inside = (cx >= sx - eps) and (cx <= sx + sw + eps) and (cy >= sy - eps) and (cy <= sy + sh + eps)
                        except Exception as e:
                            logger.exception(f"Failed to check if text is inside slot: {e}")
                            inside = False
                        if inside:
                            try:
                                sl["objects"].append(obj)
                            except Exception as e:
                                logger.exception(f"Failed to append object to slot: {e}")
                            break

                # Sized text blocks (type "text" + size): treat as text-rects and include label styling
                for it in items_for_side:
                    if str(it.get("type", "")) != "text":
                        continue
                    if not (("w_mm" in it) and ("h_mm" in it)):
                        continue
                    try:
                        obj = {
                            "type": "text",
                            "label": str(it.get("label", "")),
                            "amazon_label": it.get("amazon_label", ""),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "w_mm": float(it.get("w_mm", 0.0)),
                            "h_mm": float(it.get("h_mm", 0.0)),
                            "angle": float(it.get("angle", 0.0) or 0.0),
                            "z": int(it.get("z", 0)),
                            "label_fill": str(it.get("label_fill", "#17a24b")),
                            "label_font_size": int(round(float(it.get("label_font_size", 10)))),
                            "label_font_family": str(it.get("label_font_family", "Myriad Pro")),
                            "is_options": bool(it.get("is_options", False)),
                            "is_static": bool(it.get("is_static", False)),
                        }
                    except Exception as e:
                        logger.exception(f"Failed to process sized text for slot: {e}")
                        continue
                    for sl in slot_descs:
                        try:
                            sx = float(sl.get("x_mm", 0.0))
                            sy = float(sl.get("y_mm", 0.0))
                            sw = float(sl.get("w_mm", 0.0))
                            sh = float(sl.get("h_mm", 0.0))
                            eps = 1e-3
                            inside = (obj["x_mm"] >= sx - eps) and (obj["x_mm"] <= sx + sw + eps) and (obj["y_mm"] >= sy - eps) and (obj["y_mm"] <= sy + sh + eps)
                        except Exception as e:
                            logger.exception(f"Failed to check if sized text is inside slot: {e}")
                            inside = False
                        if inside:
                            try:
                                sl["objects"].append(obj)
                            except Exception as e:
                                logger.exception(f"Failed to append sized text to slot: {e}")
                            break

                for it in items_for_side:
                    if str(it.get("type", "")) != "rect" or str(it.get("outline", "")) != "#17a24b":
                        continue
                    try:
                        obj = {
                            "type": "text",
                            "label": str(it.get("label", "")),
                            "amazon_label": it.get("amazon_label", ""),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "w_mm": float(it.get("w_mm", 0.0)),
                            "h_mm": float(it.get("h_mm", 0.0)),
                            "angle": float(it.get("angle", 0.0) or 0.0),
                            "z": int(it.get("z", 0)),
                            # Persist font info for text blocks
                            "label_fill": str(it.get("label_fill", "#17a24b")),
                            "label_font_size": int(round(float(it.get("label_font_size", 10)))),
                            "label_font_family": str(it.get("label_font_family", "Myriad Pro")),
                            "is_options": bool(it.get("is_options", False)),
                            "is_static": bool(it.get("is_static", False)),
                        }
                    except Exception as e:
                        logger.exception(f"Failed to process rect for slot: {e}")
                        continue
                    for sl in slot_descs:
                        try:
                            sx = float(sl.get("x_mm", 0.0))
                            sy = float(sl.get("y_mm", 0.0))
                            sw = float(sl.get("w_mm", 0.0))
                            sh = float(sl.get("h_mm", 0.0))
                            eps = 1e-3
                            inside = (obj["x_mm"] >= sx - eps) and (obj["x_mm"] <= sx + sw + eps) and (obj["y_mm"] >= sy - eps) and (obj["y_mm"] <= sy + sh + eps)
                        except Exception as e:
                            logger.exception(f"Failed to check if rect is inside slot: {e}")
                            inside = False
                        if inside:
                            try:
                                sl["objects"].append(obj)
                            except Exception as e:
                                logger.exception(f"Failed to append object to slot: {e}")
                            break

                return {"slots": slot_descs}

            images_cnt_front = sum(1 for it in front_items if str(it.get("type", "")) == "image")
            text_cnt_front = sum(1 for it in front_items if (str(it.get("type", "")) == "text") or (str(it.get("type", "")) == "rect" and str(it.get("outline", "")) == "#17a24b"))
            images_cnt_back = sum(1 for it in back_items if str(it.get("type", "")) == "image")
            text_cnt_back = sum(1 for it in back_items if (str(it.get("type", "")) == "text") or (str(it.get("type", "")) == "rect" and str(it.get("outline", "")) == "#17a24b"))
            slot_count = sum(1 for it in slots_only)
            scene_top = {
                "jig": {"width_mm": float(jx), "height_mm": float(jy)},
                "slot_count": int(slot_count),
                "objects_count": {
                    "images": int(images_cnt_front + images_cnt_back),
                    "text": int(text_cnt_front + text_cnt_back),
                },
            }
            state.nonsticker_image_count = int(images_cnt_front + images_cnt_back + text_cnt_front + text_cnt_back)
            # Build Scene.Majors summary and group sides by major
            def _ordered_major_names() -> list[str]:
                try:
                    import re as __re
                    def _order_key(k: str) -> tuple:
                        m = __re.search(r"(\d+)$", k)
                        n = int(m.group(1)) if m else 10**9
                        return (n, k)
                    return sorted(list(self._major_sizes.keys()), key=_order_key)
                except Exception:
                    return list(self._major_sizes.keys())

            ordered_names = _ordered_major_names()
            name_to_label: dict[str, str] = {}
            for idx, nm in enumerate(ordered_names, start=1):
                name_to_label[nm] = f"Major {idx}"

            # Scene.Majors entries
            scene_majors: list[dict] = []
            for nm in ordered_names:
                vals = self._major_sizes.get(nm) or {}
                try:
                    mx = float(vals.get("x", 0.0)); my = float(vals.get("y", 0.0))
                    mw = float(vals.get("w", 0.0)); mh = float(vals.get("h", 0.0))
                except Exception:
                    mx, my, mw, mh = 0.0, 0.0, 0.0, 0.0
                try:
                    ox = float(vals.get("origin_x", self.origin_x.get() or 0.0))
                    oy = float(vals.get("origin_y", self.origin_y.get() or 0.0))
                except Exception:
                    ox, oy = 0.0, 0.0
                try:
                    swm = float(vals.get("slot_w", self.slot_w.get() or 0.0))
                    shm = float(vals.get("slot_h", self.slot_h.get() or 0.0))
                except Exception:
                    swm, shm = 0.0, 0.0
                try:
                    sxm = float(vals.get("step_x", self.step_x.get() or 0.0))
                    sym = float(vals.get("step_y", self.step_y.get() or 0.0))
                except Exception:
                    sxm, sym = 0.0, 0.0
                try:
                    per_major_slots = [s for s in slots_only if str(s.get("owner_major", "") or "") == str(nm)]
                    scount = int(len(per_major_slots))
                except Exception:
                    scount = 0
                scene_majors.append({
                    "rect": {"x_mm": float(mx), "y_mm": float(my), "width_mm": float(mw), "height_mm": float(mh)},
                    "origin": {"x_mm": float(ox), "y_mm": float(oy)},
                    "slot_size": {"width_mm": float(swm), "height_mm": float(shm)},
                    "step_size": {"x_mm": float(sxm), "y_mm": float(sym)},
                    "slot_count": int(scount),
                })
            scene_top["Majors"] = scene_majors

            # Group side slots by major owner
            def _group_side_by_major(flat_side: dict) -> list[dict]:
                groups_map: dict[str, dict] = {}
                slots = list(flat_side.get("slots", []))
                for sl in slots:
                    try:
                        owner = str(sl.get("owner_major", "") or "")
                    except Exception:
                        owner = ""
                    label = name_to_label.get(owner) or (f"{owner}" if owner else "Major 1")
                    grp = groups_map.get(label)
                    if not grp:
                        grp = {"label": label, "slots": []}
                        groups_map[label] = grp
                    s_copy = dict(sl)
                    # remove owner_major in final JSON
                    s_copy.pop("owner_major", None)
                    grp["slots"].append(s_copy)
                # preserve order of majors as in ordered_names if present, else insertion order
                ordered_labels = [name_to_label.get(nm) for nm in ordered_names if name_to_label.get(nm) in groups_map]
                # append any remaining labels (e.g., slots without owner)
                for lbl in list(groups_map.keys()):
                    if lbl not in ordered_labels:
                        ordered_labels.append(lbl)
                return [groups_map[lbl] for lbl in ordered_labels]

            front_grouped = _group_side_by_major(_compose_side(front_items, state.sku_name, state.prev_sku_name))
            back_grouped = _group_side_by_major(_compose_side(back_items, state.sku_name, state.prev_sku_name))

            combined = {
                "Sku": state.sku or "",
                "SkuName": state.sku_name or "",
                "IsSticker": False,
                "Scene": scene_top,
                "Frontside": front_grouped,
                "Backside": back_grouped,
            }
        except Exception as e:
            logger.exception(f"Failed to build combined JSON: {e}")
            combined = {"Sku": str(state.sku_name or ""), "Scene": {}, "Frontside": {}, "Backside": {}}
        json_path = PRODUCTS_PATH / f"{state.sku_name}.json"

        # Mark processing and launch worker thread
        state.is_processing = True

        def _worker():
            try:
                # Render PDFs
                logger.debug(f"Rendering jig SVG...")
                state.processing_message = "Rendering jig SVG..."
                # For the jig cut file we only need the outer jig frame and slot rectangles
                if state.is_cancelled:
                    logger.debug(f"Processing cancelled")
                    return
                self._render_jig_to_svg(p_jig, slots_only, jx, jy)
                # Render Single Pattern (first slot with its objects from front side)
                try:
                    state.processing_message = "Rendering single pattern SVG..."
                    logger.debug(f"Rendering single pattern SVG...")
                    front_sections = combined.get("Frontside", [])
                    slots_desc = []
                    if isinstance(front_sections, list) and front_sections:
                        first_section = front_sections[0] or {}
                        slots_desc = list(first_section.get("slots", []))
                    if slots_desc:
                        state.processing_message = "Rendering single pattern SVG..."
                        if state.is_cancelled:
                            logger.debug(f"Processing cancelled")
                            return
                        self._render_single_pattern_svg(p_pattern, slots_desc[0])
                except Exception as e:
                    state.is_failed = True
                    state.error_message = str(e)
                    logger.exception(f"Failed to render single pattern: {e}")

                logger.debug(f"Rendering front PDF...")
                state.processing_message = "Rendering front PDF..."
                if state.is_cancelled:
                    logger.debug(f"Processing cancelled")
                    return

                front_items_without_slots = [item for item in front_items if item.get("type") != "slot"]
                self._render_scene_to_pdf(p_front, front_items_without_slots, jx, jy, dpi=1200)
                logger.debug(f"Rendering back PDF...")
                state.processing_message = "Rendering back PDF..."
                if state.is_cancelled:
                    logger.debug(f"Processing cancelled")
                    return
                back_items_without_slots = [item for item in back_items if item.get("type") != "slot"]
                self._render_scene_to_pdf(p_back, back_items_without_slots, jx, jy, dpi=1200)
                # Write JSON
                try:
                    logger.debug(f"Writing JSON file...")
                    if state.is_cancelled:
                        logger.debug(f"Processing cancelled")
                        return
                    state.processing_message = "Writing JSON file..."
                    with open(json_path, "w", encoding="utf-8") as _f:
                        json.dump(combined, _f, ensure_ascii=False, indent=2)
                    logger.debug(f"Processing completed")
                    
                except Exception as e:
                    state.is_failed = True
                    state.error_message = str(e)
                    logger.exception(f"Failed to write JSON file: {e}")

                state.processing_message = ""
                # Add new product to list if not already present
                if state.is_cancelled:
                    logger.debug(f"Processing cancelled")
                    return
                for p in ALL_PRODUCTS:
                    if p == state.sku_name:
                        break
                else:
                    ALL_PRODUCTS.append(state.sku_name)
                    if state.sku_name != state.prev_sku_name and state.prev_sku_name:
                        ALL_PRODUCTS.pop(ALL_PRODUCTS.index(state.prev_sku_name))

                if state.prev_sku_name and state.prev_sku_name != state.sku_name:
                    logger.debug(f"Removing previous product: %s", state.prev_sku_name)
                    os.remove(PRODUCTS_PATH / f"{state.prev_sku_name}.json")
                    shutil.rmtree(PRODUCTS_PATH / state.prev_sku_name, ignore_errors=True)

            except MemoryError:
                state.is_failed = True
                state.error_message = "Not enough memory to render PDF"
                logger.exception("Failed to render PDF: Not enough memory")
            except Exception as e:
                state.is_failed = True
                state.error_message = str(e)
                logger.exception(f"Failed in worker thread: {e}")
            finally:
                state.is_processing = False

        state.is_cancelled = False
        threading.Thread(target=_worker, daemon=True).start()

        # Navigate immediately; results screen will poll state and update UI
        self.app.show_screen(NStickerResultsDownloadScreen)

    # ---- Front/Back scene state management ----
    def _clear_scene(self, keep_slots: bool = False):
        try:
            for cid, meta in list(self._items.items()):
                if keep_slots and meta.get("type") in ("slot", "major"):
                    continue
                # Remove rotated overlay polygon for rects
                try:
                    rid = int(meta.get("rot_id", 0) or 0)
                except Exception:
                    rid = 0
                if rid:
                    try:
                        self.canvas.delete(rid)
                    except Exception as e:
                        logger.exception(f"Failed to delete rect overlay: {e}")
                    meta["rot_id"] = None
                # Remove selection border for images
                try:
                    bid = int(meta.get("border_id", 0) or 0)
                except Exception:
                    bid = 0
                if bid:
                    try:
                        self.canvas.delete(bid)
                    except Exception as e:
                        logger.exception(f"Failed to delete image selection border: {e}")
                    meta["border_id"] = None
                self.canvas.delete(cid)
                lbl_id = meta.get("label_id")
                if lbl_id:
                    self.canvas.delete(lbl_id)
                self._items.pop(cid, None)
        finally:
            self.selection.select(None)

    def _create_rect_at_mm(
        self, 
        label: str, 
        w_mm: float,
        h_mm: float,
        x_mm: float,
        y_mm: float,
        outline: str = "#d0d0d0",
        text_fill: str = "white",
        angle: float = 0.0
    ):
        x0, y0, x1, y1 = self._jig_inner_rect_px()
        ox = self._item_outline_half_px()
        oy = self._item_outline_half_px()
        # keep fractional mm inputs
        w_mm_i = self._snap_mm(w_mm)
        h_mm_i = self._snap_mm(h_mm)
        x_mm_i = self._snap_mm(x_mm)
        y_mm_i = self._snap_mm(y_mm)
        w = w_mm_i * MM_TO_PX * self._zoom
        h = h_mm_i * MM_TO_PX * self._zoom
        try:
            ang = float(angle or 0.0)
        except Exception:
            ang = 0.0
        if int(abs(ang)) % 180 == 90:
            w, h = h, w
        # clamp top-left within inner jig
        min_left = x0 + ox
        min_top = y0 + oy
        max_left = x1 - ox - w
        max_top = y1 - oy - h
        left = x0 + x_mm_i * MM_TO_PX * self._zoom + ox
        top = y0 + y_mm_i * MM_TO_PX * self._zoom + oy
        new_left = max(min_left, min(left, max_left))
        new_top = max(min_top, min(top, max_top))
        # Invisible base rect; visual is drawn via overlay polygon
        rect = self.canvas.create_rectangle(new_left, new_top, new_left + w, new_top + h, fill="", outline="", width=0)

        # next z
        max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        self._items[rect] = CanvasObject(
            type="rect",
            w_mm=float(w_mm_i),
            h_mm=float(h_mm_i),
            x_mm=float(x_mm_i),
            y_mm=float(y_mm_i),
            label_id=None,
            outline=outline,
            canvas_id=rect,
            z=int(max_z + 1),
            angle=float(ang),
        )
        try:
            self._items[rect]["label"] = str(label)
        except Exception:
            raise
        try:
            self._update_rect_label_image(rect)
        except Exception:
            logger.exception("Failed to render rotated rect label on create")
        # Create overlay to visualize rotation; base rect stays invisible
        self._update_rect_overlay(rect, self._items[rect], new_left, new_top, w, h)
        return rect

    def _create_text_at_mm(self, text: str, x_mm: float, y_mm: float, fill: str = "#17a24b"):
        x0, y0, x1, y1 = self._jig_inner_rect_px()
        cx = x0 + x_mm * MM_TO_PX * self._zoom
        cy = y0 + y_mm * MM_TO_PX * self._zoom
        # clamp center within inner jig
        cx = max(x0, min(cx, x1))
        cy = max(y0, min(cy, y1))
        tid = self.canvas.create_text(cx, cy, text=text, fill=fill, font=("Myriad Pro", self._scaled_pt(6), "bold"), tags=("label",))
        self._items[tid] = CanvasObject(
            type="text",
            default_fill=fill,
            x_mm=float((cx - x0) / (MM_TO_PX * max(self._zoom, 1e-6))),
            y_mm=float((cy - y0) / (MM_TO_PX * max(self._zoom, 1e-6))),
            label_id=tid,
            canvas_id=tid,
        )
        return tid

    def _serialize_scene(self) -> list[dict]:
        items: list[dict] = []
        for cid, meta in self._items.items():
            t = meta.get("type")
            if t == "rect":
                try:
                    label_text = str(meta.get("label", ""))
                    items.append({
                        "type": "rect",
                        "amazon_label": meta.amazon_label,
                        "is_options": bool(meta.get("is_options", False)),
                        "is_static": bool(meta.get("is_static", False)),
                        "label": label_text,
                        "w_mm": float(meta.get("w_mm", 0.0)),
                        "h_mm": float(meta.get("h_mm", 0.0)),
                        "x_mm": float(meta.get("x_mm", 0.0)),
                        "y_mm": float(meta.get("y_mm", 0.0)),
                        "outline": str(meta.get("outline", "#d0d0d0")),
                        "angle": float(meta.get("angle", 0.0) or 0.0),
                        "z": int(meta.get("z", 0)),
                        # Persist text styling for rect labels
                        "label_fill": str(meta.get("label_fill", "#ffffff")),
                        "label_font_size": int(round(float(meta.get("label_font_size", 10)))),
                        "label_font_family": str(meta.get("label_font_family", "Myriad Pro")),
                        # Persist ownership
                        "owner_major": str(meta.get("owner_major", "")),
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize rect item {cid}: {e}")
                    continue
            elif t == "slot":
                try:
                    label_id = meta.get("label_id")
                    label_text = self.canvas.itemcget(label_id, "text") if label_id else ""
                    items.append({
                        "type": "slot",
                        "label": label_text,
                        "w_mm": float(meta.get("w_mm", 0.0)),
                        "h_mm": float(meta.get("h_mm", 0.0)),
                        "x_mm": float(meta.get("x_mm", 0.0)),
                        "y_mm": float(meta.get("y_mm", 0.0)),
                        "outline": str(meta.get("outline", "#9a9a9a")),
                        "z": int(meta.get("z", 0)),
                        "owner_major": str(meta.get("owner_major", "")),
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize slot item {cid}: {e}")
                    continue
            elif t == "image":
                try:
                    items.append({
                        "type": "image",
                        "amazon_label": meta.amazon_label,
                        "is_options": bool(meta.get("is_options", False)),
                        "is_static": bool(meta.get("is_static", False)),
                        "path": str(meta.get("path", "")),
                        "mask_path": str(meta.get("mask_path", "") if meta.get("mask_path", "") is not None else ""),
                        "w_mm": float(meta.get("w_mm", 0.0)),
                        "h_mm": float(meta.get("h_mm", 0.0)),
                        "x_mm": float(meta.get("x_mm", 0.0)),
                        "y_mm": float(meta.get("y_mm", 0.0)),
                        "angle": float(meta.get("angle", 0.0) or 0.0),
                        "z": int(meta.get("z", 0)),
                        "owner_major": str(meta.get("owner_major", "")),
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize image item {cid}: {e}")
                    continue
            elif t == "text":
                try:
                    txt = self.canvas.itemcget(cid, "text")
                    fill = meta.get("default_fill", self.canvas.itemcget(cid, "fill") or "white")
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                    items.append({
                        "type": "text",
                        "amazon_label": meta.amazon_label,
                        "is_options": bool(meta.get("is_options", False)),
                        "is_static": bool(meta.get("is_static", False)),
                        "text": txt,
                        "x_mm": x_mm,
                        "y_mm": y_mm,
                        "fill": fill,
                        "z": int(meta.get("z", 0)),
                        # Persist text styling for plain text items
                        "font_size_pt": int(round(float(meta.get("font_size_pt", 12)))),
                        "font_family": str(meta.get("font_family", "Myriad Pro")),
                        "owner_major": str(meta.get("owner_major", "")),
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize text item {cid}: {e}")
                    continue
        return items

    def _restore_scene(self, items: list[dict]):
        for it in items:
            t = it.get("type")
            if t == "rect":
                outline = str(it.get("outline", "#d0d0d0"))
                # Prefer saved label fill; otherwise infer from outline for text-rects
                text_fill = str(it.get("label_fill", "#17a24b" if outline == "#17a24b" else "white"))
                rid = self._create_rect_at_mm(
                    it.get("label", ""),
                    float(it.get("w_mm", 0.0)),
                    float(it.get("h_mm", 0.0)),
                    float(it.get("x_mm", 0.0)),
                    float(it.get("y_mm", 0.0)),
                    outline=outline,
                    text_fill=text_fill,
                    angle=float(it.get("angle", 0.0) or 0.0),
                )
                try:
                    if rid in self._items:
                        self._items[rid]["amazon_label"] = it.get("amazon_label", "")
                        # Restore flags if present
                        self._items[rid]["is_options"] = self._as_bool(it.get("is_options", False))
                        self._items[rid]["is_static"] = self._as_bool(it.get("is_static", False))
                        z_val = it.get("z")
                        if z_val is not None:
                            self._items[rid]["z"] = int(z_val)
                        # Apply restored label styling if present and re-render label image
                        try:
                            if "label_fill" in it:
                                self._items[rid]["label_fill"] = str(it.get("label_fill"))
                            if "label_font_size" in it:
                                self._items[rid]["label_font_size"] = int(round(float(it.get("label_font_size", 10))))
                            if "label_font_family" in it:
                                self._items[rid]["label_font_family"] = str(it.get("label_font_family", "Myriad Pro"))
                            self._update_rect_label_image(rid)
                        except Exception:
                            logger.exception("Failed to apply restored rect label styling")
                except Exception as e:
                    logger.exception(f"Failed to apply rect z from JSON: {e}")
            elif t == "slot":
                outline = str(it.get("outline", "#9a9a9a"))
                sid = self._create_slot_at_mm(
                    it.get("label", ""),
                    float(it.get("w_mm", 0.0)),
                    float(it.get("h_mm", 0.0)),
                    float(it.get("x_mm", 0.0)),
                    float(it.get("y_mm", 0.0)),
                    owner_major=str(it.get("owner_major", "") or ""),
                )
                try:
                    if sid in self._items:
                        self._items[sid]["amazon_label"] = str(it.get("amazon_label", "") or "")
                        z_val = it.get("z")
                        if z_val is not None:
                            self._items[sid]["z"] = int(z_val)
                except Exception as e:
                    logger.exception(f"Failed to apply slot z from JSON: {e}")
            elif t == "image":
                path_val = str(it.get("path", ""))
                # Resolve relative path (stored in JSON) to absolute on disk for rendering
                try:
                    from pathlib import Path as __Path
                    if path_val and not __Path(path_val).is_absolute():
                        path = str((PRODUCTS_PATH / path_val).resolve())
                    else:
                        path = path_val
                except Exception:
                    path = path_val
                if path and os.path.exists(path):
                    # Create image at specified mm top-left
                    x_mm = float(it.get("x_mm", 0.0))
                    y_mm = float(it.get("y_mm", 0.0))
                    w_mm = float(it.get("w_mm", 0.0))
                    h_mm = float(it.get("h_mm", 0.0))
                    angle = float(it.get("angle", 0.0) or 0.0)
                    # Create at explicit mm rather than centered
                    # Reuse helper via temporary meta
                    # Compute px and create image
                    jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
                    ox = self._item_outline_half_px(); oy = self._item_outline_half_px()
                    w_px = int(round(w_mm * MM_TO_PX * self._zoom))
                    h_px = int(round(h_mm * MM_TO_PX * self._zoom))
                    left = jx0 + ox + x_mm * MM_TO_PX * self._zoom
                    top = jy0 + oy + y_mm * MM_TO_PX * self._zoom
                    meta = CanvasObject(
                        type="image",
                        path=path,
                        w_mm=float(self._snap_mm(w_mm)),
                        h_mm=float(self._snap_mm(h_mm)),
                        x_mm=float(self._snap_mm(x_mm)),
                        y_mm=float(self._snap_mm(y_mm)),
                        angle=float(angle),
                    )
                    # Restore optional mask path if provided (resolve if relative)
                    try:
                        mpath_val = str(it.get("mask_path", "") or "")
                        if mpath_val:
                            try:
                                from pathlib import Path as __Path
                                if not __Path(mpath_val).is_absolute():
                                    mpath = str((PRODUCTS_PATH / mpath_val).resolve())
                                else:
                                    mpath = mpath_val
                            except Exception:
                                mpath = mpath_val
                            meta["mask_path"] = mpath
                    except Exception:
                        raise
                    meta["amazon_label"] = str(it.get("amazon_label", "") or "")
                    try:
                        meta["is_options"] = self._as_bool(it.get("is_options", False))
                        meta["is_static"] = self._as_bool(it.get("is_static", False))
                    except Exception:
                        logger.exception("Failed to restore flags for image item")
                    photo = self._render_photo(meta, max(1, int(w_px)), max(1, int(h_px)))
                    if photo is not None:
                        bw, bh = self._rotated_bounds_px(w_px, h_px, angle)
                        place_left = left + (w_px - bw) / 2.0
                        place_top = top + (h_px - bh) / 2.0
                        img_id = self.canvas.create_image(place_left, place_top, image=photo, anchor="nw")
                        meta.canvas_id = img_id
                        # assign next z
                        max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
                        try:
                            meta["z"] = int(it.get("z", int(max_z + 1)))
                        except Exception as e:
                            logger.exception(f"Failed to apply image z from JSON: {e}")
                            meta["z"] = int(max_z + 1)
                        # Restore ownership if present
                        try:
                            owner = str(it.get("owner_major", "") or "")
                            if owner:
                                meta["owner_major"] = owner
                        except Exception:
                            raise
                        self._items[img_id] = meta
            elif t == "text":
                # Two shapes are encoded as text in saved JSON:
                # 1) Plain text labels: have a 'text' field and no size.
                # 2) Text blocks (green rectangles): no 'text' field but have w_mm/h_mm.
                if ("text" in it) and ("w_mm" not in it and "h_mm" not in it):
                    tid = self._create_text_at_mm(
                        it.get("text", "Text"),
                        float(it.get("x_mm", 0.0)),
                        float(it.get("y_mm", 0.0)),
                        str(it.get("fill", "white")),
                    )
                    try:
                        if tid in self._items:
                            self._items[tid]["amazon_label"] = str(it.get("amazon_label", "") or "")
                            try:
                                self._items[tid]["is_options"] = self._as_bool(it.get("is_options", False))
                                self._items[tid]["is_static"] = self._as_bool(it.get("is_static", False))
                            except Exception:
                                logger.exception("Failed to restore flags for text item")
                            # Restore ownership
                            try:
                                owner = str(it.get("owner_major", "") or "")
                                if owner:
                                    self._items[tid]["owner_major"] = owner
                            except Exception:
                                raise
                            z_val = it.get("z")
                            if z_val is not None:
                                self._items[tid]["z"] = int(z_val)
                            # Apply restored text styling
                            try:
                                fam = str(it.get("font_family", "Myriad Pro"))
                                try:
                                    base_pt = int(round(float(it.get("font_size_pt", 12))))
                                except Exception:
                                    base_pt = 12
                                self._items[tid]["font_family"] = fam
                                self._items[tid]["font_size_pt"] = int(base_pt)
                                self.canvas.itemconfig(tid, font=(fam, self._scaled_pt(base_pt), "bold"))
                            except Exception:
                                logger.exception("Failed to apply restored text styling")
                    except Exception as e:
                        logger.exception(f"Failed to apply text z from JSON: {e}")
                else:
                    # Restore as the same rectangle block that was saved, using required fields
                    rid = self._create_rect_at_mm(
                        "Text",
                        float(it["w_mm"]),
                        float(it["h_mm"]),
                        float(it["x_mm"]),
                        float(it["y_mm"]),
                        outline="#17a24b",
                        text_fill=str(it.get("label_fill", "#17a24b")),
                        angle=float(it.get("angle", 0.0) or 0.0),
                    )
                    try:
                        if rid in self._items:
                            self._items[rid]["amazon_label"] = str(it.get("amazon_label", "") or "")
                            try:
                                self._items[rid]["is_options"] = self._as_bool(it.get("is_options", False))
                                self._items[rid]["is_static"] = self._as_bool(it.get("is_static", False))
                            except Exception:
                                logger.exception("Failed to restore flags for text-rect item")
                            # Restore ownership
                            try:
                                owner = str(it.get("owner_major", "") or "")
                                if owner:
                                    self._items[rid]["owner_major"] = owner
                            except Exception:
                                raise
                            z_val = it.get("z")
                            if z_val is not None:
                                self._items[rid]["z"] = int(z_val)
                            # Apply restored label styling for text-rects
                            try:
                                if "label_fill" in it:
                                    self._items[rid]["label_fill"] = str(it.get("label_fill"))
                                if "label_font_size" in it:
                                    self._items[rid]["label_font_size"] = int(round(float(it.get("label_font_size", 10))))
                                if "label_font_family" in it:
                                    self._items[rid]["label_font_family"] = str(it.get("label_font_family", "Myriad Pro"))
                                self._update_rect_label_image(rid)
                            except Exception:
                                logger.exception("Failed to apply restored text-rect label styling")
                    except Exception as e:
                        logger.exception(f"Failed to apply text-rect z from JSON: {e}")

    def _maybe_load_saved_product(self):
        # Load saved non-sticker scene when editing an existing product
        prod = str(state.saved_product or "").strip()
        if not prod:
            return
        path = PRODUCTS_PATH / f"{prod}.json"
        if not path.exists():
            return
        import json as _json
        with path.open("r", encoding="utf-8") as f:
            data = _json.load(f)

        if bool(data.get("IsSticker", False)):
            return
        sku_val = str(data.get("Sku") or prod)
        sku_name_val = str(data.get("SkuName") or prod)
        if sku_val:
            self.sku_var.set(sku_val)
            self.sku_name_var.set(sku_name_val)
            state.sku = sku_val
            state.sku_name = sku_name_val

        scene = data.get("Scene") or {}
        jig = scene.get("jig") or {}
        step = scene.get("step") or {}
        origin = scene.get("origin") or {}
        slot_size = scene.get("slot_size") or {}

        def _set_str(var, val):
            # Preserve decimals exactly as provided; avoid rounding/coercion
            try:
                s = str(val)
            except Exception:
                s = str(val)
            var.set(s)

        # Suppress trace-driven slot/major updates during bulk restore
        _prev_suppress = getattr(self, "_suppress_major_traces", False)
        self._suppress_major_traces = True

        _set_str(self.jig_x, jig.get("width_mm", self.jig_x.get()))
        _set_str(self.jig_y, jig.get("height_mm", self.jig_y.get()))
        # Initialize scene-level fields from first major if present; fall back to legacy Scene fields
        scene_majors_peek = list((scene.get("Majors") or []))
        if scene_majors_peek:
            try:
                first = scene_majors_peek[0] or {}
                _ox = (first.get("origin") or {}).get("x_mm", self.origin_x.get())
                _oy = (first.get("origin") or {}).get("y_mm", self.origin_y.get())
                _sw = (first.get("slot_size") or {}).get("width_mm", self.slot_w.get())
                _sh = (first.get("slot_size") or {}).get("height_mm", self.slot_h.get())
                _sx = (first.get("step_size") or {}).get("x_mm", self.step_x.get())
                _sy = (first.get("step_size") or {}).get("y_mm", self.step_y.get())
                _set_str(self.origin_x, _ox)
                _set_str(self.origin_y, _oy)
                _set_str(self.slot_w, _sw)
                _set_str(self.slot_h, _sh)
                _set_str(self.step_x, _sx)
                _set_str(self.step_y, _sy)
            except Exception:
                # Fallback on any error
                _set_str(self.origin_x, origin.get("x_mm", self.origin_x.get()))
                _set_str(self.origin_y, origin.get("y_mm", self.origin_y.get()))
                _set_str(self.slot_w, slot_size.get("width_mm", self.slot_w.get()))
                _set_str(self.slot_h, slot_size.get("height_mm", self.slot_h.get()))
                _set_str(self.step_x, step.get("x_mm", self.step_x.get()))
                _set_str(self.step_y, step.get("y_mm", self.step_y.get()))
        else:
            _set_str(self.step_x, step.get("x_mm", self.step_x.get()))
            _set_str(self.step_y, step.get("y_mm", self.step_y.get()))
            _set_str(self.origin_x, origin.get("x_mm", self.origin_x.get()))
            _set_str(self.origin_y, origin.get("y_mm", self.origin_y.get()))
            _set_str(self.slot_w, slot_size.get("width_mm", self.slot_w.get()))
            _set_str(self.slot_h, slot_size.get("height_mm", self.slot_h.get()))

        front = data.get("Frontside") or {}
        back = data.get("Backside") or {}

        # Build majors and slots depending on new or legacy format
        scene_majors = list((data.get("Scene") or {}).get("Majors") or [])
        major_sizes_new: dict[str, dict] = {}

        def _collect_slots_and_items(side_val) -> tuple[list[dict], list[dict]]:
            slots: list[dict] = []
            items: list[dict] = []
            if isinstance(side_val, list):
                # New format: list of sections {label, slots}
                for idx, section in enumerate(side_val):
                    try:
                        label = str((section or {}).get("label", f"Major size {idx+1}"))
                    except Exception:
                        label = f"Major size {idx+1}"
                    # Collect this section's slots and objects locally first
                    sec_slots = [dict(s) for s in list((section or {}).get("slots") or [])]
                    sec_items = []
                    for s in sec_slots:
                        for obj in list(s.get("objects") or []):
                            sec_items.append(dict(obj))
                    # Build major rectangle from slot bounds for this section
                    try:
                        if sec_slots:
                            min_x = min(float(s.get("x_mm", 0.0)) for s in sec_slots)
                            min_y = min(float(s.get("y_mm", 0.0)) for s in sec_slots)
                            max_x = max(float(s.get("x_mm", 0.0)) + float(s.get("w_mm", 0.0)) for s in sec_slots)
                            max_y = max(float(s.get("y_mm", 0.0)) + float(s.get("h_mm", 0.0)) for s in sec_slots)
                            w = max(0.0, max_x - min_x)
                            h = max(0.0, max_y - min_y)
                            # Use Scene.Majors per-index for rect/origin/slot/step if present
                            try:
                                sm = scene_majors[idx] if idx < len(scene_majors) else {}
                            except Exception:
                                sm = {}
                            rx = float((sm.get("rect") or {}).get("x_mm", min_x))
                            ry = float((sm.get("rect") or {}).get("y_mm", min_y))
                            rw = float((sm.get("rect") or {}).get("width_mm", w))
                            rh = float((sm.get("rect") or {}).get("height_mm", h))
                            ox = float((sm.get("origin") or {}).get("x_mm", self.origin_x.get() or 0.0))
                            oy = float((sm.get("origin") or {}).get("y_mm", self.origin_y.get() or 0.0))
                            sw = float((sm.get("slot_size") or {}).get("width_mm", self.slot_w.get() or 0.0))
                            sh = float((sm.get("slot_size") or {}).get("height_mm", self.slot_h.get() or 0.0))
                            sx = float((sm.get("step_size") or {}).get("x_mm", self.step_x.get() or 0.0))
                            sy = float((sm.get("step_size") or {}).get("y_mm", self.step_y.get() or 0.0))
                            # Ensure preset name uses 'Major size N' scheme consistently
                            preset_name = f"Major size {idx+1}"
                            major_sizes_new[preset_name] = {
                                "x": str(rx),
                                "y": str(ry),
                                "w": str(rw),
                                "h": str(rh),
                                "step_x": str(sx),
                                "step_y": str(sy),
                                "origin_x": str(ox),
                                "origin_y": str(oy),
                                "slot_w": str(sw),
                                "slot_h": str(sh),
                            }
                            # Rewrite owner labels in this section only
                            for s in sec_slots:
                                try:
                                    s["owner_major"] = preset_name
                                except Exception:
                                    pass
                            for o in sec_items:
                                try:
                                    o["owner_major"] = preset_name
                                except Exception:
                                    pass
                            # Append to global collections after owner assignment
                            slots.extend(sec_slots)
                            items.extend(sec_items)
                    except Exception:
                        # Best-effort; skip major rect if invalid
                        pass
            else:
                # Legacy format: single object with slots
                sec_slots = list((side_val or {}).get("slots") or [])
                for s in sec_slots:
                    slots.append(dict(s))
                    for obj in list(s.get("objects") or []):
                        items.append(dict(obj))
            return slots, items

        front_slots, front_items = _collect_slots_and_items(front)
        back_slots, back_items = _collect_slots_and_items(back)

        def _do_restore():
            # If majors present in new format, replace presets and render rectangles
            try:
                if major_sizes_new:
                    self._major_sizes = dict(major_sizes_new)
                    # Refresh preset combobox and select a valid entry
                    try:
                        # Rebuild combobox values and ensure selection is valid
                        if hasattr(self, "_major_combo"):
                            self._major_combo.configure(values=list(self._major_sizes.keys()))
                        if (self.major_name.get() or "") not in self._major_sizes:
                            # Pick first available preset if current is invalid
                            next_name = next(iter(self._major_sizes.keys()), "")
                            self.major_name.set(next_name)
                        # Sync UI fields from the selected preset (inline to avoid nested scope name)
                        sel_name = (self.major_name.get() or "").strip()
                        vals = self._major_sizes.get(sel_name)
                        if vals:
                            self._suppress_major_traces = True
                            try:
                                self.major_x.set(str(vals.get("x", "0")))
                                self.major_y.set(str(vals.get("y", "0")))
                                self.major_w.set(str(vals.get("w", "0")))
                                self.major_h.set(str(vals.get("h", "0")))
                                if hasattr(self, "step_x"):
                                    self.step_x.set(str(vals.get("step_x", self.step_x.get())))
                                if hasattr(self, "step_y"):
                                    self.step_y.set(str(vals.get("step_y", self.step_y.get())))
                                if hasattr(self, "origin_x"):
                                    self.origin_x.set(str(vals.get("origin_x", self.origin_x.get())))
                                if hasattr(self, "origin_y"):
                                    self.origin_y.set(str(vals.get("origin_y", self.origin_y.get())))
                                if hasattr(self, "slot_w"):
                                    self.slot_w.set(str(vals.get("slot_w", self.slot_w.get())))
                                if hasattr(self, "slot_h"):
                                    self.slot_h.set(str(vals.get("slot_h", self.slot_h.get())))
                            finally:
                                self._suppress_major_traces = False
                        # Update active major and visibility after selection
                        try:
                            self._active_major = (self.major_name.get() or "").strip()
                            if hasattr(self, "_refresh_major_visibility"):
                                self._refresh_major_visibility()
                        except Exception:
                            pass
                        # Ensure Remove button reflects the actual number of majors after restore
                        try:
                            if hasattr(self, "_ms_btn_remove"):
                                if len(self._major_sizes) <= 1:
                                    self._ms_btn_remove.configure(state="disabled")
                                else:
                                    self._ms_btn_remove.configure(state="normal")
                        except Exception:
                            raise
                    except Exception:
                        # Non-fatal UI sync issue
                        pass
            except Exception:
                # Keep previous presets if replacement fails
                pass
            # Clear anything auto-created and recreate slots from JSON for exact positions
            self._clear_scene(keep_slots=False)
            for sl in front_slots:
                sid = self._create_slot_at_mm(
                    str(sl.get("label", "")),
                    float(sl.get("w_mm", 0.0)),
                    float(sl.get("h_mm", 0.0)),
                    float(sl.get("x_mm", 0.0)),
                    float(sl.get("y_mm", 0.0)),
                    owner_major=str(sl.get("owner_major", "") or ""),
                )
                try:
                    if sid in self._items:
                        z_val = sl.get("z")
                        if z_val is not None:
                            self._items[sid]["z"] = int(z_val)
                except Exception as e:
                    logger.exception(f"Failed to apply saved slot z from JSON: {e}")
            # Restore front items on canvas; stash back items for toggling
            if front_items:
                self._restore_scene(front_items)
            self._scene_store["front"] = list(front_items)
            self._scene_store["back"] = list(back_items)
            self._redraw_jig(center=False)
            self._raise_all_labels()
            self.selection._reorder_by_z()
            # Render or refresh majors based on restored presets
            try:
                self._update_all_majors()
            except Exception:
                raise
            # Re-enable trace-driven updates after initial restore completes
            self._suppress_major_traces = _prev_suppress

        # Let variable traces run first, then restore
        self.after(10, _do_restore)

    def _on_backside_toggle(self, *_):
        # Deselect any current selection before switching sides
        self.selection.select(None)
        # Save current scene under current side (exclude slots)
        data_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
        self._scene_store[self._current_side] = data_no_slots
        # Switch side based on checkbox
        self._current_side = "back" if self.backside.get() else "front"
        # Clear and restore the target scene; keep slots persistent across sides
        self._clear_scene(keep_slots=True)
        data = self._scene_store.get(self._current_side) or []
        if data:
            self._restore_scene(data)
        # Keep jig in place without recentering
        self._redraw_jig(center=False)
        # Ensure labels on top after switching sides
        self._raise_all_labels()
        # Respect per-major visibility on side switch
        if hasattr(self, "_refresh_major_visibility"):
            try:
                self._refresh_major_visibility()
            except Exception:
                raise
        # Major rectangle management is delegated to MajorManager (see self.majors)
