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
from src.core.app import COLOR_BG_SCREEN, validate_min1, vcmd_int
from src.utils import *
from src.core.state import ALL_PRODUCTS, FONTS_PATH, OUTPUT_PATH, PRODUCTS_PATH, state
from src.canvas import CanvasObject, CanvasSelection, MajorManager, JigController, SlotManager, ImageManager, PdfExporter, FontsManager, CustomImagesManager
from .results_download import NStickerResultsDownloadScreen

logger = logging.getLogger(__name__)

DEFAULT_JIG_SIZE   = (296.0, 394.5831)
DEFAULT_SLOT_SIZE  = (40.66, 28.9)
DEFAULT_ORIGIN_POS = (11.76, 12.52)
DEFAULT_STEP_SIZE  = (72.55, 47.85)
DEFAULT_MAJOR_SIZE = tuple((int(DEFAULT_SLOT_SIZE[i] + (DEFAULT_ORIGIN_POS[i]*2)) for i in range(2)))
DEFAULT_MAJOR_POS  = (12, 15)

# Left menu colors (reusing top menu scheme)
BUTTON_COLOR = "#3a5f8f"
BUTTON_HOVER_COLOR = "#4a7faf"
BORDER_COLOR = TOP_MENU_CONTAINER_BORDER = "#3d3d3d"
TOP_MENU_ACCENT_BLUE = "#4a90d9"

# Top menu colors
TOP_MENU_BG = "#1a1a1a"
TOP_MENU_CONTAINER_BG = "#2d2d2d"
TOP_MENU_CONTAINER_BORDER = "#3d3d3d"
TOP_MENU_BOX_BG = "#252525"
TOP_MENU_INPUT_BG = "#2d2d2d"
TOP_MENU_LABEL_FG = "#888888"
TOP_MENU_TEXT_FG = "white"
TOP_MENU_SEPARATOR = "#3d3d3d"
TOP_MENU_ACCENT_BLUE = "#4a90d9"
TOP_MENU_ACCENT_ORANGE = "#e67e22"
TOP_MENU_ACCENT_PURPLE = "#9b59b6"
TOP_MENU_ACCENT_GREEN = "#27ae60"
TOP_MENU_ACCENT_RED = "#c0392b"
TOP_MENU_BUTTON_INACTIVE = "#3d3d3d"


