import os
import re
import struct
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import threading
import math

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont

from PIL import ImageDraw

from src.core import Screen, vcmd_float, COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL, MM_TO_PX, IMAGES_PATH, TEMP_FOLDER
from src.utils import *
from src.core.state import ALL_PRODUCTS, FONTS_PATH, PRODUCTS_PATH, state
from src.canvas import CanvasObject, CanvasSelection
from src.canvas.jig import JigController
from src.canvas.slots import SlotManager
from src.canvas.images import ImageManager
from src.canvas.export import PdfExporter
from .results_download import NStickerResultsDownloadScreen

logger = logging.getLogger(__name__)

# Optional PIL (Pillow) import for high-quality image scaling
try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:  # pragma: no cover - PIL might not be available in some envs
    Image = None  # type: ignore
    ImageTk = None  # type: ignore

 

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

        # Top row: Write SKU (primary SKU field)
        header_row_top = ttk.Frame(self, style="Screen.TFrame")
        header_row_top.pack(padx=0, pady=(35, 8))
        tk.Label(header_row_top, text=" Write SKU ", bg="#737373", fg=COLOR_TEXT,
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
        tk.Label(header_row_bottom, text=" Write name for SKU ", bg="#737373", fg=COLOR_TEXT,
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

        bar = tk.Frame(self, bg="black")
        bar.pack(fill="x", padx=10, pady=(6, 10))

        # 1) Import Image pill button (styled like "Yes")
        pill_font_obj = tkfont.Font(font=("Myriad Pro", 16))
        pad_x = 12
        pad_y = 12
        # Calculate width for "Import" (longer word)
        import_width = pill_font_obj.measure("Import")
        pill_w = int(import_width + pad_x * 2)
        pill_h = int(pill_font_obj.metrics("linespace") * 2 + pad_y * 2)
        self.btn_import_img = tk.Canvas(bar, width=pill_w, height=pill_h, bg="black",
                                        highlightthickness=0, bd=0, cursor="hand2")
        # Draw rounded pill
        r = max(6, int(round(pill_h * 0.22)))
        x1, y1, x2, y2 = 0, 0, pill_w, pill_h
        _pill_shapes = []
        _pill_shapes.append(self.btn_import_img.create_rectangle(x1 + r, y1, x2 - r, y2, fill=COLOR_PILL, outline=""))
        _pill_shapes.append(self.btn_import_img.create_rectangle(x1, y1 + r, x2, y2 - r, fill=COLOR_PILL, outline=""))
        _pill_shapes.append(self.btn_import_img.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=COLOR_PILL, outline=""))
        _pill_shapes.append(self.btn_import_img.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=COLOR_PILL, outline=""))
        _pill_shapes.append(self.btn_import_img.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill=COLOR_PILL, outline=""))
        _pill_shapes.append(self.btn_import_img.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill=COLOR_PILL, outline=""))
        # Two-line text
        tx = pill_w // 2
        ty1 = pill_h // 2 - pill_font_obj.metrics("linespace") // 2
        ty2 = pill_h // 2 + pill_font_obj.metrics("linespace") // 2
        _pill_text_ids = [
            self.btn_import_img.create_text(tx, ty1, text="Import", font=("Myriad Pro", 16), fill=COLOR_TEXT, anchor="center"),
            self.btn_import_img.create_text(tx, ty2, text="Image", font=("Myriad Pro", 16), fill=COLOR_TEXT, anchor="center")
        ]

        def _pill_press(_e, c=self.btn_import_img, shapes=_pill_shapes, tids=_pill_text_ids):
            for sid in shapes:
                c.itemconfigure(sid, fill="#3f3f3f")
            for tid in tids:
                c.move(tid, 1, 1)
            c._pressed = True

        def _pill_release(e, c=self.btn_import_img, shapes=_pill_shapes, tids=_pill_text_ids):
            for sid in shapes:
                c.itemconfigure(sid, fill=COLOR_PILL)
            for tid in tids:
                c.move(tid, -1, -1)
            try:
                w = c.winfo_width(); h = c.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(c, "_pressed", False) and inside:
                c.after(10, self._import_image)
            c._pressed = False

        self.btn_import_img.bind("<ButtonPress-1>", _pill_press)
        self.btn_import_img.bind("<ButtonRelease-1>", _pill_release)
        self.btn_import_img.pack(side="left", padx=8, pady=8)

        # 2) Jig size label and fields
        tk.Label(bar, text="Jig size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(16, 6))
        self.jig_x = tk.StringVar(value=state.pkg_x or "296")
        self.jig_y = tk.StringVar(value=state.pkg_y or "415")
        jig_col = tk.Frame(bar, bg="black")
        jig_col.pack(side="left", padx=8, pady=8)
        # Jig X row
        _jxbox = tk.Frame(jig_col, bg="#6f6f6f")
        _jxbox.pack(side="top", pady=2)
        tk.Label(_jxbox, text="Width: ", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_jxbox, textvariable=self.jig_x, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_jxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Jig Y row
        _jybox = tk.Frame(jig_col, bg="#6f6f6f")
        _jybox.pack(side="top", pady=2)
        tk.Label(_jybox, text="Height:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_jybox, textvariable=self.jig_y, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_jybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # live redraw and slot re-create when jig size changes
        self.jig_x.trace_add("write", self._on_jig_change)
        self.jig_y.trace_add("write", self._on_jig_change)

        # 4) White vertical separator
        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)

        # Slot size label and fields
        tk.Label(bar, text="Slot size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(0, 6))
        self.slot_w = tk.StringVar(value="48")
        self.slot_h = tk.StringVar(value="48")
        slot_col = tk.Frame(bar, bg="black")
        slot_col.pack(side="left", padx=8, pady=8)
        # Slot Width row
        _swbox = tk.Frame(slot_col, bg="#6f6f6f")
        _swbox.pack(side="top", pady=2)
        tk.Label(_swbox, text="Width: ", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_swbox, textvariable=self.slot_w, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_swbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Slot Height row
        _shbox = tk.Frame(slot_col, bg="#6f6f6f")
        _shbox.pack(side="top", pady=2)
        tk.Label(_shbox, text="Height:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_shbox, textvariable=self.slot_h, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_shbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # White vertical separator
        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)

        # Origin Pos label and fields
        tk.Label(bar, text="Origin Pos:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(0, 6))
        self.origin_x = tk.StringVar(value="0")
        self.origin_y = tk.StringVar(value="0")
        origin_col = tk.Frame(bar, bg="black")
        origin_col.pack(side="left", padx=8, pady=8)
        # Origin X row
        _oxbox = tk.Frame(origin_col, bg="#6f6f6f")
        _oxbox.pack(side="top", pady=2)
        tk.Label(_oxbox, text="X:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_oxbox, textvariable=self.origin_x, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_oxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Origin Y row
        _oybox = tk.Frame(origin_col, bg="#6f6f6f")
        _oybox.pack(side="top", pady=2)
        tk.Label(_oybox, text="Y:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_oybox, textvariable=self.origin_y, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_oybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)
        # Step Size label and fields
        tk.Label(bar, text="Step Size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(0, 6))
        self.step_x = tk.StringVar(value=self.slot_w.get())
        self.step_y = tk.StringVar(value=self.slot_h.get())
        step_col = tk.Frame(bar, bg="black")
        step_col.pack(side="left", padx=8, pady=8)
        # Step X row
        _sxbox = tk.Frame(step_col, bg="#6f6f6f")
        _sxbox.pack(side="top", pady=2)
        tk.Label(_sxbox, text="X:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_sxbox, textvariable=self.step_x, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_sxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Step Y row
        _sybox = tk.Frame(step_col, bg="#6f6f6f")
        _sybox.pack(side="top", pady=2)
        tk.Label(_sybox, text="Y:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_sybox, textvariable=self.step_y, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_sybox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # White vertical separator
        tk.Frame(bar, bg="white", width=2).pack(side="left", fill="y", padx=12, pady=6)

        # 5) Tools next to the separator
        tools = tk.Frame(bar, bg="black")
        tools.pack(side="left", pady=(8, 0))

        # Load tool icons (keep references on self to avoid GC)
        self._img_cursor = None
        self._img_stick = None
        try:
            self._img_cursor = tk.PhotoImage(file=str(IMAGES_PATH / "cursor.png"))
        except Exception:
            self._img_cursor = None
        try:
            self._img_stick = tk.PhotoImage(file=str(IMAGES_PATH / "stick.png"))
        except Exception:
            self._img_stick = None

        # Tool tiles like in the screenshot
        # self._create_tool_tile(
        #     tools,
        #     icon_image=self._img_cursor,
        #     icon_text=None,
        #     label_text="Select tool",
        #     command=lambda: None,
        # )
        self._create_tool_tile(
            tools,
            icon_image=self._img_stick,
            icon_text=None,
            label_text="AI arrange",
            command=self._ai_arrange,
        )
        # Slots are auto-created from inputs; no manual button needed
        self._create_tool_tile(
            tools,
            icon_image=None,
            icon_text="T",
            label_text="Text",
            command=self._drop_text,
        )
        # Help/shortcuts on the right end of the first line
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
        self.sel_w = tk.StringVar(value=state.pkg_x or "296")
        self.sel_h = tk.StringVar(value=state.pkg_y or "415")
        _wb = self._chip(row2, "Width:", self.sel_w, width=8)
        tk.Label(_wb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        _hb = self._chip(row2, "Height:", self.sel_h, width=8)
        tk.Label(_hb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Angle control (degrees)
        self.sel_angle = tk.StringVar(value="0")
        _ab = self._chip(row2, "Angle:", self.sel_angle, width=6)
        tk.Label(_ab, text="deg", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

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

        board = tk.Frame(self, bg="black")
        board.pack(expand=True, fill="both", padx=10, pady=10)
        # canvas without visible scrollbars
        self.canvas = tk.Canvas(board, bg="#5a5a5a", highlightthickness=0, takefocus=1)
        self.canvas.pack(expand=True, fill="both")
        # Managers and method delegations (must be set before bindings)
        self.jig = JigController(self)
        self.slots = SlotManager(self)
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
        self._render_scene_to_pdf = self.exporter.render_scene_to_pdf
        # Now bind using delegated methods
        self.canvas.bind("<Configure>", self._redraw_jig)
        self.canvas.bind("<Button-1>", self.selection.on_click)
        self.canvas.bind("<Button-1>", lambda _e: self.canvas.focus_set(), add="+")
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
        # initial jig draw
        self.after(0, self._redraw_jig)
        # initialize jig size from Size fields when no saved size
        self._did_autosize = False
        self.after(0, self._ensure_initial_jig_size)
        # Auto-recreate slots when inputs change (always)
        self.slot_w.trace_add("write", lambda *_: self._maybe_recreate_slots())
        self.slot_h.trace_add("write", lambda *_: self._maybe_recreate_slots())
        self.origin_x.trace_add("write", lambda *_: self._maybe_recreate_slots())
        self.origin_y.trace_add("write", lambda *_: self._maybe_recreate_slots())
        self.step_x.trace_add("write", lambda *_: self._maybe_recreate_slots())
        self.step_y.trace_add("write", lambda *_: self._maybe_recreate_slots())
        # Initial auto placement
        self.after(0, lambda: self._place_slots(silent=True))

        self._items: dict[int, CanvasObject] = {}   # canvas_id -> CanvasObject
        # Per-side scene storage
        self._scene_store: dict[str, list[dict]] = {"front": [], "back": []}
        self._current_side: str = "front"

        # Show popup on right-click only when an object is under cursor
        self.canvas.bind("<Button-3>", self.selection.maybe_show_context_menu)

        # Key bindings moved to canvas-level to require focus

        # Bottom buttons styled like font_info
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

        # Proceed (styled like font_info)
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

        # If coming from "Update existing product", restore saved scene
        self.after(0, self._maybe_load_saved_product)

    # UI helpers
    def _snap_mm(self, value: float) -> int:
        """Snap a millimeter value to the nearest integer mm."""
        try:
            return int(round(float(value)))
        except Exception:
            return 0

    
    def _raise_all_labels(self):
        # Ensure text squares (rect + label) are above normal items
        self.canvas.tag_raise("text_item")
        self.canvas.tag_raise("label")

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
        # Recreate slots based on current parameters
        self._place_slots(silent=True)
        self._renumber_slots()

    def _maybe_recreate_slots(self):
        self._place_slots(silent=True)

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
        # place at the center of current viewport (like text)
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        cx = self.canvas.canvasx(cw // 2)
        cy = self.canvas.canvasy(ch // 2)
        # snap width/height to integer millimeters
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
        txt = self.canvas.create_text(cx, cy, text=label, fill=text_fill, font=("Myriad Pro", self._scaled_pt(10)), tags=("label",))
        # Persist position in mm relative to jig for stability on jig resize
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        if x_mm is None:
            x_mm = (cx - scaled_w / 2 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
        if y_mm is None:
            y_mm = (cy - scaled_h / 2 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
        # snap to integer mm and align rectangle to snapped grid
        sx_mm = self._snap_mm(x_mm)
        sy_mm = self._snap_mm(y_mm)
        new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
        new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
        self.canvas.coords(rect, new_left, new_top, new_left + scaled_w, new_top + scaled_h)
        self.canvas.coords(txt, new_left + scaled_w / 2, new_top + scaled_h / 2)
        
        # compute next z to keep newer items above older ones
        max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        self._items[rect] = CanvasObject(
            type="rect",
            w_mm=float(qw_mm),
            h_mm=float(qh_mm),
            x_mm=float(sx_mm),
            y_mm=float(sy_mm),
            label_id=txt,
            outline=outline,
            canvas_id=rect,
            z=int(max_z + 1),
        )
        # Create initial overlay polygon to visualize rotation/selection consistently
        try:
            self._update_rect_overlay(rect, self._items[rect], new_left, new_top, scaled_w, scaled_h)
        except Exception as e:
            logger.exception(f"Failed to create/update rect overlay: {e}")
        self.selection.select(rect)
        self._update_scrollregion()
        self._raise_all_labels()
        self.selection._reorder_by_z()

    def _drop_text(self):
        # Create a square rectangle with a text label inside, so it behaves like images
        default_w = 40.0
        default_h = 40.0
        # Text rectangles use green outline
        self.create_placeholder("Text", default_w, default_h, text_fill="#17a24b", outline="#17a24b")

    def _ai_arrange(self):
        # Arrange non-slot items into existing slots.
        # Order for both slots and items: right-to-left within a row, bottom-to-top across rows
        # so the first item goes to the lower-right slot, then leftwards, then rows upwards.

        # Collect and order slots by current canvas position
        slot_entries: List[Tuple[float, float, int, CanvasObject]] = []  # (left_px, top_px, slot_cid, slot_meta)
        for scid, smeta in self._items.items():
            if smeta.get("type") != "slot":
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

        # Collect placeable items (rect or image), ordered bottom->top, right->left
        item_entries: List[Tuple[float, float, int, CanvasObject]] = []  # (left_px, top_px, cid, meta)
        for cid, meta in self._items.items():
            if meta.get("type") not in ("rect", "image"):
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
                    jx, jy = 296.0, 415.0
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
                meta.x_mm = float(self._snap_mm(left_mm))
                meta.y_mm = float(self._snap_mm(top_mm))
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
                    jx, jy = 296.0, 415.0
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
                self._raise_all_labels()
                # Persist mm top-left
                meta.x_mm = float(self._snap_mm(left_mm))
                meta.y_mm = float(self._snap_mm(top_mm))

        self._redraw_jig(center=False)
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
            jx, jy = 296.0, 415.0
        self.jig_x.set(str(int(jx)))
        self.jig_y.set(str(int(jy)))
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
        try:
            img_count = sum(1 for _cid, meta in self._items.items() if meta.get("type") in ["image", "rect"])
        except Exception:
            img_count = 0
        state.nonsticker_image_count = int(img_count)
        # Snapshot current side (exclude slots) so both sides are up-to-date
        current_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
        self._scene_store[self._current_side] = current_no_slots
        # Collect slots from the current canvas (slots are shared across sides)
        slots_only = [it for it in self._serialize_scene() if it.get("type") == "slot"]
        # Prepare background job to render PDFs and write JSON without blocking UI
        p_jig = os.path.join(TEMP_FOLDER, "Jig_file.pdf")
        p_front = os.path.join(TEMP_FOLDER, "Test_file.pdf")
        p_back = os.path.join(TEMP_FOLDER, "Test_file_backside.pdf")
        try:
            jx = float(self.jig_x.get() or 0.0)
            jy = float(self.jig_y.get() or 0.0)
        except Exception:
            jx, jy = 296.0, 415.0
        front_items = list(slots_only) + list(self._scene_store.get("front") or [])
        back_items = list(slots_only) + list(self._scene_store.get("back") or [])

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

            def _compose_side(items_for_side: list[dict]) -> dict:
                slot_descs: list[dict] = []
                for it in items_for_side:
                    if str(it.get("type", "")) == "slot":
                        try:
                            key = (
                                str(it.get("label", "")),
                                float(it.get("x_mm", 0.0)),
                                float(it.get("y_mm", 0.0)),
                                float(it.get("w_mm", 0.0)),
                                float(it.get("h_mm", 0.0)),
                            )
                            slot_entry = {
                                "label": str(it.get("label", "")),
                                "x_mm": float(it.get("x_mm", 0.0)),
                                "y_mm": float(it.get("y_mm", 0.0)),
                                "w_mm": float(it.get("w_mm", 0.0)),
                                "h_mm": float(it.get("h_mm", 0.0)),
                                "z": int(slot_z_map.get(key, 0)),
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
                        return (sx <= cx <= sx + sw) and (sy <= cy <= sy + sh)
                    except Exception as e:
                        logger.exception(f"Failed to check if image is centered in slot: {e}")
                        return False

                for it in items_for_side:
                    if str(it.get("type", "")) != "image":
                        continue
                    try:
                        key = (
                            str(it.get("path", "")),
                            float(it.get("x_mm", 0.0)),
                            float(it.get("y_mm", 0.0)),
                            float(it.get("w_mm", 0.0)),
                            float(it.get("h_mm", 0.0)),
                        )
                        obj = {
                            "type": "image",
                            "path": str(it.get("path", "")),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "w_mm": float(it.get("w_mm", 0.0)),
                            "h_mm": float(it.get("h_mm", 0.0)),
                            "angle": float(it.get("angle", 0.0) or 0.0),
                            "z": int(image_z_map.get(key, 0)),
                        }
                    except Exception as e:
                        logger.exception(f"Failed to process image for slot: {e}")
                        continue
                    for sl in slot_descs:
                        if _center_in_slot(obj, sl):
                            sl["objects"].append(obj)
                            break

                for it in items_for_side:
                    if str(it.get("type", "")) != "text":
                        continue
                    try:
                        key = (
                            str(it.get("text", "")),
                            float(it.get("x_mm", 0.0)),
                            float(it.get("y_mm", 0.0)),
                            str(it.get("fill", "white")),
                        )
                        obj = {
                            "type": "text",
                            "text": str(it.get("text", "")),
                            "fill": str(it.get("fill", "white")),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "z": int(text_z_map.get(key, 0)),
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
                            inside = (sx <= cx <= sx + sw) and (sy <= cy <= sy + sh)
                        except Exception as e:
                            logger.exception(f"Failed to check if text is inside slot: {e}")
                            inside = False
                        if inside:
                            try:
                                sl["objects"].append(obj)
                            except Exception as e:
                                logger.exception(f"Failed to append object to slot: {e}")
                            break

                for it in items_for_side:
                    if str(it.get("type", "")) != "rect" or str(it.get("outline", "")) != "#17a24b":
                        continue
                    try:
                        key = (
                            str(it.get("label", "")),
                            float(it.get("x_mm", 0.0)),
                            float(it.get("y_mm", 0.0)),
                            float(it.get("w_mm", 0.0)),
                            float(it.get("h_mm", 0.0)),
                        )
                        obj = {
                            "type": "text",
                            "label": str(it.get("label", "")),
                            "x_mm": float(it.get("x_mm", 0.0)),
                            "y_mm": float(it.get("y_mm", 0.0)),
                            "w_mm": float(it.get("w_mm", 0.0)),
                            "h_mm": float(it.get("h_mm", 0.0)),
                            "angle": float(it.get("angle", 0.0) or 0.0),
                            "z": int(text_rect_z_map.get(key, 0)),
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
                            inside = (sx <= obj["x_mm"] <= sx + sw) and (sy <= obj["y_mm"] <= sy + sh)
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
                "step": {"x_mm": float(step_x), "y_mm": float(step_y)},
                "origin": {"x_mm": float(origin_x), "y_mm": float(origin_y)},
                "slot_size": {"width_mm": float(slot_w), "height_mm": float(slot_h)},
                "slot_count": int(slot_count),
                "objects_count": {
                    "images": int(images_cnt_front + images_cnt_back),
                    "text": int(text_cnt_front + text_cnt_back),
                },
            }
            combined = {
                "Sku": state.sku or "",
                "SkuName": state.sku_name or "",
                "IsSticker": False,
                "Scene": scene_top,
                "Frontside": _compose_side(front_items),
                "Backside": _compose_side(back_items),
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
                logger.debug(f"Rendering jig PDF...")
                state.processing_message = "Rendering jig PDF..."
                self._render_scene_to_pdf(p_jig, front_items, jx, jy, only_jig=True, dpi=1200)
                logger.debug(f"Rendering front PDF...")
                state.processing_message = "Rendering front PDF..."
                self._render_scene_to_pdf(p_front, front_items, jx, jy, dpi=1200)
                logger.debug(f"Rendering back PDF...")
                state.processing_message = "Rendering back PDF..."
                self._render_scene_to_pdf(p_back, back_items, jx, jy, dpi=1200)
                # Write JSON
                try:
                    import json as _json
                    logger.debug(f"Writing JSON file...")
                    state.processing_message = "Writing JSON file..."
                    with open(json_path, "w", encoding="utf-8") as _f:
                        _json.dump(combined, _f, ensure_ascii=False, indent=2)
                    logger.debug(f"Processing completed")
                    
                except Exception as e:
                    state.is_failed = True
                    state.error_message = str(e)
                    logger.exception(f"Failed to write JSON file: {e}")

                state.processing_message = ""
                # Add new product to list if not already present
                for p in ALL_PRODUCTS:
                    if p == state.sku_name:
                        break
                else:
                    ALL_PRODUCTS.append(state.sku_name)

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

        threading.Thread(target=_worker, daemon=True).start()

        # Navigate immediately; results screen will poll state and update UI
        self.app.show_screen(NStickerResultsDownloadScreen)

    # ---- Front/Back scene state management ----
    def _clear_scene(self, keep_slots: bool = False):
        try:
            for cid, meta in list(self._items.items()):
                if keep_slots and meta.get("type") == "slot":
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

    def _create_rect_at_mm(self, label: str, w_mm: float, h_mm: float, x_mm: float, y_mm: float, outline: str = "#d0d0d0", text_fill: str = "white", angle: float = 0.0):
        x0, y0, x1, y1 = self._jig_inner_rect_px()
        ox = self._item_outline_half_px()
        oy = self._item_outline_half_px()
        # snap all inputs to integer mm
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
        txt = self.canvas.create_text(new_left + w / 2, new_top + h / 2, text=label, fill=text_fill, font=("Myriad Pro", self._scaled_pt(10)), tags=("label",))

        # keep provided mm unless clamped
        if new_left != left or new_top != top:
            x_mm_i = self._snap_mm((new_left - (x0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6)))
            y_mm_i = self._snap_mm((new_top - (y0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6)))
        # next z
        max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        self._items[rect] = CanvasObject(
            type="rect",
            w_mm=float(w_mm_i),
            h_mm=float(h_mm_i),
            x_mm=float(x_mm_i),
            y_mm=float(y_mm_i),
            label_id=txt,
            outline=outline,
            canvas_id=rect,
            z=int(max_z + 1),
            angle=float(ang),
        )
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
        tid = self.canvas.create_text(cx, cy, text=text, fill=fill, font=("Myriad Pro", self._scaled_pt(12), "bold"), tags=("label",))
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
                    label_id = meta.get("label_id")
                    label_text = self.canvas.itemcget(label_id, "text") if label_id else ""
                    items.append({
                        "type": "rect",
                        "label": label_text,
                        "w_mm": float(meta.get("w_mm", 0.0)),
                        "h_mm": float(meta.get("h_mm", 0.0)),
                        "x_mm": float(meta.get("x_mm", 0.0)),
                        "y_mm": float(meta.get("y_mm", 0.0)),
                        "outline": str(meta.get("outline", "#d0d0d0")),
                        "angle": float(meta.get("angle", 0.0) or 0.0),
                        "z": int(meta.get("z", 0)),
                    })
                except Exception:
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
                    })
                except Exception as e:
                    logger.exception(f"Failed to serialize slot item {cid}: {e}")
                    continue
            elif t == "image":
                try:
                    items.append({
                        "type": "image",
                        "path": str(meta.get("path", "")),
                        "w_mm": float(meta.get("w_mm", 0.0)),
                        "h_mm": float(meta.get("h_mm", 0.0)),
                        "x_mm": float(meta.get("x_mm", 0.0)),
                        "y_mm": float(meta.get("y_mm", 0.0)),
                        "angle": float(meta.get("angle", 0.0) or 0.0),
                        "z": int(meta.get("z", 0)),
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
                        "text": txt,
                        "x_mm": x_mm,
                        "y_mm": y_mm,
                        "fill": fill,
                        "z": int(meta.get("z", 0)),
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
                # If restored rect is a Text rect, it may have green outline
                text_fill = "#17a24b" if outline == "#17a24b" else "white"
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
                        z_val = it.get("z")
                        if z_val is not None:
                            self._items[rid]["z"] = int(z_val)
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
                )
                try:
                    if sid in self._items:
                        z_val = it.get("z")
                        if z_val is not None:
                            self._items[sid]["z"] = int(z_val)
                except Exception as e:
                    logger.exception(f"Failed to apply slot z from JSON: {e}")
            elif t == "image":
                path = str(it.get("path", ""))
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
                            z_val = it.get("z")
                            if z_val is not None:
                                self._items[tid]["z"] = int(z_val)
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
                        text_fill="#17a24b",
                        angle=float(it.get("angle", 0.0) or 0.0),
                    )
                    try:
                        if rid in self._items:
                            z_val = it.get("z")
                            if z_val is not None:
                                self._items[rid]["z"] = int(z_val)
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
            var.set(str(int(round(float(val)))))

        _set_str(self.jig_x, jig.get("width_mm", self.jig_x.get()))
        _set_str(self.jig_y, jig.get("height_mm", self.jig_y.get()))
        _set_str(self.step_x, step.get("x_mm", self.step_x.get()))
        _set_str(self.step_y, step.get("y_mm", self.step_y.get()))
        _set_str(self.origin_x, origin.get("x_mm", self.origin_x.get()))
        _set_str(self.origin_y, origin.get("y_mm", self.origin_y.get()))
        _set_str(self.slot_w, slot_size.get("width_mm", self.slot_w.get()))
        _set_str(self.slot_h, slot_size.get("height_mm", self.slot_h.get()))

        front = data.get("Frontside") or {}
        back = data.get("Backside") or {}
        front_slots = list(front.get("slots") or [])
        back_slots = list(back.get("slots") or [])

        # Flatten objects for each side (items carry absolute mm coords)
        front_items = []
        for sl in front_slots:
            front_items.extend(list(sl.get("objects") or []))
        back_items = []
        for sl in back_slots:
            back_items.extend(list(sl.get("objects") or []))

        def _do_restore():
            # Clear anything auto-created and recreate slots from JSON for exact positions
            self._clear_scene(keep_slots=False)
            for sl in front_slots:
                sid = self._create_slot_at_mm(
                    str(sl.get("label", "")),
                    float(sl.get("w_mm", 0.0)),
                    float(sl.get("h_mm", 0.0)),
                    float(sl.get("x_mm", 0.0)),
                    float(sl.get("y_mm", 0.0)),
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