class NStickerCanvasScreen(Screen):
    """Non-sticker designer: SKU, jig, import, place, size."""
    def __init__(self, master, app):
        super().__init__(master, app)

        if not self.app.is_fullscreen:
            self.app.toggle_fullscreen()
        # self.app.set_small_size()

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

        left_bar = tk.Frame(self, bg=TOP_MENU_BG, width=250)
        left_bar.pack(side="left", fill="y", padx=0, pady=0)
        left_bar.pack_propagate(False)
        # Expose left bar for child managers (e.g., Fonts) to attach their UI
        self.left_bar = left_bar

        self.sku_var = tk.StringVar(value="")
        self.sku_name_var = tk.StringVar(value=state.sku_name or "")

        # Top horizontal bar for Import, Jig size, tools, and shortcuts
        bar = tk.Frame(self, bg="green")
        bar.pack(fill="none", padx=0, pady=(0, 0))

        # 2) Jig size values (UI moved to left bar below)
        # Keep StringVars here so other logic can reference them early
        self.jig_x = tk.StringVar(value=state.pkg_x or "296.0")
        self.jig_y = tk.StringVar(value=state.pkg_y or "394.5831")
        # live redraw and slot re-create when jig size changes
        self.jig_x.trace_add("write", self._on_jig_change)
        self.jig_y.trace_add("write", self._on_jig_change)

        # 4) White vertical separator (between jig/tools and Major Info)
        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)

        # Major Size columns: label | presets | x,y | w,h | vertical separator
        tk.Label(bar, text="Major Info:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(16, 6))

        # Column 2: Preset combobox + buttons stacked
        ms_preset_col = tk.Frame(bar, bg="black")
        ms_preset_col.pack(side="left", padx=8, pady=8)
        ms_wrap = tk.Frame(ms_preset_col, bg="#6f6f6f")
        ms_wrap.pack(side="top", pady=2)
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
            values = list(self._major_sizes.keys())
            self._major_combo.configure(values=values)
            try:
                if hasattr(self, "_major_combo_basic"):
                    self._major_combo_basic.configure(values=values)
            except Exception:
                pass
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
        _small_btn_style.configure("Small.TButton", font=("Segoe UI", 9), padding=(0, 1))
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

        self.slot_w = tk.StringVar(value="40.66")
        self.slot_h = tk.StringVar(value="28.9")
        self.origin_x = tk.StringVar(value="11.76")
        self.origin_y = tk.StringVar(value="12.52")
        self.step_x = tk.StringVar(value="72.55")
        self.step_y = tk.StringVar(value="47.85")
        
        self._export_files_list = ["File 1"]
        self.export_file_var = tk.StringVar(value="File 1")

        # Initialize ASIN data (UI is in top menu panel_amazon)
        def _asin_load_all() -> list[str]:
            asins: list[str] = [asin_pair[0] for asin_pair in state.asins]
            if not asins:
                asins = []
            seen = set()
            uniq: list[str] = []
            for v in asins:
                if v not in seen:
                    seen.add(v)
                    uniq.append(v)
            return uniq

        def _asin_initial_counts() -> dict[str, int]:
            counts: dict[str, int] = {asin_pair[0]: asin_pair[1] for asin_pair in state.asins}
            return counts

        def _asin_initial_mirrors() -> dict[str, bool]:
            mirrors: dict[str, bool] = {}
            try:
                for asin_pair in state.asins:
                    try:
                        if isinstance(asin_pair, (list, tuple)) and len(asin_pair) >= 1:
                            a = str(asin_pair[0])
                            m = False
                            if len(asin_pair) >= 3:
                                try:
                                    m = bool(asin_pair[2])
                                except Exception:
                                    m = False
                            mirrors[a] = m
                    except Exception:
                        continue
            except Exception:
                pass
            return mirrors

        self._asin_list: list[str] = _asin_load_all()
        self.asin_combo_var = tk.StringVar(value=(self._asin_list[0] if self._asin_list else ""))
        _initial_counts = _asin_initial_counts()
        _initial_mirrors = _asin_initial_mirrors()
        self._asin_counts: dict[str, int] = {k: int(_initial_counts.get(k, 1)) for k in self._asin_list}
        self._asin_mirror: dict[str, bool] = {k: bool(_initial_mirrors.get(k, False)) for k in self._asin_list}
        
        # Per-ASIN object storage: each ASIN has its own objects for front and back
        self._asin_objects: dict[str, dict[str, list[dict]]] = {}
        for asin in self._asin_list:
            self._asin_objects[asin] = {"front": [], "back": []}

        def _asin_refresh_values(select_value: Optional[str] = None):
            try:
                values = list(self._asin_list)
                try:
                    if hasattr(self, "_asin_combo_left"):
                        self._asin_combo_left.configure(values=values)
                except Exception:
                    pass
                if select_value is not None:
                    self.asin_combo_var.set(select_value)
            except Exception:
                pass

        def _on_asin_combo(_e=None):
            try:
                prev_asin = state.asins[0][0] if state.asins else None
                sel = (self.asin_combo_var.get() or "").strip()
                
                # Save previous ASIN state (only objects, NOT slots)
                if prev_asin and prev_asin in self._asin_objects:
                    current_objects = [it for it in self._serialize_scene() if it.get("type") != "slot"]
                    self._asin_objects[prev_asin][self._current_side] = current_objects
                    
                    other_side = "back" if self._current_side == "front" else "front"
                    if other_side in self._scene_store:
                        other_objects = [it for it in self._scene_store[other_side] if it.get("type") != "slot"]
                        self._asin_objects[prev_asin][other_side] = other_objects
                    # Persist per-ASIN mirror flag from UI for previous ASIN
                    try:
                        if hasattr(self, "asin_mirror_var"):
                            self._asin_mirror[prev_asin] = bool(self.asin_mirror_var.get())
                    except Exception:
                        pass
                    
                    logger.debug(f"[ASIN] Switch '{prev_asin}'→'{sel}': Saved {len(current_objects)} objects")
                
                # Switch to new ASIN
                self.sku_var.set(sel)
                state.asins = [[sel, self._asin_counts.get(sel, 1)]]
                
                # Restore new ASIN objects (slots stay on canvas!)
                if sel and sel in self._asin_objects:
                    self._clear_scene(keep_slots=True)
                    objects_to_restore = self._asin_objects[sel].get(self._current_side, [])
                    
                    if objects_to_restore:
                        self._restore_scene(objects_to_restore)
                        logger.debug(f"[ASIN] Restored '{sel}': {len(objects_to_restore)} objects")
                    
                    other_side = "back" if self._current_side == "front" else "front"
                    other_objects = [it for it in self._asin_objects[sel].get(other_side, []) if it.get("type") != "slot"]
                    self._scene_store[other_side] = other_objects
                    
                    self._redraw_jig(center=False)
                    self._raise_all_labels()
                    self.selection._reorder_by_z()
                    # Restore mirror UI for newly selected ASIN
                    try:
                        if hasattr(self, "asin_mirror_var"):
                            self.asin_mirror_var.set(bool(self._asin_mirror.get(sel, False)))
                    except Exception:
                        pass
                else:
                    logger.warning(f"[ASIN] '{sel}' not found! Available: {list(self._asin_objects.keys())}")
                    try:
                        if hasattr(self, "asin_mirror_var"):
                            self.asin_mirror_var.set(False)
                    except Exception:
                        pass
                
                try:
                    _apply_count_from_selection()
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to switch ASIN")
                pass

        def _on_asin_combo_trace(*args):
            logger.debug(f"[ASIN_TRACE] asin_combo_var changed to: '{self.asin_combo_var.get()}'")
            _on_asin_combo()
        
        # Trace the variable to catch all changes
        try:
            self.asin_combo_var.trace_add("write", _on_asin_combo_trace)
        except Exception:
            pass

        # Guard to suppress applying count when we are programmatically switching selection
        self._suppress_asin_apply = False
        def _apply_count_from_selection():
            try:
                sel = (self.asin_combo_var.get() or "").strip()
                if getattr(self, "_suppress_asin_apply", False):
                    return
                if sel:
                    c = int(self._asin_counts.get(sel, 1))
                    if c < 1:
                        c = 1
                    self.count_in_order.set(str(c))
            except Exception:
                pass

        # Also react to any change of the combobox variable (covers programmatic changes)
        try:
            self.asin_combo_var.trace_add("write", lambda *_: _apply_count_from_selection())
        except Exception:
            pass

        # Count field initialized here (UI in panel_amazon)
        self.count_in_order = tk.StringVar(value="1")

        def _asin_add():
            try:
                val = (self.sku_var.get() or "").strip()
                
                if not val:
                    messagebox.showwarning("Missing ASIN", "Please enter an ASIN to add.")
                    return
                if len(val) < 3:
                    messagebox.showwarning("Invalid ASIN", "ASIN is too short.")
                    return
                
                # Read the intended count BEFORE changing selection
                try:
                    cnt_txt = (self.count_in_order.get() or "1").strip()
                    cnt = int(cnt_txt) if cnt_txt.isdigit() else 1
                except Exception:
                    cnt = 1
                cnt = max(1, cnt)
                
                # Save current ASIN's state FIRST before copying
                current_asin = state.asins[0][0] if state.asins else None
                
                if current_asin and current_asin in self._asin_objects:
                    current_objects = [it for it in self._serialize_scene() if it.get("type") != "slot"]
                    self._asin_objects[current_asin][self._current_side] = current_objects
                    
                    other_side = "back" if self._current_side == "front" else "front"
                    if other_side in self._scene_store:
                        other_objects = [it for it in self._scene_store[other_side] if it.get("type") != "slot"]
                        self._asin_objects[current_asin][other_side] = other_objects
                
                # Copy current objects (NOT slots!) if this is a new ASIN
                if val not in self._asin_list:
                    self._asin_list.append(val)
                    
                    # Get current objects (excluding slots - they're shared)
                    # Important: Respect which side is currently active on canvas
                    current_canvas_objects = [it for it in self._serialize_scene() if it.get("type") != "slot"]
                    
                    # Determine which side is on canvas and which is in storage
                    if self._current_side == "front":
                        current_front = current_canvas_objects
                        current_back = [it for it in self._scene_store.get("back", []) if it.get("type") != "slot"]
                    else:  # backside is active
                        current_back = current_canvas_objects
                        current_front = [it for it in self._scene_store.get("front", []) if it.get("type") != "slot"]
                    
                    # Deep copy to avoid reference issues
                    import copy
                    self._asin_objects[val] = {
                        "front": copy.deepcopy(current_front),
                        "back": copy.deepcopy(current_back)
                    }
                    # Initialize mirror flag for new ASIN (default False)
                    try:
                        self._asin_mirror[val] = False
                    except Exception:
                        pass
                    logger.debug(f"[ASIN] Added '{val}' (count={cnt}): copied {len(current_front)} front objs, {len(current_back)} back objs from '{current_asin}' (current_side={self._current_side})")
                
                # Persist count for the new ASIN immediately
                self._asin_counts[val] = cnt
                
                # Select the new ASIN, but do not let selection overwrite the entered count
                self._suppress_asin_apply = True
                _asin_refresh_values(select_value=val)
                self._suppress_asin_apply = False
                # Ensure Count reflects stored value for newly selected ASIN
                self.count_in_order.set(str(cnt))
                state.asins = [[val, cnt]]
                
                # Update SKU var to reflect the new ASIN but DON'T trigger restore
                # The canvas already has the correct objects (just copied to new ASIN)
                self.sku_var.set(val)

                
                try:
                    messagebox.showinfo("ASIN", f"Added ASIN '{val}' with count {self._asin_counts[val]}.")
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to add ASIN")
                pass

        def _asin_remove():
            try:
                sel = (self.asin_combo_var.get() or "").strip()
                if sel in self._asin_list:
                    try:
                        self._asin_list.remove(sel)
                    except Exception:
                        pass
                    try:
                        self._asin_counts.pop(sel, None)
                    except Exception:
                        pass
                    try:
                        self._asin_mirror.pop(sel, None)
                    except Exception:
                        pass
                    # Also remove from _asin_objects to prevent copying backside to other ASINs
                    try:
                        self._asin_objects.pop(sel, None)
                    except Exception:
                        pass
                # Choose next selection
                next_sel = self._asin_list[0] if self._asin_list else ""
                _asin_refresh_values(select_value=next_sel)
                self.sku_var.set(next_sel)
                state.asins = next_sel
                _apply_count_from_selection()
            except Exception:
                pass

        # Update count map when count changes for the selected ASIN
        def _on_count_change(*_):
            try:
                sel = (self.asin_combo_var.get() or "").strip()
                if not sel:
                    return
                txt = (self.count_in_order.get() or "1").strip()
                try:
                    c = int(txt)
                except Exception:
                    c = 1
                # Only update the selected ASIN's count when editing pertains to it:
                # either the entry matches selection or entry is blank
                entry_val = (self.sku_var.get() or "").strip()
                if (entry_val == "") or (entry_val == sel):
                    self._asin_counts[sel] = max(1, c)
            except Exception:
                pass
        try:
            self.count_in_order.trace_add("write", _on_count_change)
        except Exception:
            pass

        # Initial refresh
        _asin_refresh_values(select_value=self.asin_combo_var.get())
        _apply_count_from_selection()

        self.sticker_var = tk.BooleanVar(value=False)
        self.backside = tk.BooleanVar(value=False)
        self.backside.trace_add("write", self._on_backside_toggle)

        self._use_top_menu = True

        # --- Top Menu (Modern 3-row layout with visual separation) ---
        top_menu = tk.Frame(self, bg=TOP_MENU_BG)
        top_menu.pack(side="top", fill="x", padx=0, pady=0)

        # Helper: create styled input group with label and entry
        def _create_input_group(parent, label_text, var, width=8, entry_bg=TOP_MENU_CONTAINER_BG, label_width=None):
            frame = tk.Frame(parent, bg=TOP_MENU_BG)
            lbl = tk.Label(frame, text=label_text, bg=TOP_MENU_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9))
            if label_width:
                lbl.configure(width=label_width, anchor="e")
            lbl.pack(side="left", padx=(0, 4))
            entry = tk.Entry(frame, textvariable=var, width=width, bg=entry_bg, fg=TOP_MENU_TEXT_FG,
                            insertbackground="white", relief="flat", bd=0, highlightthickness=1,
                            highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightcolor=TOP_MENU_ACCENT_BLUE,
                            font=("Segoe UI", 10), justify="center")
            entry.pack(side="left")
            return frame, entry

        def _create_validated_input(parent, label_text, var, width=6):
            frame = tk.Frame(parent, bg=TOP_MENU_BG)
            tk.Label(frame, text=label_text, bg=TOP_MENU_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left", padx=(0, 2))
            entry = tk.Entry(frame, textvariable=var, width=width, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                            insertbackground="white", relief="flat", bd=0, highlightthickness=1,
                            highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightcolor=TOP_MENU_ACCENT_BLUE,
                            font=("Segoe UI", 10), justify="center",
                            validate="key", validatecommand=(vcmd_float(self), "%P"))
            entry.pack(side="left")
            return frame, entry

        # ===== ROW 1: Product Name | Export format + DPI | CMYK colors =====
        row1 = tk.Frame(top_menu, bg=TOP_MENU_BG)
        row1.pack(side="top", fill="x", pady=(4, 6))

        # Product Name with styled container
        prod_container = tk.Frame(row1, bg=TOP_MENU_CONTAINER_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        prod_container.pack(side="left", padx=(0, 12))
        tk.Label(prod_container, text="Product Name", bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 8)).pack(side="top", anchor="w", padx=6, pady=(4, 0))
        tk.Entry(prod_container, textvariable=self.sku_name_var, width=22, bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", bd=0, font=("Segoe UI", 11), justify="left").pack(side="top", padx=6, pady=(0, 6))

        # Vertical separator
        tk.Frame(row1, bg=TOP_MENU_SEPARATOR, width=1).pack(side="left", fill="y", padx=(0, 10), pady=4)

        # Export format toggle buttons
        export_container = tk.Frame(row1, bg=TOP_MENU_CONTAINER_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        export_container.pack(side="left", padx=(0, 8))
        tk.Label(export_container, text="Export Format", bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 8)).pack(side="top", anchor="w", padx=6, pady=(4, 2))
        
        fmt_btns_row = tk.Frame(export_container, bg=TOP_MENU_CONTAINER_BG)
        fmt_btns_row.pack(side="top", padx=6, pady=(0, 6))
        
        if not hasattr(self, "format_var"):
            self.format_var = tk.StringVar(value="pdf")
        if not hasattr(self, "_format_buttons"):
            self._format_buttons = {}
        
        def _toggle_format(fmt):
            current = self.format_var.get().lower().split(",")
            current = [f.strip() for f in current if f.strip()]
            if fmt in current:
                current.remove(fmt)
            else:
                current.append(fmt)
            self.format_var.set(",".join(current) if current else "pdf")
            _update_format_buttons()
        
        def _update_format_buttons():
            current = self.format_var.get().lower().split(",")
            current = [f.strip() for f in current if f.strip()]
            for fmt, btn in self._format_buttons.items():
                if fmt in current:
                    btn.configure(bg=TOP_MENU_ACCENT_BLUE, fg=TOP_MENU_TEXT_FG, relief="flat")
                else:
                    btn.configure(bg=TOP_MENU_BUTTON_INACTIVE, fg=TOP_MENU_LABEL_FG, relief="flat")
        
        for fmt in ["PDF", "JPG", "PNG", "BMP"]:
            btn = tk.Button(fmt_btns_row, text=fmt, width=4, relief="flat", bd=0,
                           bg=TOP_MENU_BUTTON_INACTIVE, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9, "bold"),
                           activebackground="#5a5a5a", activeforeground="white", cursor="hand2",
                           command=lambda f=fmt.lower(): _toggle_format(f))
            btn.pack(side="left", padx=1)
            self._format_buttons[fmt.lower()] = btn
        _update_format_buttons()

        # DPI input
        dpi_container = tk.Frame(row1, bg=TOP_MENU_CONTAINER_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        dpi_container.pack(side="left", padx=(0, 8))
        tk.Label(dpi_container, text="DPI", bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 8)).pack(side="top", anchor="w", padx=6, pady=(4, 0))
        if not hasattr(self, "dpi_var"):
            self.dpi_var = tk.StringVar(value="1200")
        tk.Entry(dpi_container, textvariable=self.dpi_var, width=6, bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", bd=0, font=("Segoe UI", 11), justify="center").pack(side="top", padx=6, pady=(0, 6))

        # Vertical separator
        tk.Frame(row1, bg=TOP_MENU_SEPARATOR, width=1).pack(side="left", fill="y", padx=(2, 10), pady=4)

        # JIG CMYK with color preview
        if not hasattr(self, "jig_cmyk"):
            self.jig_cmyk = tk.StringVar(value="75,0,75,0")
        self._jig_cmyk_invalid = False
        
        jig_cmyk_container = tk.Frame(row1, bg=TOP_MENU_CONTAINER_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        jig_cmyk_container.pack(side="left", padx=(0, 8))
        tk.Label(jig_cmyk_container, text="JIG CMYK", bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 8)).pack(side="top", anchor="w", padx=6, pady=(4, 0))
        jig_inner = tk.Frame(jig_cmyk_container, bg=TOP_MENU_CONTAINER_BG)
        jig_inner.pack(side="top", padx=6, pady=(0, 6))
        self._jig_cmyk_entry = tk.Entry(jig_inner, textvariable=self.jig_cmyk, width=12, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                                         insertbackground="white", relief="flat", bd=0, font=("Segoe UI", 10), justify="center")
        self._jig_cmyk_entry.pack(side="left")
        
        def _on_jig_cmyk_focus_in(event=None):
            self._prev_jig_cmyk = self.jig_cmyk.get()
        def _on_jig_cmyk_focus_out(event=None):
            orig = str(self.jig_cmyk.get() or "")
            parts = orig.split(",")
            if len(parts) != 4:
                self._jig_cmyk_invalid = True
                return
            parts = [p.strip() for p in parts]
            self.jig_cmyk.set(",".join(parts))
            self._jig_cmyk_invalid = False
        self._jig_cmyk_entry.bind("<FocusIn>", _on_jig_cmyk_focus_in)
        self._jig_cmyk_entry.bind("<FocusOut>", _on_jig_cmyk_focus_out)

        # Object CMYK with color preview
        if not hasattr(self, "obj_cmyk"):
            self.obj_cmyk = tk.StringVar(value="0,100,0,0")
        self._obj_cmyk_invalid = False
        
        obj_cmyk_container = tk.Frame(row1, bg=TOP_MENU_CONTAINER_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        obj_cmyk_container.pack(side="left", padx=(0, 4))
        tk.Label(obj_cmyk_container, text="Object CMYK", bg=TOP_MENU_CONTAINER_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 8)).pack(side="top", anchor="w", padx=6, pady=(4, 0))
        obj_inner = tk.Frame(obj_cmyk_container, bg=TOP_MENU_CONTAINER_BG)
        obj_inner.pack(side="top", padx=6, pady=(0, 6))
        self._obj_cmyk_entry = tk.Entry(obj_inner, textvariable=self.obj_cmyk, width=12, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                                         insertbackground="white", relief="flat", bd=0, font=("Segoe UI", 10), justify="center")
        self._obj_cmyk_entry.pack(side="left")
        
        def _on_obj_cmyk_focus_in(event=None):
            self._prev_obj_cmyk = self.obj_cmyk.get()
        def _on_obj_cmyk_focus_out(event=None):
            orig = str(self.obj_cmyk.get() or "")
            parts = orig.split(",")
            if len(parts) != 4:
                self._obj_cmyk_invalid = True
                return
            parts = [p.strip() for p in parts]
            self.obj_cmyk.set(",".join(parts))
            self._obj_cmyk_invalid = False
        self._obj_cmyk_entry.bind("<FocusIn>", _on_obj_cmyk_focus_in)
        self._obj_cmyk_entry.bind("<FocusOut>", _on_obj_cmyk_focus_out)

        # Horizontal separator line
        tk.Frame(top_menu, bg=TOP_MENU_SEPARATOR, height=1).pack(side="top", fill="x", padx=4, pady=(0, 2))

        # ===== ROW 2: Jig Size | Major Area | Add/Delete | Select Area =====
        row2_top = tk.Frame(top_menu, bg=TOP_MENU_BG)
        row2_top.pack(side="top", fill="x", pady=(4, 4))

        # Jig Size container
        jig_size_box = tk.Frame(row2_top, bg=TOP_MENU_BOX_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        jig_size_box.pack(side="left", padx=(0, 8))
        tk.Label(jig_size_box, text="Jig Size", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_ACCENT_BLUE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 6))
        tk.Label(jig_size_box, text="W:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left")
        tk.Entry(jig_size_box, textvariable=self.jig_x, width=7, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(jig_size_box, text="H:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))
        tk.Entry(jig_size_box, textvariable=self.jig_y, width=7, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(jig_size_box, text="", bg=TOP_MENU_BOX_BG, width=1).pack(side="left")

        # Major Area container
        major_box = tk.Frame(row2_top, bg=TOP_MENU_BOX_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        major_box.pack(side="left", padx=(0, 8))
        tk.Label(major_box, text="Major Area", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_ACCENT_BLUE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 6))
        self._major_combo_basic = ttk.Combobox(major_box, textvariable=self.major_name, state="readonly",
                                               values=list(self._major_sizes.keys()), justify="center", width=14)
        self._major_combo_basic.pack(side="left", padx=(0, 6), pady=4)
        for lbl, var in [("X:", self.major_x), ("Y:", self.major_y), ("W:", self.major_w), ("H:", self.major_h)]:
            tk.Label(major_box, text=lbl, bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left", padx=(4 if lbl != "X:" else 0, 0))
            tk.Entry(major_box, textvariable=var, width=5, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                     insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                     validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(major_box, text="", bg=TOP_MENU_BOX_BG, width=1).pack(side="left")

        # Action buttons container
        action_box = tk.Frame(row2_top, bg=TOP_MENU_BG)
        action_box.pack(side="left", padx=(0, 12))
        
        btn_frame = tk.Frame(action_box, bg=TOP_MENU_BG)
        btn_frame.pack(side="left")
        
        self._ms_btn_add = tk.Button(btn_frame, text="Add", bg=TOP_MENU_ACCENT_GREEN, fg=TOP_MENU_TEXT_FG,
                                      font=("Segoe UI", 9, "bold"), relief="flat", width=6, height=1,
                                      activebackground="#2ecc71", activeforeground="white", cursor="hand2",
                                      command=_ms_add)
        self._ms_btn_add.pack(side="left", padx=(0, 4))
        self._ms_btn_add.bind("<Enter>", lambda e: self._ms_btn_add.config(bg="#2ecc71"))
        self._ms_btn_add.bind("<Leave>", lambda e: self._ms_btn_add.config(bg=TOP_MENU_ACCENT_GREEN))
        
        self._ms_btn_remove = tk.Button(btn_frame, text="Remove", bg=TOP_MENU_ACCENT_RED, fg=TOP_MENU_TEXT_FG,
                                         font=("Segoe UI", 9, "bold"), relief="flat", width=8, height=1,
                                         activebackground="#e74c3c", activeforeground="white", cursor="hand2",
                                         command=_ms_remove)
        self._ms_btn_remove.pack(side="left")
        self._ms_btn_remove.bind("<Enter>", lambda e: self._ms_btn_remove.config(bg="#e74c3c"))
        self._ms_btn_remove.bind("<Leave>", lambda e: self._ms_btn_remove.config(bg=TOP_MENU_ACCENT_RED))

        # Horizontal separator line
        tk.Frame(top_menu, bg=TOP_MENU_SEPARATOR, height=1).pack(side="top", fill="x", padx=4, pady=2)

        # ===== ROW 3: Slot Size | Origin Offset | Step Size =====
        row3_top = tk.Frame(top_menu, bg=TOP_MENU_BG)
        row3_top.pack(side="top", fill="x", pady=(4, 4))

        # Slot Size container
        slot_size_box = tk.Frame(row3_top, bg=TOP_MENU_BOX_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        slot_size_box.pack(side="left", padx=(0, 8))
        tk.Label(slot_size_box, text="Slot Size", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_ACCENT_ORANGE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 6))
        tk.Label(slot_size_box, text="W:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left")
        tk.Entry(slot_size_box, textvariable=self.slot_w, width=6, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(slot_size_box, text="H:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))
        tk.Entry(slot_size_box, textvariable=self.slot_h, width=6, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(slot_size_box, text="", bg=TOP_MENU_BOX_BG, width=1).pack(side="left")

        # Origin Offset container
        origin_box = tk.Frame(row3_top, bg=TOP_MENU_BOX_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        origin_box.pack(side="left", padx=(0, 8))
        tk.Label(origin_box, text="Origin Offset", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_ACCENT_ORANGE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 6))
        tk.Label(origin_box, text="X:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left")
        tk.Entry(origin_box, textvariable=self.origin_x, width=6, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(origin_box, text="Y:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))
        tk.Entry(origin_box, textvariable=self.origin_y, width=6, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(origin_box, text="", bg=TOP_MENU_BOX_BG, width=1).pack(side="left")

        # Step Size container
        step_box = tk.Frame(row3_top, bg=TOP_MENU_BOX_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        step_box.pack(side="left", padx=(0, 8))
        tk.Label(step_box, text="Step Size", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_ACCENT_ORANGE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 6))
        tk.Label(step_box, text="X:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left")
        tk.Entry(step_box, textvariable=self.step_x, width=6, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(step_box, text="Y:", bg=TOP_MENU_BOX_BG, fg=TOP_MENU_LABEL_FG, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))
        tk.Entry(step_box, textvariable=self.step_y, width=6, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG,
                 insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=2, pady=4)
        tk.Label(step_box, text="", bg=TOP_MENU_BOX_BG, width=1).pack(side="left")

        # Backside checkbox container
        backside_box = tk.Frame(row3_top, bg=TOP_MENU_BOX_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        backside_box.pack(side="left", padx=(0, 4))
        tk.Checkbutton(backside_box, text="Backside", variable=self.backside, bg=TOP_MENU_BOX_BG, fg=TOP_MENU_TEXT_FG,
                       selectcolor=TOP_MENU_INPUT_BG, activebackground=TOP_MENU_BOX_BG, activeforeground=TOP_MENU_TEXT_FG,
                       font=("Segoe UI", 9), relief="flat", borderwidth=0, highlightthickness=0).pack(side="left", padx=8, pady=4)

        if not hasattr(self, "sel_amazon_label"):
            self.sel_amazon_label = tk.StringVar(value="")

        if not getattr(self, "_use_top_menu", False):
            top_menu.destroy()
        else:
            try:
                bar.pack_forget()
            except Exception:
                pass
            for _legacy in (locals().get("slot_col"), locals().get("origin_col"), locals().get("step_col")):
                try:
                    if _legacy is not None:
                        _legacy.pack_forget()
                except Exception:
                    pass
            # Proactively remove any leftover labels/boxes under left_bar except the backside toggle and tools
            try:
                whitelist = set([id(locals().get("tools")), id(locals().get("backside_wrap"))])
                for ch in list(left_bar.winfo_children()):
                    try:
                        if id(ch) not in whitelist:
                            ch.pack_forget()
                    except Exception:
                        pass
            except Exception:
                pass

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
        
        self._transformation_expanded = True
        self._transformation_animation_id = None
        
        transformation_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        transformation_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        transformation_header = tk.Frame(transformation_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        transformation_header.pack(side="top", fill="x", padx=5, pady=2)
        
        transformation_header_content = tk.Frame(transformation_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        transformation_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        transformation_header_lbl = tk.Label(transformation_header_content, text="▼ Transformation", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        transformation_header_lbl.pack(side="left")
        
        transformation_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        transformation_outer.pack(side="top", fill="x", padx=10, pady=(0, 0))
        
        transformation_outer_inner = tk.Frame(transformation_outer, bg=TOP_MENU_BG)
        transformation_outer_inner.pack(side="top", fill="x", padx=5)
        
        transformation_wrapper = tk.Frame(transformation_outer_inner, bg=TOP_MENU_BG)
        transformation_wrapper.pack(side="top", fill="x")
        transformation_wrapper.pack_propagate(False)
        
        transformation_container = tk.Frame(transformation_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        transformation_container.pack(side="top", fill="both", expand=True)

        row2 = tk.Frame(transformation_container, bg=TOP_MENU_BG)
        row2.pack(side="top", fill="x", padx=8, pady=6)

        self.sel_x = tk.StringVar(value="0")
        self.sel_y = tk.StringVar(value="0")
        self.sel_w = tk.StringVar(value=state.pkg_x or "296.0")
        self.sel_h = tk.StringVar(value=state.pkg_y or "394.5831")
        self.sel_angle = tk.StringVar(value="0")

        for label_text, var in [("X:", self.sel_x), ("Y:", self.sel_y), ("W:", self.sel_w), ("H:", self.sel_h)]:
            row = tk.Frame(row2, bg=TOP_MENU_BG)
            row.pack(side="top", fill="x", pady=2)
            tk.Label(row, text=label_text, fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=5, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=var, width=13, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center").pack(side="left", fill="x", expand=True, padx=(4, 0))

        angle_row = tk.Frame(row2, bg=TOP_MENU_BG)
        angle_row.pack(side="top", fill="x", pady=2)
        tk.Label(angle_row, text="Angle:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=5, anchor="w").pack(side="left")
        angle_container = tk.Frame(angle_row, bg=TOP_MENU_INPUT_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        angle_container.pack(side="left", fill="x", expand=True, padx=(4, 0))
        tk.Entry(angle_container, textvariable=self.sel_angle, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", bd=0, width=12, font=("Segoe UI", 10), justify="center").pack(side="left", fill="x", expand=True)
        tk.Label(angle_container, text="°", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_INPUT_BG, font=("Segoe UI", 10)).pack(side="right", padx=2)

        self.row2 = row2
        
        transformation_container.update_idletasks()
        transformation_wrapper.config(height=transformation_container.winfo_reqheight())

        self._text_expanded = False
        self._text_animation_id = None
        
        text_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        text_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        text_header = tk.Frame(text_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        text_header.pack(side="top", fill="x", padx=5, pady=2)
        
        text_header_content = tk.Frame(text_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        text_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        text_header_lbl = tk.Label(text_header_content, text="▼ Text", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        text_header_lbl.pack(side="left")
        
        text_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        text_outer.pack(side="top", fill="x", padx=10, pady=(0, 0))
        
        text_outer_inner = tk.Frame(text_outer, bg=TOP_MENU_BG)
        text_outer_inner.pack(side="top", fill="x", padx=5)
        
        text_wrapper = tk.Frame(text_outer_inner, bg=TOP_MENU_BG)
        text_wrapper.pack(side="top", fill="x")
        text_wrapper.pack_propagate(False)
        
        text_container = tk.Frame(text_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        text_container.pack(side="top", fill="both", expand=True)

        text_content = tk.Frame(text_container, bg=TOP_MENU_BG)
        text_content.pack(side="top", fill="x", padx=8, pady=6)

        self.text_size = tk.StringVar(value="12")
        self.text_color = tk.StringVar(value="#17a24b")
        self.text_family = tk.StringVar(value="Myriad Pro")

        size_row = tk.Frame(text_content, bg=TOP_MENU_BG)
        size_row.pack(side="top", fill="x", pady=2)
        tk.Label(size_row, text="Size:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=7, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        size_entry = tk.Entry(size_row, textvariable=self.text_size, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", bd=0, width=8, font=("Segoe UI", 10), justify="center")
        size_entry.pack(side="left", fill="x", expand=True)
        tk.Label(size_row, text="pt", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

        color_row = tk.Frame(text_content, bg=TOP_MENU_BG)
        color_row.pack(side="top", fill="x", pady=2)
        tk.Label(color_row, text="Color:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=7, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        color_entry = tk.Entry(color_row, textvariable=self.text_color, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", bd=0, width=12, font=("Segoe UI", 10), justify="center")
        color_entry.pack(side="left", fill="x", expand=True)

        def _open_color_picker(e=None):
            try:
                initial = (self.text_color.get() or "#17a24b").strip()
            except Exception:
                initial = "#17a24b"
            try:
                from tkinter import colorchooser
                _rgb, hx = colorchooser.askcolor(color=initial, title="Select color")
            except Exception:
                hx = None
            if hx:
                try:
                    self.text_color.set(hx)
                except Exception:
                    pass
            return "break"
        color_entry.bind("<Button-1>", _open_color_picker)

        family_row = tk.Frame(text_content, bg=TOP_MENU_BG)
        family_row.pack(side="top", fill="x", pady=2)
        tk.Label(family_row, text="Family:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=7, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self._family_combo = ttk.Combobox(
            family_row,
            textvariable=self.text_family,
            state="readonly",
            values=["Myriad Pro"],
            justify="center",
            width=14,
        )
        self._family_combo.pack(side="left", fill="x", expand=True)

        text_buttons_row = tk.Frame(text_content, bg=TOP_MENU_BG)
        text_buttons_row.pack(side="top", fill="x", pady=(4, 0))
        
        def _create_text_button(parent, text, command):
            bg_color = TOP_MENU_ACCENT_GREEN if text == "Import" else TOP_MENU_ACCENT_RED
            hover_color = "#2ecc71" if text == "Import" else "#e74c3c"
            btn_frame = tk.Frame(parent, bg=bg_color, cursor="hand2")
            btn_frame.pack(side="left", fill="x", expand=True, pady=1, padx=(0 if text == "Import" else 2, 2 if text == "Import" else 0))
            lbl = tk.Label(btn_frame, text=text, fg="white", bg=bg_color, font=("Segoe UI", 10, "bold"), pady=4)
            lbl.pack(fill="x")
            def on_click(e=None):
                command()
            def on_enter(e=None):
                btn_frame.configure(bg=hover_color)
                lbl.configure(bg=hover_color)
            def on_leave(e=None):
                btn_frame.configure(bg=bg_color)
                lbl.configure(bg=bg_color)
            btn_frame.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            return btn_frame

        self._text_import_btn = _create_text_button(text_buttons_row, "Import", lambda: self.fonts._on_import_font() if hasattr(self, 'fonts') else None)
        self._text_remove_btn = _create_text_button(text_buttons_row, "Remove", lambda: self.fonts._on_remove_font() if hasattr(self, 'fonts') else None)

        def _animate_text_section(target_height, current_height, step):
            if self._text_animation_id:
                self.after_cancel(self._text_animation_id)
            
            if abs(current_height - target_height) < step:
                text_wrapper.config(height=target_height)
                if target_height == 0:
                    text_container.pack_forget()
                    text_wrapper.pack_forget()
                self._text_animation_id = None
                return
            
            if current_height < target_height:
                new_height = min(current_height + step, target_height)
            else:
                new_height = max(current_height - step, target_height)
            
            text_wrapper.config(height=new_height)
            self._text_animation_id = self.after(10, lambda: _animate_text_section(target_height, new_height, step))

        def _toggle_text_section():
            if self._text_expanded:
                self._text_expanded = False
                text_header_lbl.config(text="▶ Text")
                _animate_text_section(0, text_wrapper.winfo_height(), 8)
            else:
                self._text_expanded = True
                text_header_lbl.config(text="▼ Text")
                text_wrapper.pack(side="top", fill="x")
                text_container.pack(side="top", fill="both", expand=True)
                text_container.update_idletasks()
                target_height = text_container.winfo_reqheight()
                _animate_text_section(target_height, 0, 8)

        def _on_text_header_enter(e=None):
            text_header.config(highlightbackground="#777777")
        def _on_text_header_leave(e=None):
            text_header.config(highlightbackground=BORDER_COLOR)

        text_header.bind("<Button-1>", lambda e: _toggle_text_section())
        text_header_content.bind("<Button-1>", lambda e: _toggle_text_section())
        text_header_lbl.bind("<Button-1>", lambda e: _toggle_text_section())
        text_header.bind("<Enter>", _on_text_header_enter)
        text_header.bind("<Leave>", _on_text_header_leave)
        text_header_content.bind("<Enter>", _on_text_header_enter)
        text_header_content.bind("<Leave>", _on_text_header_leave)
        text_header_lbl.bind("<Enter>", _on_text_header_enter)
        text_header_lbl.bind("<Leave>", _on_text_header_leave)

        text_container.update_idletasks()
        text_wrapper.config(height=0)
        text_wrapper.pack_forget()
        text_header_outer.pack_forget()
        text_outer.pack_forget()

        self.text_section = {
            'header_outer': text_header_outer,
            'header': text_header,
            'header_lbl': text_header_lbl,
            'wrapper': text_wrapper,
            'container': text_container,
            'outer': text_outer,
            'amazon_anchor': None
        }

        self._amazon_expanded = True
        self._amazon_animation_id = None
        
        amazon_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        amazon_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        self.text_section['amazon_anchor'] = amazon_header_outer
        
        amazon_header = tk.Frame(amazon_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        amazon_header.pack(side="top", fill="x", padx=5, pady=2)
        
        amazon_header_content = tk.Frame(amazon_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        amazon_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        amazon_header_lbl = tk.Label(amazon_header_content, text="▼ Amazon-spec", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        amazon_header_lbl.pack(side="left")
        
        fields_outer2 = tk.Frame(left_bar, bg=TOP_MENU_BG)
        fields_outer2.pack(side="top", fill="x", padx=10, pady=(0, 0))
        
        fields_outer2_inner = tk.Frame(fields_outer2, bg=TOP_MENU_BG)
        fields_outer2_inner.pack(side="top", fill="x", padx=5)
        
        amazon_wrapper = tk.Frame(fields_outer2_inner, bg=TOP_MENU_BG)
        amazon_wrapper.pack(side="top", fill="x")
        amazon_wrapper.pack_propagate(False)
        
        fields_container2 = tk.Frame(amazon_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        fields_container2.pack(side="top", fill="both", expand=True)

        row3 = tk.Frame(fields_container2, bg=TOP_MENU_BG)
        row3.pack(side="top", fill="x", padx=8, pady=6)

        label_row = tk.Frame(row3, bg=TOP_MENU_BG)
        label_row.pack(side="top", fill="x", pady=2)
        tk.Label(label_row, text="Label:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=5, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(label_row, textvariable=self.sel_amazon_label, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", bd=0, width=12, font=("Segoe UI", 10), justify="center").pack(side="left", fill="x", expand=True, padx=(4, 0))

        file_row = tk.Frame(row3, bg=TOP_MENU_BG)
        file_row.pack(side="top", fill="x", pady=2)
        tk.Label(file_row, text="File:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=5, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.sel_export_file = tk.StringVar(value="File 1")
        self._file_selector_left = ttk.Combobox(
            file_row,
            textvariable=self.sel_export_file,
            state="readonly",
            values=self._export_files_list,
            width=16
        )
        self._file_selector_left.pack(side="left", fill="x", expand=True, padx=(4, 0))

        static_row = tk.Frame(row3, bg=TOP_MENU_BG)
        static_row.pack(side="top", anchor="w", pady=(8, 2))
        self._suppress_flag_traces = False
        self.sel_is_options = tk.BooleanVar(value=False)
        self.sel_is_static = tk.BooleanVar(value=False)
        static_btn_frame = tk.Frame(static_row, bg=TOP_MENU_CONTAINER_BG, highlightbackground=TOP_MENU_CONTAINER_BORDER, highlightthickness=1)
        static_btn_frame.pack(side="left")
        tk.Checkbutton(
            static_btn_frame,
            text="Static",
            variable=self.sel_is_static,
            bg=TOP_MENU_CONTAINER_BG,
            fg=TOP_MENU_TEXT_FG,
            selectcolor=TOP_MENU_INPUT_BG,
            activebackground=TOP_MENU_CONTAINER_BG,
            activeforeground=TOP_MENU_TEXT_FG,
            font=("Segoe UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        ).pack(side="left", padx=8, pady=4)

        fields_container2.update_idletasks()
        amazon_wrapper.config(height=fields_container2.winfo_reqheight())

        self._actions_expanded = True
        self._actions_animation_id = None
        
        actions_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        actions_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        actions_header = tk.Frame(actions_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        actions_header.pack(side="top", fill="x", padx=5, pady=2)
        
        actions_header_content = tk.Frame(actions_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        actions_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        actions_header_lbl = tk.Label(actions_header_content, text="▼ Actions", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        actions_header_lbl.pack(side="left")
        
        actions_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        actions_outer.pack(side="top", fill="x", padx=10, pady=(0, 0))
        
        actions_outer_inner = tk.Frame(actions_outer, bg=TOP_MENU_BG)
        actions_outer_inner.pack(side="top", fill="x", padx=5)
        
        actions_wrapper = tk.Frame(actions_outer_inner, bg=TOP_MENU_BG)
        actions_wrapper.pack(side="top", fill="x")
        actions_wrapper.pack_propagate(False)
        
        actions_container = tk.Frame(actions_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        actions_container.pack(side="top", fill="both", expand=True)

        tools = tk.Frame(actions_container, bg=TOP_MENU_BG)
        tools.pack(side="top", fill="x", padx=8, pady=6)
        self.tools_panel = tools

        self._img_cursor = None
        self._img_stick = None
        self._img_image = None

        def _create_action_button(parent, text, command):
            btn_frame = tk.Frame(parent, bg=BUTTON_COLOR, cursor="hand2")
            btn_frame.pack(side="top", fill="x", pady=1)
            lbl = tk.Label(btn_frame, text=text, fg="white", bg=BUTTON_COLOR, font=("Segoe UI", 10, "bold"), pady=4)
            lbl.pack(fill="x")
            def on_click(e=None):
                command()
            def on_enter(e=None):
                btn_frame.configure(bg=BUTTON_HOVER_COLOR)
                lbl.configure(bg=BUTTON_HOVER_COLOR)
            def on_leave(e=None):
                btn_frame.configure(bg=BUTTON_COLOR)
                lbl.configure(bg=BUTTON_COLOR)
            btn_frame.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            return btn_frame

        _create_action_button(tools, "Add Image", self._import_image)
        _create_action_button(tools, "Add Text", self._drop_text)
        _create_action_button(tools, "Add Barcode", self._drop_barcode)
        _create_action_button(tools, "Arrange Objects", self._ai_arrange_objects)
        _create_action_button(tools, "Arrange Majors", self._arrange_majors)

        actions_container.update_idletasks()
        actions_wrapper.config(height=actions_container.winfo_reqheight())

        def _animate_section(wrapper, container, header_lbl, expanded_attr, animation_id_attr, target_height, current_height, step):
            if getattr(self, animation_id_attr):
                self.after_cancel(getattr(self, animation_id_attr))
            
            if abs(current_height - target_height) < step:
                wrapper.config(height=target_height)
                if target_height == 0:
                    container.pack_forget()
                setattr(self, animation_id_attr, None)
                return
            
            if current_height < target_height:
                new_height = min(current_height + step, target_height)
            else:
                new_height = max(current_height - step, target_height)
            
            wrapper.config(height=new_height)
            aid = self.after(10, lambda: _animate_section(wrapper, container, header_lbl, expanded_attr, animation_id_attr, target_height, new_height, step))
            setattr(self, animation_id_attr, aid)

        def _toggle_transformation():
            if self._transformation_expanded:
                self._transformation_expanded = False
                transformation_header_lbl.config(text="▶ Transformation")
                _animate_section(transformation_wrapper, transformation_container, transformation_header_lbl, '_transformation_expanded', '_transformation_animation_id', 0, transformation_wrapper.winfo_height(), 8)
            else:
                self._transformation_expanded = True
                transformation_header_lbl.config(text="▼ Transformation")
                transformation_container.pack(side="top", fill="both", expand=True)
                transformation_container.update_idletasks()
                target_height = transformation_container.winfo_reqheight()
                _animate_section(transformation_wrapper, transformation_container, transformation_header_lbl, '_transformation_expanded', '_transformation_animation_id', target_height, 0, 8)
        
        def _on_transformation_enter(e=None):
            transformation_header.config(highlightbackground="#777777")
        def _on_transformation_leave(e=None):
            transformation_header.config(highlightbackground=BORDER_COLOR)
        
        transformation_header.bind("<Button-1>", lambda e: _toggle_transformation())
        transformation_header_content.bind("<Button-1>", lambda e: _toggle_transformation())
        transformation_header_lbl.bind("<Button-1>", lambda e: _toggle_transformation())
        transformation_header.bind("<Enter>", _on_transformation_enter)
        transformation_header.bind("<Leave>", _on_transformation_leave)
        transformation_header_content.bind("<Enter>", _on_transformation_enter)
        transformation_header_content.bind("<Leave>", _on_transformation_leave)
        transformation_header_lbl.bind("<Enter>", _on_transformation_enter)
        transformation_header_lbl.bind("<Leave>", _on_transformation_leave)

        def _toggle_amazon():
            if self._amazon_expanded:
                self._amazon_expanded = False
                amazon_header_lbl.config(text="▶ Amazon-spec")
                _animate_section(amazon_wrapper, fields_container2, amazon_header_lbl, '_amazon_expanded', '_amazon_animation_id', 0, amazon_wrapper.winfo_height(), 8)
            else:
                self._amazon_expanded = True
                amazon_header_lbl.config(text="▼ Amazon-spec")
                fields_container2.pack(side="top", fill="both", expand=True)
                fields_container2.update_idletasks()
                target_height = fields_container2.winfo_reqheight()
                _animate_section(amazon_wrapper, fields_container2, amazon_header_lbl, '_amazon_expanded', '_amazon_animation_id', target_height, 0, 8)
        
        def _on_amazon_enter(e=None):
            amazon_header.config(highlightbackground="#777777")
        def _on_amazon_leave(e=None):
            amazon_header.config(highlightbackground=BORDER_COLOR)
        
        amazon_header.bind("<Button-1>", lambda e: _toggle_amazon())
        amazon_header_content.bind("<Button-1>", lambda e: _toggle_amazon())
        amazon_header_lbl.bind("<Button-1>", lambda e: _toggle_amazon())
        amazon_header.bind("<Enter>", _on_amazon_enter)
        amazon_header.bind("<Leave>", _on_amazon_leave)
        amazon_header_content.bind("<Enter>", _on_amazon_enter)
        amazon_header_content.bind("<Leave>", _on_amazon_leave)
        amazon_header_lbl.bind("<Enter>", _on_amazon_enter)
        amazon_header_lbl.bind("<Leave>", _on_amazon_leave)

        def _toggle_actions():
            if self._actions_expanded:
                self._actions_expanded = False
                actions_header_lbl.config(text="▶ Actions")
                _animate_section(actions_wrapper, actions_container, actions_header_lbl, '_actions_expanded', '_actions_animation_id', 0, actions_wrapper.winfo_height(), 8)
            else:
                self._actions_expanded = True
                actions_header_lbl.config(text="▼ Actions")
                actions_container.pack(side="top", fill="both", expand=True)
                actions_container.update_idletasks()
                target_height = actions_container.winfo_reqheight()
                _animate_section(actions_wrapper, actions_container, actions_header_lbl, '_actions_expanded', '_actions_animation_id', target_height, 0, 8)
        
        def _on_actions_enter(e=None):
            actions_header.config(highlightbackground="#777777")
        def _on_actions_leave(e=None):
            actions_header.config(highlightbackground=BORDER_COLOR)
        
        actions_header.bind("<Button-1>", lambda e: _toggle_actions())
        actions_header_content.bind("<Button-1>", lambda e: _toggle_actions())
        actions_header_lbl.bind("<Button-1>", lambda e: _toggle_actions())
        actions_header.bind("<Enter>", _on_actions_enter)
        actions_header.bind("<Leave>", _on_actions_leave)
        actions_header_content.bind("<Enter>", _on_actions_enter)
        actions_header_content.bind("<Leave>", _on_actions_leave)
        actions_header_lbl.bind("<Enter>", _on_actions_enter)
        actions_header_lbl.bind("<Leave>", _on_actions_leave)

        self._export_file_expanded = True
        self._export_file_animation_id = None
        
        export_file_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        export_file_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        export_file_header = tk.Frame(export_file_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        export_file_header.pack(side="top", fill="x", padx=5, pady=2)
        
        export_file_header_content = tk.Frame(export_file_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        export_file_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        export_file_header_lbl = tk.Label(export_file_header_content, text="▼ Export Files", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        export_file_header_lbl.pack(side="left")
        
        export_file_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        export_file_outer.pack(side="top", fill="x", padx=10, pady=(0, 0))
        
        export_file_outer_inner = tk.Frame(export_file_outer, bg=TOP_MENU_BG)
        export_file_outer_inner.pack(side="top", fill="x", padx=5)
        
        export_file_wrapper = tk.Frame(export_file_outer_inner, bg=TOP_MENU_BG)
        export_file_wrapper.pack(side="top", fill="x")
        export_file_wrapper.pack_propagate(False)
        
        export_file_container = tk.Frame(export_file_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        export_file_container.pack(side="top", fill="both", expand=True)

        export_file_content = tk.Frame(export_file_container, bg=TOP_MENU_BG)
        export_file_content.pack(side="top", fill="x", padx=8, pady=6)

        export_file_selector_row = tk.Frame(export_file_content, bg=TOP_MENU_BG)
        export_file_selector_row.pack(side="top", fill="x", pady=2)
        self._export_file_selector_left = ttk.Combobox(
            export_file_selector_row,
            textvariable=self.export_file_var,
            state="readonly",
            values=self._export_files_list,
            justify="center",
            width=16,
        )
        self._export_file_selector_left.pack(side="left", fill="x", expand=True)

        export_file_buttons_row = tk.Frame(export_file_content, bg=TOP_MENU_BG)
        export_file_buttons_row.pack(side="top", fill="x", pady=(4, 0))
        
        def _add_export_file():
            try:
                existing_nums = []
                for fname in self._export_files_list:
                    try:
                        if fname.startswith("File "):
                            num = int(fname.split()[1])
                            existing_nums.append(num)
                    except (IndexError, ValueError):
                        pass
                
                next_num = 1
                while next_num in existing_nums:
                    next_num += 1
                
                new_file = f"File {next_num}"
                self._export_files_list.append(new_file)
                if hasattr(self, "_export_file_selector_left"):
                    self._export_file_selector_left.configure(values=self._export_files_list)
                if hasattr(self, "_file_selector_left"):
                    self._file_selector_left.configure(values=self._export_files_list)
                self.export_file_var.set(new_file)
            except Exception as e:
                logger.exception(f"Failed to add export file: {e}")
        
        def _remove_export_file():
            try:
                if len(self._export_files_list) <= 1:
                    messagebox.showwarning("Cannot Remove", "You must have at least one export file.")
                    return
                current = self.export_file_var.get()
                if current in self._export_files_list:
                    self._export_files_list.remove(current)
                    for cid, meta in self._items.items():
                        if meta.get("type") not in ("slot", "major") and meta.get("export_file") == current:
                            meta["export_file"] = self._export_files_list[0]
                    if hasattr(self, "_export_file_selector_left"):
                        self._export_file_selector_left.configure(values=self._export_files_list)
                    if hasattr(self, "_file_selector_left"):
                        self._file_selector_left.configure(values=self._export_files_list)
                    self.export_file_var.set(self._export_files_list[0])
            except Exception as e:
                logger.exception(f"Failed to remove export file: {e}")

        def _create_export_button(parent, text, command):
            bg_color = TOP_MENU_ACCENT_GREEN if text == "Add" else TOP_MENU_ACCENT_RED
            hover_color = "#2ecc71" if text == "Add" else "#e74c3c"
            btn_frame = tk.Frame(parent, bg=bg_color, cursor="hand2")
            btn_frame.pack(side="left", fill="x", expand=True, pady=1, padx=(0 if text == "Add" else 2, 2 if text == "Add" else 0))
            lbl = tk.Label(btn_frame, text=text, fg="white", bg=bg_color, font=("Segoe UI", 10, "bold"), pady=4)
            lbl.pack(fill="x")
            def on_click(e=None):
                command()
            def on_enter(e=None):
                btn_frame.configure(bg=hover_color)
                lbl.configure(bg=hover_color)
            def on_leave(e=None):
                btn_frame.configure(bg=bg_color)
                lbl.configure(bg=bg_color)
            btn_frame.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            return btn_frame

        _create_export_button(export_file_buttons_row, "Add", _add_export_file)
        _create_export_button(export_file_buttons_row, "Remove", _remove_export_file)

        export_file_container.update_idletasks()
        export_file_wrapper.config(height=export_file_container.winfo_reqheight())

        def _toggle_export_file():
            if self._export_file_expanded:
                self._export_file_expanded = False
                export_file_header_lbl.config(text="▶ Export Files")
                _animate_section(export_file_wrapper, export_file_container, export_file_header_lbl, '_export_file_expanded', '_export_file_animation_id', 0, export_file_wrapper.winfo_height(), 8)
            else:
                self._export_file_expanded = True
                export_file_header_lbl.config(text="▼ Export Files")
                export_file_container.pack(side="top", fill="both", expand=True)
                export_file_container.update_idletasks()
                target_height = export_file_container.winfo_reqheight()
                _animate_section(export_file_wrapper, export_file_container, export_file_header_lbl, '_export_file_expanded', '_export_file_animation_id', target_height, 0, 8)
        
        def _on_export_file_header_enter(e=None):
            export_file_header.config(highlightbackground="#777777")
        def _on_export_file_header_leave(e=None):
            export_file_header.config(highlightbackground=BORDER_COLOR)
        
        export_file_header.bind("<Button-1>", lambda e: _toggle_export_file())
        export_file_header_content.bind("<Button-1>", lambda e: _toggle_export_file())
        export_file_header_lbl.bind("<Button-1>", lambda e: _toggle_export_file())
        export_file_header.bind("<Enter>", _on_export_file_header_enter)
        export_file_header.bind("<Leave>", _on_export_file_header_leave)
        export_file_header_content.bind("<Enter>", _on_export_file_header_enter)
        export_file_header_content.bind("<Leave>", _on_export_file_header_leave)
        export_file_header_lbl.bind("<Enter>", _on_export_file_header_enter)
        export_file_header_lbl.bind("<Leave>", _on_export_file_header_leave)

        self._asin_expanded = True
        self._asin_animation_id = None
        
        asin_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        asin_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        asin_header = tk.Frame(asin_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        asin_header.pack(side="top", fill="x", padx=5, pady=2)
        
        asin_header_content = tk.Frame(asin_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        asin_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        asin_header_lbl = tk.Label(asin_header_content, text="▼ ASIN", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        asin_header_lbl.pack(side="left")
        
        asin_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        asin_outer.pack(side="top", fill="x", padx=10, pady=(0, 0))
        
        asin_outer_inner = tk.Frame(asin_outer, bg=TOP_MENU_BG)
        asin_outer_inner.pack(side="top", fill="x", padx=5)
        
        asin_wrapper = tk.Frame(asin_outer_inner, bg=TOP_MENU_BG)
        asin_wrapper.pack(side="top", fill="x")
        asin_wrapper.pack_propagate(False)
        
        asin_container = tk.Frame(asin_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        asin_container.pack(side="top", fill="both", expand=True)

        asin_content = tk.Frame(asin_container, bg=TOP_MENU_BG)
        asin_content.pack(side="top", fill="x", padx=8, pady=6)

        asin_selector_row = tk.Frame(asin_content, bg=TOP_MENU_BG)
        asin_selector_row.pack(side="top", fill="x", pady=2)
        self._asin_combo_left = ttk.Combobox(
            asin_selector_row,
            textvariable=self.asin_combo_var,
            state="readonly",
            values=self._asin_list,
            justify="center",
            width=16,
        )
        self._asin_combo_left.pack(side="left", fill="x", expand=True)

        asin_entry_row = tk.Frame(asin_content, bg=TOP_MENU_BG)
        asin_entry_row.pack(side="top", fill="x", pady=2)
        tk.Label(asin_entry_row, text="ASIN:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG, width=5, anchor="w").pack(side="left")
        tk.Entry(asin_entry_row, textvariable=self.sku_var, width=18, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center").pack(side="left", fill="x", expand=True, padx=(4, 0))

        asin_count_row = tk.Frame(asin_content, bg=TOP_MENU_BG)
        asin_count_row.pack(side="top", fill="x", pady=2)
        tk.Label(asin_count_row, text="Count:", fg=TOP_MENU_LABEL_FG, bg=TOP_MENU_BG).pack(side="left")
        tk.Entry(asin_count_row, textvariable=self.count_in_order, width=10, bg=TOP_MENU_INPUT_BG, fg=TOP_MENU_TEXT_FG, insertbackground="white", relief="flat", font=("Segoe UI", 10), justify="center",
                 validate="key", validatecommand=(validate_min1(self), "%P")).pack(side="left", padx=(4, 4))
        
        self.asin_mirror_var = tk.BooleanVar(value=False)
        def _on_mirror_changed(*_):
            try:
                sel = (self.asin_combo_var.get() or "").strip()
                self._asin_mirror[sel] = bool(self.asin_mirror_var.get())
            except Exception:
                pass
        self.asin_mirror_var.trace_add("write", _on_mirror_changed)
        
        asin_mirror_frame = tk.Frame(asin_count_row, bg=TOP_MENU_BG)
        asin_mirror_frame.pack(side="left", padx=(4, 0))
        tk.Checkbutton(
            asin_mirror_frame,
            text="Mirror",
            variable=self.asin_mirror_var,
            bg=TOP_MENU_BG,
            fg=TOP_MENU_TEXT_FG,
            selectcolor=TOP_MENU_INPUT_BG,
            activebackground=TOP_MENU_CONTAINER_BG,
            activeforeground=TOP_MENU_TEXT_FG,
            font=("Segoe UI", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        ).pack(side="left", padx=8, pady=4)

        asin_buttons_row = tk.Frame(asin_content, bg=TOP_MENU_BG)
        asin_buttons_row.pack(side="top", fill="x", pady=(4, 0))

        def _create_asin_button(parent, text, command):
            bg_color = TOP_MENU_ACCENT_GREEN if text == "Add" else TOP_MENU_ACCENT_RED
            hover_color = "#2ecc71" if text == "Add" else "#e74c3c"
            btn_frame = tk.Frame(parent, bg=bg_color, cursor="hand2")
            btn_frame.pack(side="left", fill="x", expand=True, pady=1, padx=(0 if text == "Add" else 2, 2 if text == "Add" else 0))
            lbl = tk.Label(btn_frame, text=text, fg="white", bg=bg_color, font=("Segoe UI", 10, "bold"), pady=4)
            lbl.pack(fill="x")
            def on_click(e=None):
                command()
            def on_enter(e=None):
                btn_frame.configure(bg=hover_color)
                lbl.configure(bg=hover_color)
            def on_leave(e=None):
                btn_frame.configure(bg=bg_color)
                lbl.configure(bg=bg_color)
            btn_frame.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            return btn_frame

        _create_asin_button(asin_buttons_row, "Add", _asin_add)
        _create_asin_button(asin_buttons_row, "Remove", _asin_remove)

        asin_container.update_idletasks()
        asin_wrapper.config(height=asin_container.winfo_reqheight())

        def _toggle_asin():
            if self._asin_expanded:
                self._asin_expanded = False
                asin_header_lbl.config(text="▶ ASIN")
                _animate_section(asin_wrapper, asin_container, asin_header_lbl, '_asin_expanded', '_asin_animation_id', 0, asin_wrapper.winfo_height(), 8)
            else:
                self._asin_expanded = True
                asin_header_lbl.config(text="▼ ASIN")
                asin_container.pack(side="top", fill="both", expand=True)
                asin_container.update_idletasks()
                target_height = asin_container.winfo_reqheight()
                _animate_section(asin_wrapper, asin_container, asin_header_lbl, '_asin_expanded', '_asin_animation_id', target_height, 0, 8)
        
        def _on_asin_header_enter(e=None):
            asin_header.config(highlightbackground="#777777")
        def _on_asin_header_leave(e=None):
            asin_header.config(highlightbackground=BORDER_COLOR)
        
        asin_header.bind("<Button-1>", lambda e: _toggle_asin())
        asin_header_content.bind("<Button-1>", lambda e: _toggle_asin())
        asin_header_lbl.bind("<Button-1>", lambda e: _toggle_asin())
        asin_header.bind("<Enter>", _on_asin_header_enter)
        asin_header.bind("<Leave>", _on_asin_header_leave)
        asin_header_content.bind("<Enter>", _on_asin_header_enter)
        asin_header_content.bind("<Leave>", _on_asin_header_leave)
        asin_header_lbl.bind("<Enter>", _on_asin_header_enter)
        asin_header_lbl.bind("<Leave>", _on_asin_header_leave)

        self._asin_combo_left.bind("<<ComboboxSelected>>", lambda e: (logger.debug("[ASIN_EVENT] Left ComboboxSelected event triggered"), _on_asin_combo(e)))

        self._pens_expanded = False
        self._pens_animation_id = None
        
        pens_header_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        pens_header_outer.pack(side="top", fill="x", padx=10, pady=(5, 0))
        
        pens_header = tk.Frame(pens_header_outer, bg=TOP_MENU_CONTAINER_BG, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
        pens_header.pack(side="top", fill="x", padx=5, pady=2)
        
        pens_header_content = tk.Frame(pens_header, bg=TOP_MENU_CONTAINER_BG, cursor="hand2")
        pens_header_content.pack(side="top", fill="x", padx=8, pady=6)
        
        pens_header_lbl = tk.Label(pens_header_content, text="▶ Pens", fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_CONTAINER_BG, font=("Segoe UI", 11, "bold"), cursor="hand2")
        pens_header_lbl.pack(side="left")
        
        pens_outer = tk.Frame(left_bar, bg=TOP_MENU_BG)
        pens_outer.pack(side="top", fill="x", padx=10, pady=(0, 10))
        
        pens_outer_inner = tk.Frame(pens_outer, bg=TOP_MENU_BG)
        pens_outer_inner.pack(side="top", fill="x", padx=5)
        
        pens_wrapper = tk.Frame(pens_outer_inner, bg=TOP_MENU_BG, height=0)
        pens_wrapper.pack(side="top", fill="x")
        pens_wrapper.pack_propagate(False)
        
        pens_container = tk.Frame(pens_wrapper, bg=TOP_MENU_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        
        pens_frame = tk.Frame(pens_container, bg=TOP_MENU_BG)
        pens_frame.pack(side="top", fill="x", padx=8, pady=6)

        def _animate_pens(target_height, current_height, step):
            if self._pens_animation_id:
                self.after_cancel(self._pens_animation_id)
            
            if abs(current_height - target_height) < step:
                pens_wrapper.config(height=target_height)
                if target_height == 0:
                    pens_container.pack_forget()
                self._pens_animation_id = None
                return
            
            if current_height < target_height:
                new_height = min(current_height + step, target_height)
            else:
                new_height = max(current_height - step, target_height)
            
            pens_wrapper.config(height=new_height)
            self._pens_animation_id = self.after(10, lambda: _animate_pens(target_height, new_height, step))

        def _toggle_pens():
            if self._pens_expanded:
                self._pens_expanded = False
                pens_header_lbl.config(text="▶ Pens")
                _animate_pens(0, pens_wrapper.winfo_height(), 8)
            else:
                self._pens_expanded = True
                pens_header_lbl.config(text="▼ Pens")
                pens_container.pack(side="top", fill="both", expand=True)
                pens_container.update_idletasks()
                target_height = pens_container.winfo_reqheight()
                _animate_pens(target_height, 0, 8)
        
        def _on_header_enter(e=None):
            pens_header.config(highlightbackground="#777777")
        
        def _on_header_leave(e=None):
            pens_header.config(highlightbackground=BORDER_COLOR)
        
        pens_header.bind("<Button-1>", lambda e: _toggle_pens())
        pens_header_content.bind("<Button-1>", lambda e: _toggle_pens())
        pens_header_lbl.bind("<Button-1>", lambda e: _toggle_pens())
        pens_header.bind("<Enter>", _on_header_enter)
        pens_header.bind("<Leave>", _on_header_leave)
        pens_header_content.bind("<Enter>", _on_header_enter)
        pens_header_content.bind("<Leave>", _on_header_leave)
        pens_header_lbl.bind("<Enter>", _on_header_enter)
        pens_header_lbl.bind("<Leave>", _on_header_leave)


        def _create_pens_button(parent, text, command, is_settings=False):
            if is_settings:
                btn_frame = tk.Frame(parent, bg="white", cursor="hand2")
                fg_color = "black"
                bg_color = "white"
                hover_bg = "#e0e0e0"
            else:
                btn_frame = tk.Frame(parent, bg=BUTTON_COLOR, cursor="hand2")
                fg_color = "white"
                bg_color = BUTTON_COLOR
                hover_bg = BUTTON_HOVER_COLOR
            btn_frame.pack(side="top", fill="x", pady=1)
            lbl = tk.Label(btn_frame, text=text, fg=fg_color, bg=bg_color, font=("Segoe UI", 10, "bold"), pady=4)
            lbl.pack(fill="x")
            def on_click(e=None):
                command()
            def on_enter(e=None):
                btn_frame.configure(bg=hover_bg)
                lbl.configure(bg=hover_bg)
            def on_leave(e=None):
                btn_frame.configure(bg=bg_color)
                lbl.configure(bg=bg_color)
            btn_frame.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            return btn_frame

        _create_pens_button(pens_frame, "Settings", lambda: None, is_settings=True)
        _create_pens_button(pens_frame, "Create Pen", lambda: None)
        _create_pens_button(pens_frame, "Delete Pen", lambda: None)


        shortcuts = tk.Frame(bar, bg="black")
        shortcuts.pack(side="right", padx=8, pady=8)
        shortcuts.grid_columnconfigure(0, weight=0)
        shortcuts.grid_columnconfigure(1, weight=0)

        def _on_export_file_change(*_):
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            obj = self._items[sel]
            if obj.get("type") in ("slot", "major"):
                return
            obj["export_file"] = str(self.sel_export_file.get() or "File 1").strip()
        self.sel_export_file.trace_add("write", _on_export_file_change)

        self.custom_images = CustomImagesManager(self)

        self.sel_custom_image_line = tk.Frame(row2, bg="black")
        _custom_img_line = tk.Frame(self.sel_custom_image_line, bg="black")
        _custom_img_line.pack(side="top", anchor="w")
        _custom_img_wrap = tk.Frame(_custom_img_line, bg="#6f6f6f")
        _custom_img_wrap.pack(side="left", padx=6, pady=8)
        tk.Label(_custom_img_wrap, text="Custom:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)

        self.sel_custom_image = tk.StringVar(value="")
        self._suppress_custom_image_trace = False
        self._sel_custom_image_combo = ttk.Combobox(
            _custom_img_wrap,
            textvariable=self.sel_custom_image,
            state="readonly",
            values=[],
            justify="center",
            width=10
        )
        self._sel_custom_image_combo.pack(side="left")

        def _on_custom_image_change(*_):
            if getattr(self, "_suppress_custom_image_trace", False):
                return
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            obj = self._items[sel]
            if obj.get("type") != "image":
                return
            obj["custom_image"] = str(self.sel_custom_image.get() or "").strip()
        self.sel_custom_image.trace_add("write", _on_custom_image_change)
        
        # Buttons line (Import/Remove) stacked below
        def _on_import_custom_image():
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            obj = self._items[sel]
            if obj.get("type") != "image":
                return
            self.custom_images.import_custom_image_for_object(obj)
        
        def _on_remove_custom_image():
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            obj = self._items[sel]
            if obj.get("type") != "image":
                return
            self.custom_images.remove_custom_image_from_object(obj)
        
        _btn_line = tk.Frame(self.sel_custom_image_line, bg="black")
        _btn_line.pack(side="top", anchor="w")
        # Import
        _import_btn = create_button(
            ButtonInfo(
                parent=_btn_line,
                text_info=TextInfo(text="Import", color=COLOR_TEXT, font_size=10),
                command=_on_import_custom_image,
                background_color="#000000",
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_DARK,
                active_color=COLOR_PILL,
                padding_x=15,
                padding_y=4,
            )
        )
        _import_btn.pack(side="left", padx=(6, 4))
        
        # Remove
        _remove_btn = create_button(
            ButtonInfo(
                parent=_btn_line,
                text_info=TextInfo(text="Remove", color=COLOR_TEXT, font_size=10),
                command=_on_remove_custom_image,
                background_color="#000000",
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_DARK,
                active_color=COLOR_PILL,
                padding_x=12,
                padding_y=4,
            )
        )
        _remove_btn.pack(side="left", padx=8)
        
        # Initially hide custom image selector
        self.sel_custom_image_line.pack_forget()

        def _on_flags_change(*_):
            if getattr(self, "_suppress_flag_traces", False):
                return
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            self._items[sel]["is_options"] = bool(self.sel_is_options.get())
            self._items[sel]["is_static"] = bool(self.sel_is_static.get())
        self.sel_is_options.trace_add("write", _on_flags_change)
        self.sel_is_static.trace_add("write", _on_flags_change)

        def _on_name_change(*_):
            sel = getattr(self.selection, "_selected", None)
            if not sel or sel not in self._items:
                return
            self._items[sel]["amazon_label"] = str(self.sel_amazon_label.get() or "").strip()
        self.sel_amazon_label.trace_add("write", _on_name_change)

        self.fonts = FontsManager(self)

        self._zoom: float = 1.5
        self.selection = CanvasSelection(self)

        self.sel_x.trace_add("write", self.selection.on_pos_change)
        self.sel_y.trace_add("write", self.selection.on_pos_change)
        self.sel_w.trace_add("write", self.selection.on_size_change)
        self.sel_h.trace_add("write", self.selection.on_size_change)
        self.sel_angle.trace_add("write", self.selection.on_angle_change)

        self.board = tk.Frame(self, bg="black")
        self.board.pack(expand=True, fill="both", padx=0, pady=0)
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
                        font_size=16,
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
                        font_size=16,
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
                        # Treat barcode the same as rect: label must be above the rotated overlay polygon
                        if meta.get("type") in ("rect", "barcode", "major"):
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
            item_type = meta.get("type")
            if item_type not in ("rect", "barcode"):
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
            # Resolve color: support hex (#rrggbb) and named colors via tkinter
            try:
                color_rgba = (255, 255, 255, 255)
                if isinstance(fill, str) and fill:
                    if fill.startswith("#") and len(fill) == 7:
                        r = int(fill[1:3], 16); g = int(fill[3:5], 16); b = int(fill[5:7], 16)
                        color_rgba = (r, g, b, 255)
                    else:
                        # Attempt tkinter color resolution
                        try:
                            r, g, b = self.canvas.winfo_rgb(fill)
                            # winfo_rgb returns 16-bit per channel; convert to 8-bit
                            color_rgba = (r // 256, g // 256, b // 256, 255)
                        except Exception:
                            pass
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

    def _chip(self, parent, label, var, width=8, label_padx=6, pady=8):
        box = tk.Frame(parent, bg="#6f6f6f")
        box.pack(side="left", padx=6, pady=pady)
        tk.Label(box, text=label, bg="#6f6f6f", fg="white").pack(side="left", padx=label_padx)
        tk.Entry(box, textvariable=var, width=width, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        return box

    def _create_tool_tile(self, parent, icon_image: Optional[tk.PhotoImage], icon_text: Optional[str], label_text: str, command):
        """Create a square tile with an icon (image or text) and a label underneath."""
        wrap = tk.Frame(parent, bg="black")
        wrap.pack(side="left", padx=6, pady=6)

        tile_size = 30
        tile = tk.Frame(wrap, bg="#c7c7c7", width=tile_size, height=tile_size, relief="flat", bd=0)
        tile.pack()
        tile.pack_propagate(False)

        if icon_image is not None:
            icon_lbl = tk.Label(tile, image=icon_image, bg="#c7c7c7")
            icon_lbl.pack(expand=True)
        else:
            icon_lbl = tk.Label(tile, text=(icon_text or ""), bg="#c7c7c7", fg="#000000", font=("Myriad Pro", 20, "bold"))
            icon_lbl.pack(expand=True)

        lbl = tk.Label(wrap, text=label_text, fg=TOP_MENU_TEXT_FG, bg=TOP_MENU_BG, font=("Segoe UI", 8))
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
        # Base rect initially invisible for general rects; barcode will be made visible below
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
            type="rect" if label != "Barcode" else "barcode",
            w_mm=float(qw_mm),
            h_mm=float(qh_mm),
            x_mm=float(sx_mm),
            y_mm=float(sy_mm),
            label_id=None,
            outline=outline,
            canvas_id=rect,
            z=int(max_z + 1),
            export_file=self._export_files_list[0],
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
            self._items[rect]["label_fill"] = str(text_fill)
        except Exception:
            raise
        # Base rect stays invisible for both rect and barcode - overlay provides visibility
        # Create rotated label image now
        try:
            self._update_rect_label_image(rect)
        except Exception:
            logger.exception("Failed to create rotated label image for placeholder")
        # Create initial overlay polygon for both rects and barcodes to show rotation
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

    def _drop_barcode(self):
        """Create a barcode on the canvas. Only allow 1 barcode at a time."""
        # Count existing barcodes BEFORE creating new one
        barcode_count = sum(1 for cid, meta in self._items.items() if meta.get("type") == "barcode")
        if barcode_count >= 1:
            # Already have 1 barcode, do nothing silently
            return
        
        # Create a rectangle with black border and "Barcode" text label
        default_w = 80.0  # mm
        default_h = 30.0  # mm
        
        # Create using the standard placeholder method (handles zoom, scaling, etc.)
        self.create_placeholder("Barcode", default_w, default_h, text_fill="#000000", outline="black")
        
        # Locate the newly created barcode by label and highest z, ensure it's configured correctly
        max_z = -1
        barcode_id = None
        for cid, meta in self._items.items():
            if str(meta.get("label", "")) == "Barcode":
                z = int(meta.get("z", 0))
                if z > max_z:
                    max_z = z
                    barcode_id = cid
        if barcode_id:
            # Ensure type is barcode (in case of legacy behavior)
            self._items[barcode_id]["type"] = "barcode"
            # Barcode uses overlay polygon like rect to show rotation visually
            # Base rect stays invisible, overlay provides the visual representation
            # Label styling default for barcode
            self._items[barcode_id]["label_fill"] = "black"
            logger.info("Created barcode rect")

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
                                            new_meta["export_file"] = str(om.get("export_file", "File 1"))
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
                                                self._items[tid]["export_file"] = str(om.get("export_file", "File 1"))
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
        # Require at least one ASIN to continue
        try:
            if not getattr(self, "_asin_list", None) or len(self._asin_list) == 0:
                messagebox.showwarning("Missing ASINs", "Please add at least one ASIN before proceeding.")
                return
        except Exception:
            messagebox.showwarning("Missing ASINs", "Please add at least one ASIN before proceeding.")
            return
        
        sku_name_val = self.sku_name_var.get().strip()
        if not sku_name_val:
            messagebox.showwarning("Missing ASIN", "Please select an ASIN name before proceeding.")
            return
        if len(sku_name_val) < 3:
            messagebox.showwarning("Invalid ASIN", "ASIN name is too short.")
            return

        state.sku_name = sku_name_val
        # Validate CMYK fields before proceeding: prefer per-field invalid flags set by focus handlers/restore.
        try:
            jig_invalid = getattr(self, "_jig_cmyk_invalid", False)
            obj_invalid = getattr(self, "_obj_cmyk_invalid", False)
            # Also double-check current split length in case user bypassed focus events
            if hasattr(self, "jig_cmyk") and not jig_invalid:
                jig_invalid = (len(str(self.jig_cmyk.get() or "").split(",")) != 4)
            if hasattr(self, "obj_cmyk") and not obj_invalid:
                obj_invalid = (len(str(self.obj_cmyk.get() or "").split(",")) != 4)
            if jig_invalid or obj_invalid:
                # Build a single consolidated message
                msgs = []
                if jig_invalid:
                    msgs.append("Jig CMYK must contain exactly 4 comma-separated values (C,M,Y,K).")
                if obj_invalid:
                    msgs.append("Object CMYK must contain exactly 4 comma-separated values (C,M,Y,K).")
                messagebox.showerror("Invalid CMYK", "\n".join(msgs))
                return
        except Exception:
            logger.exception("Failed to validate CMYK before proceeding")
        state.pkg_x = self.jig_x.get().strip()
        state.pkg_y = self.jig_y.get().strip()
        # Count only image items. Text items are stored with type 'text'
        # Snapshot current side (exclude slots) so both sides are up-to-date
        current_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
        self._scene_store[self._current_side] = current_no_slots
        # Collect slots from the current canvas (slots are shared across sides)
        slots_only = [it for it in self._serialize_scene() if it.get("type") == "slot"]
        # Prepare background job to render PDFs and write JSON without blocking UI
        p_jig = os.path.join(OUTPUT_PATH, "Cut_jig.svg")
        p_pattern = os.path.join(OUTPUT_PATH, "Single_pattern.svg")
        p_front = os.path.join(OUTPUT_PATH, "Test_file_frontside.pdf")
        p_front_png = os.path.join(OUTPUT_PATH, "Test_file_frontside.png")
        p_front_jpg = os.path.join(OUTPUT_PATH, "Test_file_frontside.jpg")
        p_back = os.path.join(OUTPUT_PATH, "Test_file_backside.pdf")
        p_back_png = os.path.join(OUTPUT_PATH, "Test_file_backside.png")
        p_back_jpg = os.path.join(OUTPUT_PATH, "Test_file_backside.jpg")
        try:
            jx = float(self.jig_x.get() or 0.0)
            jy = float(self.jig_y.get() or 0.0)
        except Exception:
            jx, jy = 296.0, 394.5831
        front_items = list(slots_only) + list(self._scene_store.get("front") or [])
        back_items = list(slots_only) + list(self._scene_store.get("back") or [])

        # Ensure images are stored internally per product and update paths
        try:

            is_sticker = self.sticker_var.get()

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
            
            # Copy custom images from each object's custom_images dict to product folder
            def _copy_custom_images_for_objects(items_list):
                """Copy custom images to product folder and update paths in object metadata."""
                for obj in items_list:
                    try:
                        if obj.get("type") != "image":
                            continue
                        
                        # Get this object's custom images dict
                        custom_imgs = obj.get("custom_images", {})
                        if not custom_imgs or not isinstance(custom_imgs, dict):
                            continue
                        
                        # Copy each custom image file to product folder
                        updated_imgs = {}
                        for name, src_path_str in custom_imgs.items():
                            try:
                                src_path = _Path(src_path_str)
                                if not src_path.exists():
                                    logger.warning(f"Custom image not found: {src_path_str}")
                                    updated_imgs[name] = src_path_str
                                    continue
                                
                                # Check if already under current product folder
                                try:
                                    is_under_products = str(src_path).startswith(str(PRODUCTS_PATH))
                                except Exception:
                                    is_under_products = False
                                
                                needs_copy = (not is_under_products) or (src_path.parent != product_folder)
                                
                                if needs_copy:
                                    dst_path = product_folder / src_path.name
                                    try:
                                        _shutil.copy2(src_path, dst_path)
                                        logger.debug(f"Copied custom image: %s -> %s", src_path, dst_path)
                                    except _shutil.SameFileError:
                                        logger.debug(f"Custom image already exists: %s", dst_path)
                                    except Exception:
                                        logger.exception(f"Failed to copy: {src_path}")
                                        try:
                                            _shutil.copyfile(src_path, dst_path)
                                        except Exception:
                                            logger.exception(f"Failed second copy: {src_path}")
                                            updated_imgs[name] = src_path_str
                                            continue
                                    
                                    # Update to new path
                                    updated_imgs[name] = str(dst_path)
                                else:
                                    # Already in correct location
                                    updated_imgs[name] = src_path_str
                            except Exception as e:
                                logger.exception(f"Failed processing custom image '{name}': {e}")
                                updated_imgs[name] = src_path_str
                        
                        # Update object's custom_images dict with new paths
                        obj["custom_images"] = updated_imgs
                    except Exception as e:
                        logger.exception(f"Failed processing custom images for object: {e}")
            
            try:
                _copy_custom_images_for_objects(front_items)
                _copy_custom_images_for_objects(back_items)
            except Exception:
                logger.exception("Failed to copy custom images to product folder")
        except Exception:
            logger.exception("Failed to prepare internal product images and update paths")

        # Validate that all non-slot, non-barcode, non-static objects have a non-empty amazon_label
        # Check objects for ALL ASINs, not just current canvas
        try:
            def _missing_label(obj: dict) -> bool:
                try:
                    obj_type = str(obj.get("type", ""))
                    # Skip validation for slots and barcodes
                    if obj_type in ("slot", "barcode"):
                        return False
                    # Skip validation for static objects
                    if bool(obj.get("is_static", False)):
                        return False
                    return str(obj.get("amazon_label", "") or "").strip() == ""
                except Exception:
                    return True
            
            # Save current ASIN state before validation
            self._save_current_asin_objects()
            
            # Check all ASINs for missing labels
            missing_asins = []
            for asin in self._asin_list:
                if asin in self._asin_objects:
                    asin_front = self._asin_objects[asin].get("front", [])
                    asin_back = self._asin_objects[asin].get("back", [])
                    
                    if any(_missing_label(it) for it in (asin_front + asin_back)):
                        missing_asins.append(asin)
            
            if missing_asins:
                messagebox.showwarning(
                    "Missing Amazon label",
                    f"Objects in ASIN(s) {', '.join(missing_asins)} have empty Amazon Label.\nPlease fill all labels before proceeding.",
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
                            # Export file assignment
                            "export_file": str(it.get("export_file", "File 1")),
                            # Custom images dict (name -> path mapping) and selected custom image
                            "custom_images": dict(it.get("custom_images", {})),
                            "custom_image": str(it.get("custom_image", "") or ""),
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
                            # Export file assignment
                            "export_file": str(it.get("export_file", "File 1")),
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
                            # Export file assignment
                            "export_file": str(it.get("export_file", "File 1")),
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
                            # Export file assignment
                            "export_file": str(it.get("export_file", "File 1")),
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
                "jig": {"width_mm": float(jx), "height_mm": float(jy), "cmyk": self._normalize_cmyk(self.jig_cmyk.get() if hasattr(self, "jig_cmyk") else "75,0,75,0")},
                "slot_count": int(slot_count),
                "objects_count": {
                    "images": int(images_cnt_front + images_cnt_back),
                    "text": int(text_cnt_front + text_cnt_back),
                },
                # Save export files list
                "export_files": list(self._export_files_list) if hasattr(self, "_export_files_list") else ["File 1"],
            }
            # Persist object CMYK at scene level
            try:
                scene_top["object_cmyk"] = self._normalize_cmyk(self.obj_cmyk.get() if hasattr(self, "obj_cmyk") else "0,100,0,0")
            except Exception:
                scene_top["object_cmyk"] = "0,0,0,0"
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

            # Extract optional barcode objects per side (barcode does not belong to slots)
            def _extract_barcode(items_for_side: list[dict]) -> dict | None:
                try:
                    for it in items_for_side:
                        if str(it.get("type", "")) == "barcode":
                            # Return a shallow copy to avoid accidental mutations later
                            return dict(it)
                except Exception:
                    logger.exception("Failed to extract barcode from items_for_side")
                return None

            front_barcode = _extract_barcode(self._scene_store.get("front") or [])
            back_barcode = _extract_barcode(self._scene_store.get("back") or [])

            # Save current ASIN's objects before building JSON
            self._save_current_asin_objects()
            
            logger.debug(f"[JSON_SAVE] _asin_objects contents: {list(self._asin_objects.keys())}")
            for asin, sides in self._asin_objects.items():
                logger.debug(f"[JSON_SAVE]   '{asin}': front={len(sides.get('front', []))}objs, back={len(sides.get('back', []))}objs")
            
            # Persist ASINs as [asin, count] pairs from current selection list and counts
            try:
                asin_pairs = []
                for a in list(getattr(self, "_asin_list", []) or []):
                    try:
                        c = int((getattr(self, "_asin_counts", {}) or {}).get(a, 1))
                    except Exception:
                        c = 1
                    try:
                        m = bool((getattr(self, "_asin_mirror", {}) or {}).get(a, False))
                    except Exception:
                        m = False
                    # Persist ASIN as [asin, count, mirror]
                    asin_pairs.append([a, max(1, c), m])
            except Exception:
                asin_pairs = []

            # Build per-ASIN objects structure with proper slot grouping
            asin_objects_map = {}
            logger.debug(f"[JSON_SAVE] Building ASINObjects for ASINs: {self._asin_list}")
            
            # Get shared slots from canvas (same for all ASINs)
            slots_only = [it for it in self._serialize_scene() if it.get("type") == "slot"]
            logger.debug(f"[JSON_SAVE] Found {len(slots_only)} shared slots")
            
            for asin in self._asin_list:
                if asin in self._asin_objects:
                    # Get objects for this ASIN (WITHOUT slots)
                    asin_front_objects = self._asin_objects[asin].get("front", [])
                    asin_back_objects = self._asin_objects[asin].get("back", [])
                    
                    # Combine shared slots + this ASIN's objects (like old logic)
                    asin_front_items = list(slots_only) + list(asin_front_objects)
                    asin_back_items = list(slots_only) + list(asin_back_objects)
                    
                    logger.debug(f"[JSON_SAVE] Processing '{asin}': front={len(asin_front_items)} items (slots+objs), back={len(asin_back_items)} items")
                    
                    # Use old logic: _compose_side + _group_side_by_major
                    asin_front_grouped = _group_side_by_major(_compose_side(asin_front_items, state.sku_name, state.prev_sku_name))
                    asin_back_grouped = _group_side_by_major(_compose_side(asin_back_items, state.sku_name, state.prev_sku_name))
                    
                    logger.debug(f"[JSON_SAVE] After grouping '{asin}': front={len(asin_front_grouped)} groups, back={len(asin_back_grouped)} groups")
                    
                    # Extract barcodes for this ASIN
                    asin_front_barcode = _extract_barcode(asin_front_objects)
                    asin_back_barcode = _extract_barcode(asin_back_objects)
                    
                    asin_data = {
                        "Frontside": asin_front_grouped,
                        "Backside": asin_back_grouped,
                    }
                    
                    if asin_front_barcode:
                        asin_data["FrontsideBarcode"] = asin_front_barcode
                    if asin_back_barcode:
                        asin_data["BacksideBarcode"] = asin_back_barcode
                    
                    asin_objects_map[asin] = asin_data
                    logger.debug(f"[JSON_SAVE] Added '{asin}' to ASINObjects map")
                else:
                    logger.warning(f"[JSON_SAVE] ASIN '{asin}' not found in _asin_objects!")

            combined = {
                "ASINs": asin_pairs,
                "SkuName": state.sku_name or "",
                "Scene": scene_top,
                "ASINObjects": asin_objects_map,
            }
        except Exception as e:
            logger.exception(f"Failed to build combined JSON: {e}")
            combined = {"Sku": str(state.sku_name or ""), "Scene": {}, "Frontside": {}, "Backside": {}}
        json_path = PRODUCTS_PATH / f"{state.sku_name}.json"

        # Parse export formats and DPI like order_range.py
        try:
            fmt_s = (self.format_var.get() if hasattr(self, "format_var") else "pdf").strip()
        except Exception:
            fmt_s = "pdf"
        fmts = [f.strip().lower() for f in fmt_s.split(",") if f.strip()]
        export_formats: list[str] = []
        seen = set()
        for f in fmts:
            if f == "jpeg":
                f = "jpg"
            if f in ("pdf", "png", "jpg") and f not in seen:
                seen.add(f)
                export_formats.append(f)
        if not export_formats:
            export_formats = ["pdf"]
        try:
            dpi_s = (self.dpi_var.get() if hasattr(self, "dpi_var") else "1200").strip()
            export_dpi = int(dpi_s or "1200")
            if export_dpi <= 0:
                export_dpi = 1200
        except Exception:
            export_dpi = 1200
        self._export_formats = export_formats
        self._export_dpi = int(export_dpi)

        # Mark processing and launch worker thread
        state.is_processing = True

        def _worker():
            try:
                # Get export files list
                export_files_to_render = list(getattr(self, "_export_files_list", ["File 1"]))
                fmts = list(getattr(self, "_export_formats", ["pdf"]))
                dpi_v = int(getattr(self, "_export_dpi", 1200))
                
                # Group items by export file for both front and back
                def _group_by_export_file(items_list):
                    """Group items by their export_file assignment, excluding slots"""
                    grouped = {}
                    for item in items_list:
                        if item.get("type") == "slot":
                            # Skip slots - they should not be exported
                            continue
                        else:
                            # Regular objects go to their assigned file
                            ef = item.get("export_file", "File 1")
                            if ef not in grouped:
                                grouped[ef] = []
                            grouped[ef].append(item)
                    return grouped
                
                front_grouped = _group_by_export_file(front_items)
                back_grouped = _group_by_export_file(back_items)
                
                # Render each export file separately
                for export_file_name in export_files_to_render:
                    # Get items for this export file
                    front_items_for_file = front_grouped.get(export_file_name, [])
                    back_items_for_file = back_grouped.get(export_file_name, [])
                    
                    # Count non-slot items to determine if file has content
                    front_objects = [it for it in front_items_for_file if it.get("type") != "slot"]
                    back_objects = [it for it in back_items_for_file if it.get("type") != "slot"]
                    
                    # Skip if no objects in this file
                    if not front_objects and not back_objects:
                        logger.debug(f"Skipping {export_file_name} - no objects assigned")
                        continue
                    
                    # Generate file names for this export file
                    file_suffix = export_file_name.split(' ')[-1]  # e.g., "File 1" -> "1"
                    
                    # Render frontside for this export file
                    if front_objects:
                        logger.debug(f"Rendering frontside for {export_file_name}...")
                        state.processing_message = f"Rendering frontside for {export_file_name}..."
                        if state.is_cancelled:
                            logger.debug(f"Processing cancelled")
                            return
                        
                        p_front_file = os.path.join(OUTPUT_PATH, f"Test_file_frontside_{file_suffix}.pdf")
                        p_front_png_file = os.path.join(OUTPUT_PATH, f"Test_file_frontside_{file_suffix}.png")
                        p_front_jpg_file = os.path.join(OUTPUT_PATH, f"Test_file_frontside_{file_suffix}.jpg")
                        
                        did_pdf = False
                        if "pdf" in fmts:
                            self._render_scene_to_pdf(p_front_file, front_items_for_file, jx, jy, dpi=dpi_v)
                            did_pdf = True
                        elif ("png" in fmts) or ("jpg" in fmts):
                            tmp_pdf = os.path.join(TEMP_FOLDER, f"__tmp_front_{file_suffix}.pdf")
                            try:
                                self._render_scene_to_pdf(tmp_pdf, front_items_for_file, jx, jy, dpi=dpi_v)
                            finally:
                                try:
                                    os.remove(tmp_pdf)
                                except Exception:
                                    pass
                        
                        if "png" in fmts:
                            try:
                                self.exporter.save_last_render_as_png(p_front_png_file)
                            except Exception:
                                logger.exception(f"Failed to save front PNG for {export_file_name}; continuing")
                        if "jpg" in fmts:
                            try:
                                self.exporter.save_last_render_as_jpg(p_front_jpg_file)
                            except Exception:
                                logger.exception(f"Failed to save front JPG for {export_file_name}; continuing")
                    
                    # Render backside for this export file
                    if back_objects:
                        logger.debug(f"Rendering backside for {export_file_name}...")
                        state.processing_message = f"Rendering backside for {export_file_name}..."
                        if state.is_cancelled:
                            logger.debug(f"Processing cancelled")
                            return
                        
                        p_back_file = os.path.join(OUTPUT_PATH, f"Test_file_backside_{file_suffix}.pdf")
                        p_back_png_file = os.path.join(OUTPUT_PATH, f"Test_file_backside_{file_suffix}.png")
                        p_back_jpg_file = os.path.join(OUTPUT_PATH, f"Test_file_backside_{file_suffix}.jpg")
                        
                        did_pdf = False
                        if "pdf" in fmts:
                            self._render_scene_to_pdf(p_back_file, back_items_for_file, jx, jy, dpi=dpi_v)
                            did_pdf = True
                        elif ("png" in fmts) or ("jpg" in fmts):
                            tmp_pdf_b = os.path.join(TEMP_FOLDER, f"__tmp_back_{file_suffix}.pdf")
                            try:
                                self._render_scene_to_pdf(tmp_pdf_b, back_items_for_file, jx, jy, dpi=dpi_v)
                            finally:
                                try:
                                    os.remove(tmp_pdf_b)
                                except Exception:
                                    pass
                        
                        if "png" in fmts:
                            try:
                                self.exporter.save_last_render_as_png(p_back_png_file)
                            except Exception:
                                logger.exception(f"Failed to save back PNG for {export_file_name}; continuing")
                        if "jpg" in fmts:
                            try:
                                self.exporter.save_last_render_as_jpg(p_back_jpg_file)
                            except Exception:
                                logger.exception(f"Failed to save back JPG for {export_file_name}; continuing")
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

        # Persist actual clamped mm (top-left of rotated bounds)
        try:
            ax_mm = self._snap_mm((new_left - (x0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6)))
            ay_mm = self._snap_mm((new_top - (y0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6)))
        except Exception:
            ax_mm, ay_mm = float(x_mm_i), float(y_mm_i)

        # next z
        max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        self._items[rect] = CanvasObject(
            type="rect",
            w_mm=float(w_mm_i),
            h_mm=float(h_mm_i),
            x_mm=float(ax_mm),
            y_mm=float(ay_mm),
            label_id=None,
            outline=outline,
            canvas_id=rect,
            z=int(max_z + 1),
            angle=float(ang),
            export_file=self._export_files_list[0],
        )
        try:
            self._items[rect]["label"] = str(label)
            # Set label_fill so it persists and is used by _update_rect_label_image
            self._items[rect]["label_fill"] = str(text_fill)
        except Exception:
            raise
        try:
            self._update_rect_label_image(rect)
        except Exception:
            logger.exception("Failed to render rotated rect label on create")
        # Create overlay to visualize rotation; base rect stays invisible
        self._update_rect_overlay(rect, self._items[rect], new_left, new_top, w, h)
        
        # Auto-save to current ASIN after adding new object
        try:
            logger.debug(f"[OBJECT_CREATE] Rect created: id={rect}, label='{label}', x={x_mm:.2f}, y={y_mm:.2f} - auto-saving to ASIN")
            self._save_current_asin_objects()
        except Exception:
            pass
        
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
            export_file=self._export_files_list[0],
        )
        
        # Auto-save to current ASIN after adding new object
        try:
            logger.debug(f"[OBJECT_CREATE] Text created: id={tid}, text='{text}', x={x_mm:.2f}, y={y_mm:.2f} - auto-saving to ASIN")
            self._save_current_asin_objects()
        except Exception:
            pass
        
        return tid

    def _save_current_asin_objects(self):
        """Save current canvas objects to the current ASIN's storage (both sides)."""
        try:
            current_asin = state.asins[0][0] if state.asins else None
            if current_asin:
                # Create ASIN entry if it doesn't exist
                if current_asin not in self._asin_objects:
                    self._asin_objects[current_asin] = {"front": [], "back": []}
                    logger.debug(f"[ASIN] Created new entry for '{current_asin}'")
                
                # Save only objects (NOT slots - they're shared!)
                all_serialized = self._serialize_scene()
                current_objects = [it for it in all_serialized if it.get("type") != "slot"]
                
                other_side = "back" if self._current_side == "front" else "front"
                other_objects = [it for it in self._scene_store.get(other_side, []) if it.get("type") != "slot"]
                
                logger.debug(f"[ASIN] Saved '{current_asin}': {self._current_side}={len(current_objects)} objs, {other_side}={len(other_objects)} objs")
                
                self._asin_objects[current_asin][self._current_side] = current_objects
                self._asin_objects[current_asin][other_side] = other_objects
        except Exception:
            logger.exception("Failed to save current ASIN objects")
    
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
                        # Export file assignment
                        "export_file": str(meta.get("export_file", "File 1")),
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
                    custom_imgs_dict = dict(meta.get("custom_images", {}))
                    custom_img_selected = str(meta.get("custom_image", ""))
                    logger.info(f"Serializing image cid={cid}: custom_images={custom_imgs_dict}, custom_image={custom_img_selected}")
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
                        # Export file assignment
                        "export_file": str(meta.get("export_file", "File 1")),
                        # Custom images (name -> path mapping) and selected custom image
                        "custom_images": custom_imgs_dict,
                        "custom_image": custom_img_selected,
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
                        # Export file assignment
                        "export_file": str(meta.get("export_file", "File 1")),
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize text item {cid}: {e}")
                    continue
            elif t == "barcode":
                try:
                    label_text = str(meta.get("label", "Barcode"))
                    items.append({
                        "type": "barcode",
                        "amazon_label": meta.amazon_label,
                        "is_options": bool(meta.get("is_options", False)),
                        "is_static": bool(meta.get("is_static", False)),
                        "label": label_text,
                        "w_mm": float(meta.get("w_mm", 0.0)),
                        "h_mm": float(meta.get("h_mm", 0.0)),
                        "x_mm": float(meta.get("x_mm", 0.0)),
                        "y_mm": float(meta.get("y_mm", 0.0)),
                        "outline": str(meta.get("outline", "black")),
                        "angle": float(meta.get("angle", 0.0) or 0.0),
                        "z": int(meta.get("z", 0)),
                        # Persist text styling for barcode labels
                        "label_fill": str(meta.get("label_fill", "black")),
                        "label_font_size": int(round(float(meta.get("label_font_size", 10)))),
                        "label_font_family": str(meta.get("label_font_family", "Myriad Pro")),
                        "owner_major": str(meta.get("owner_major", "")),
                        # Export file assignment
                        "export_file": str(meta.get("export_file", "File 1")),
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize barcode item {cid}: {e}")
                    continue
        return items

    def _normalize_cmyk(self, value) -> str:
        """Normalize a CMYK-like value into a 4-part comma-separated numeric string.

        Rules:
        - Accept strings like "C,M,Y,K" or numeric values; tolerate spaces.
        - Non-numeric parts are treated as 0.
        - If fewer than 4 parts, pad with 0s; if more than 4, truncate to first 4.
        - Returns a string like "C,M,Y,K" where each is an integer if possible or a float.
        """
        try:
            s = str(value or "")
        except Exception:
            return "0,0,0,100"
        parts = [p.strip() for p in s.split(",") if p is not None]
        nums: list[str] = []
        for p in parts:
            if p == "":
                nums.append("0")
                continue
            try:
                f = float(p)
                if f.is_integer():
                    nums.append(str(int(f)))
                else:
                    # keep minimal float representation
                    nums.append(str(f))
            except Exception:
                # non-numeric -> 0
                nums.append("0")
        # pad/truncate to exactly 4
        if len(nums) < 4:
            nums += ["0"] * (4 - len(nums))
        elif len(nums) > 4:
            nums = nums[:4]
        return ",".join(nums)

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
                        # Restore export file assignment
                        self._items[rid]["export_file"] = str(it.get("export_file", "File 1"))
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
                        # Restore export file assignment
                        meta["export_file"] = str(it.get("export_file", "File 1"))
                        # Restore custom images dict and selected custom image
                        custom_imgs_from_json = dict(it.get("custom_images", {}))
                        meta["custom_images"] = custom_imgs_from_json
                        meta["custom_image"] = str(it.get("custom_image", "") or "")
                        logger.info(f"Restored image: custom_images={custom_imgs_from_json}, custom_image={meta['custom_image']}")
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
                                # Restore export file assignment
                                self._items[tid]["export_file"] = str(it.get("export_file", "File 1"))
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
                                # Restore export file assignment
                                self._items[rid]["export_file"] = str(it.get("export_file", "File 1"))
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
            elif t == "barcode":
                # Restore barcode as a rectangle with saved styling and label
                outline = str(it.get("outline", "black"))
                text_fill = str(it.get("label_fill", "black"))
                label_text = str(it.get("label", "Barcode"))
                rid = self._create_rect_at_mm(
                    label_text,
                    float(it.get("w_mm", 80.0)),
                    float(it.get("h_mm", 30.0)),
                    float(it.get("x_mm", 0.0)),
                    float(it.get("y_mm", 0.0)),
                    outline=outline,
                    text_fill=text_fill,
                    angle=float(it.get("angle", 0.0) or 0.0),
                )
                try:
                    if rid in self._items:
                        # Change type from rect to barcode
                        self._items[rid]["type"] = "barcode"
                        self._items[rid]["amazon_label"] = it.get("amazon_label", "")
                        # Restore flags if present
                        self._items[rid]["is_options"] = self._as_bool(it.get("is_options", False))
                        self._items[rid]["is_static"] = self._as_bool(it.get("is_static", False))
                        # Restore export file assignment
                        self._items[rid]["export_file"] = str(it.get("export_file", "File 1"))
                        z_val = it.get("z")
                        if z_val is not None:
                            self._items[rid]["z"] = int(z_val)
                        # Remove rotated overlay for barcode (not used) and ensure base rect is visible
                        try:
                            old_rot = int(self._items[rid].get("rot_id", 0) or 0)
                        except Exception:
                            old_rot = 0
                        if old_rot:
                            try:
                                self.canvas.delete(old_rot)
                            except Exception:
                                pass
                            self._items[rid]["rot_id"] = None
                        # Ensure the base rect has a visible fill and outline for barcode
                        try:
                            self.canvas.itemconfig(rid, outline=outline or "black", fill="white", width=2)
                        except Exception:
                            pass
                        # Keep barcode label in black by default unless overridden by saved data
                        self._items[rid]["label_fill"] = text_fill or "black"
                        # Apply restored label styling if present
                        try:
                            if "label_fill" in it:
                                self._items[rid]["label_fill"] = str(it.get("label_fill"))
                            if "label_font_size" in it:
                                self._items[rid]["label_font_size"] = int(round(float(it.get("label_font_size", 10))))
                            if "label_font_family" in it:
                                self._items[rid]["label_font_family"] = str(it.get("label_font_family", "Myriad Pro"))
                            self._update_rect_label_image(rid)
                        except Exception:
                            logger.exception("Failed to apply restored barcode label styling")
                except Exception as e:
                    logger.exception(f"Failed to restore barcode from JSON: {e}")

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

        sku_val = data.get("ASINs") or []
        sku_name_val = str(data.get("SkuName") or prod)
        if sku_val:
            if sku_val:
                self.sku_var.set(sku_val[0][0])
            self.sku_name_var.set(sku_name_val)
            state.asins = sku_val
            # Restore per-ASIN mirror flags from saved ASINs (if present as third element)
            try:
                for entry in sku_val:
                    try:
                        if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                            a = str(entry[0])
                            m = False
                            if len(entry) >= 3:
                                try:
                                    m = bool(entry[2])
                                except Exception:
                                    m = False
                            try:
                                # ensure mapping exists
                                if not hasattr(self, "_asin_mirror"):
                                    self._asin_mirror = {}
                                self._asin_mirror[a] = m
                            except Exception:
                                pass
                    except Exception:
                        continue
            except Exception:
                pass
            state.sku_name = sku_name_val

        scene = data.get("Scene") or {}
        jig = scene.get("jig") or {}
        step = scene.get("step") or {}
        origin = scene.get("origin") or {}
        slot_size = scene.get("slot_size") or {}
        
        # Load export files list if present
        try:
            export_files_saved = scene.get("export_files") or ["File 1"]
            if export_files_saved and isinstance(export_files_saved, list):
                self._export_files_list = list(export_files_saved)
                if self._export_files_list:
                    self.export_file_var.set(self._export_files_list[0])
                # Refresh UI
                if hasattr(self, "_export_file_combo"):
                    self._export_file_combo.configure(values=self._export_files_list)
                if hasattr(self, "_export_file_selector_left"):
                    self._export_file_selector_left.configure(values=self._export_files_list)
                if hasattr(self, "_file_selector_left"):
                    self._file_selector_left.configure(values=self._export_files_list)
        except Exception:
            logger.exception("Failed to restore export files list")

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
        # Restore jig/object CMYK values if present.
        # Do NOT auto-normalize saved values. If the saved value doesn't contain exactly 4 comma-separated parts,
        # mark the field invalid and leave the current UI value untouched so the user must correct it.
        try:
            if hasattr(self, "jig_cmyk") and "cmyk" in jig:
                saved = jig.get("cmyk")
                if saved is None:
                    _set_str(self.jig_cmyk, self.jig_cmyk.get())
                    self._jig_cmyk_invalid = False
                else:
                    parts = str(saved).split(",")
                    if len(parts) != 4:
                        # don't change UI, but mark invalid so proceed will prompt the user
                        self._jig_cmyk_invalid = True
                    else:
                        # Accept as-is but trim spaces
                        _set_str(self.jig_cmyk, ",".join([p.strip() for p in parts]))
                        self._jig_cmyk_invalid = False
            if hasattr(self, "obj_cmyk") and "object_cmyk" in scene:
                saved2 = scene.get("object_cmyk")
                if saved2 is None:
                    _set_str(self.obj_cmyk, self.obj_cmyk.get())
                    self._obj_cmyk_invalid = False
                else:
                    parts2 = str(saved2).split(",")
                    if len(parts2) != 4:
                        self._obj_cmyk_invalid = True
                    else:
                        _set_str(self.obj_cmyk, ",".join([p.strip() for p in parts2]))
                        self._obj_cmyk_invalid = False
        except Exception:
            logger.exception("Failed to restore CMYK values from scene")
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

        # Check if we have per-ASIN objects (new format) or legacy format
        asin_objects_data = data.get("ASINObjects", {})
        use_per_asin_format = bool(asin_objects_data)
        
        # If we have per-ASIN objects, load them into _asin_objects
        if use_per_asin_format:
            import copy
            logger.debug(f"[RESTORE] Loading per-ASIN objects for {len(asin_objects_data)} ASINs")
            for asin in self._asin_list:
                if asin in asin_objects_data:
                    asin_data = asin_objects_data[asin]
                    
                    # Data is always in grouped format (with slots)
                    frontside = asin_data.get("Frontside", [])
                    backside = asin_data.get("Backside", [])
                    
                    # Store grouped format
                    self._asin_objects[asin] = {
                        "front_grouped": copy.deepcopy(frontside),
                        "back_grouped": copy.deepcopy(backside),
                        "front_barcode": copy.deepcopy(asin_data.get("FrontsideBarcode")) if "FrontsideBarcode" in asin_data else None,
                        "back_barcode": copy.deepcopy(asin_data.get("BacksideBarcode")) if "BacksideBarcode" in asin_data else None,
                    }
                    logger.debug(f"[RESTORE] Loaded '{asin}' grouped format with {len(frontside)} front groups, {len(backside)} back groups")
            
            # Use first ASIN's data for building slots and initial display
            current_asin = self._asin_list[0] if self._asin_list else None
            if current_asin and current_asin in self._asin_objects:
                asin_obj = self._asin_objects[current_asin]
                # Always use grouped format
                front = asin_obj.get("front_grouped", [])
                back = asin_obj.get("back_grouped", [])
            else:
                front = []
                back = []
        else:
            # Legacy format: single Frontside/Backside for all ASINs
            # Initialize all ASINs with the same objects
            front = data.get("Frontside") or {}
            back = data.get("Backside") or {}
            
            # Copy to all ASINs in legacy mode
            import copy
            for asin in self._asin_list:
                self._asin_objects[asin] = {
                    "front_grouped": copy.deepcopy(front),
                    "back_grouped": copy.deepcopy(back),
                    "front_barcode": copy.deepcopy(data.get("FrontsideBarcode")) if "FrontsideBarcode" in data else None,
                    "back_barcode": copy.deepcopy(data.get("BacksideBarcode")) if "BacksideBarcode" in data else None,
                }

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

        # Always use grouped format for extraction
        front_slots, front_items = _collect_slots_and_items(front)
        back_slots, back_items = _collect_slots_and_items(back)
        logger.debug(f"[RESTORE] Extracted front={len(front_items)}objs ({len(front_slots)}slots), back={len(back_items)}objs ({len(back_slots)}slots)")

        # Barcode is stored per side outside of slots; append if present
        if use_per_asin_format:
            # Get barcodes from current ASIN's data
            current_asin = self._asin_list[0] if self._asin_list else None
            if current_asin and current_asin in self._asin_objects:
                try:
                    fb = self._asin_objects[current_asin].get("front_barcode")
                    if isinstance(fb, dict) and str(fb.get("type", "")) == "barcode":
                        front_items.append(dict(fb))
                except Exception:
                    logger.exception("Failed to restore FrontsideBarcode from per-ASIN data")
                try:
                    bb = self._asin_objects[current_asin].get("back_barcode")
                    if isinstance(bb, dict) and str(bb.get("type", "")) == "barcode":
                        back_items.append(dict(bb))
                except Exception:
                    logger.exception("Failed to restore BacksideBarcode from per-ASIN data")
        else:
            # Legacy: get barcodes from root level
            try:
                fb = data.get("FrontsideBarcode")
                if isinstance(fb, dict) and str(fb.get("type", "")) == "barcode":
                    front_items.append(dict(fb))
            except Exception:
                logger.exception("Failed to restore FrontsideBarcode from JSON")
            try:
                bb = data.get("BacksideBarcode")
                if isinstance(bb, dict) and str(bb.get("type", "")) == "barcode":
                    back_items.append(dict(bb))
            except Exception:
                logger.exception("Failed to restore BacksideBarcode from JSON")
        
        # Convert grouped format back to flat items for _asin_objects storage
        if use_per_asin_format:
            for asin in self._asin_list:
                if asin in self._asin_objects:
                    asin_obj = self._asin_objects[asin]
                    
                    # Convert from grouped format to flat
                    def _flatten_grouped(grouped_side):
                        items = []
                        if isinstance(grouped_side, list):
                            for section in grouped_side:
                                sec_slots = list((section or {}).get("slots") or [])
                                for s in sec_slots:
                                    for obj in list(s.get("objects") or []):
                                        items.append(dict(obj))
                        return items
                    
                    front_flat = _flatten_grouped(asin_obj.get("front_grouped", []))
                    back_flat = _flatten_grouped(asin_obj.get("back_grouped", []))
                    
                    # Add barcodes
                    if asin_obj.get("front_barcode"):
                        front_flat.append(dict(asin_obj["front_barcode"]))
                    if asin_obj.get("back_barcode"):
                        back_flat.append(dict(asin_obj["back_barcode"]))
                    
                    # Update storage with flat format (for internal use)
                    self._asin_objects[asin]["front"] = front_flat
                    self._asin_objects[asin]["back"] = back_flat
                    logger.debug(f"[RESTORE] Converted '{asin}' from grouped to flat: front={len(front_flat)}objs, back={len(back_flat)}objs")

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
        
        # Save current scene under current side (exclude slots) - both to scene_store and per-ASIN
        data_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
        self._scene_store[self._current_side] = data_no_slots
        
        # Also save to current ASIN's storage
        self._save_current_asin_objects()
        
        # Switch side based on checkbox
        self._current_side = "back" if self.backside.get() else "front"
        
        # Clear and restore the target scene; keep slots persistent across sides
        self._clear_scene(keep_slots=True)
        
        # Restore from current ASIN's storage for the new side
        current_asin = state.asins[0][0] if state.asins else None
        if current_asin and current_asin in self._asin_objects:
            data = self._asin_objects[current_asin].get(self._current_side, [])
        else:
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
