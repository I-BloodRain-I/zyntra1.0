import os
import re
import shutil
import struct
from pathlib import Path
import tempfile
from typing import Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.core import Screen, vcmd_float, COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL, MM_TO_PX, IMAGES_PATH, TEMP_FOLDER
from src.core.state import state
from src.utils import create_button, ButtonInfo, TextInfo, _rounded_rect
from src.canvas import CanvasObject, CanvasSelection
from .results_download import NStickerResultsDownloadScreen

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

        header_row = ttk.Frame(self, style="Screen.TFrame")
        header_row.pack(padx=0, pady=(25, 25))
        tk.Label(header_row, text=" Write name for SKU ", bg="#737373", fg=COLOR_TEXT,
                 font=("Myriad Pro", 22)).pack(side="left", padx=(8, 0))
        self.sku_var = tk.StringVar(value=state.sku or "Carmirror134")
        # Flat tk.Entry without focus border, with manual left padding via a black wrapper
        input_wrap = tk.Frame(header_row, bg="#000000")
        input_wrap.pack(side="left")
        tk.Frame(input_wrap, width=15, height=1, bg="#000000").pack(side="left")
        sku_entry = tk.Entry(input_wrap, textvariable=self.sku_var, width=22,
                             bg="#000000", fg="#ffffff", insertbackground="#ffffff",
                             relief="flat", bd=0, highlightthickness=0,
                             font=("Myriad Pro", 22))
        sku_entry.pack(side="left", ipady=2)

        bar = tk.Frame(self, bg="black")
        bar.pack(fill="x", padx=10, pady=(6, 10))

        # 1) Import Image pill button (styled like "Yes")
        from tkinter import font as tkfont
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
                try:
                    c.itemconfigure(sid, fill="#3f3f3f")
                except Exception:
                    pass
            for tid in tids:
                try:
                    c.move(tid, 1, 1)
                except Exception:
                    pass
            c._pressed = True

        def _pill_release(e, c=self.btn_import_img, shapes=_pill_shapes, tids=_pill_text_ids):
            for sid in shapes:
                try:
                    c.itemconfigure(sid, fill=COLOR_PILL)
                except Exception:
                    pass
            for tid in tids:
                try:
                    c.move(tid, -1, -1)
                except Exception:
                    pass
            try:
                w = c.winfo_width(); h = c.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(c, "_pressed", False) and inside:
                try:
                    c.after(10, self._import_image)
                except Exception:
                    pass
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
        self.step_w = tk.StringVar(value=self.slot_w.get())
        self.step_h = tk.StringVar(value=self.slot_h.get())
        step_col = tk.Frame(bar, bg="black")
        step_col.pack(side="left", padx=8, pady=8)
        # Step X row
        _sxbox = tk.Frame(step_col, bg="#6f6f6f")
        _sxbox.pack(side="top", pady=2)
        tk.Label(_sxbox, text="Width: ", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_sxbox, textvariable=self.step_w, width=8, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")
        tk.Label(_sxbox, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # Step Y row
        _sybox = tk.Frame(step_col, bg="#6f6f6f")
        _sybox.pack(side="top", pady=2)
        tk.Label(_sybox, text="Height:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(_sybox, textvariable=self.step_h, width=8, bg="#d9d9d9", justify="center",
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
        try:
            shortcuts.grid_columnconfigure(0, weight=0)
            shortcuts.grid_columnconfigure(1, weight=0)
        except Exception:
            pass

        tk.Label(shortcuts, text="+ / -", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=0, column=0, sticky="e", padx=(0, 0))
        tk.Label(shortcuts, text="→    Zoom in/out", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=0, column=1, sticky="w")

        tk.Label(shortcuts, text="CTRL + Middle Mouse", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=1, column=0, sticky="e", padx=(0, 0))
        tk.Label(shortcuts, text="→    Zoom in/out", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=1, column=1, sticky="w")

        tk.Label(shortcuts, text="Delete", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=2, column=0, sticky="e", padx=(0, 0))
        tk.Label(shortcuts, text="→ Remove object", fg="white", bg="black", font=("Myriad Pro", 12)).grid(row=2, column=1, sticky="w")


        row2 = tk.Frame(self, bg="black")
        row2.pack(fill="x", padx=10, pady=(0, 6))
        # Image size label at start of the line
        tk.Label(row2, text="Image size:", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(2, 8))
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

        # Selection controller (must be created before traces/bindings)
        self._zoom: float = 1.5
        self.selection = CanvasSelection(self)

        # live updates when size/position change
        self.sel_x.trace_add("write", self.selection.on_pos_change)
        self.sel_y.trace_add("write", self.selection.on_pos_change)
        self.sel_w.trace_add("write", self.selection.on_size_change)
        self.sel_h.trace_add("write", self.selection.on_size_change)

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
        self.canvas = tk.Canvas(board, bg="#5a5a5a", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<Configure>", self._redraw_jig)
        self.canvas.bind("<Button-1>", self.selection.on_click)
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
        self.step_w.trace_add("write", lambda *_: self._maybe_recreate_slots())
        self.step_h.trace_add("write", lambda *_: self._maybe_recreate_slots())
        # Initial auto placement
        self.after(0, lambda: self._place_slots(silent=True))

        self._items: dict[int, CanvasObject] = {}   # canvas_id -> CanvasObject
        # Per-side scene storage
        self._scene_store: dict[str, list[dict]] = {"front": [], "back": []}
        self._current_side: str = "front"

        # Show popup on right-click only when an object is under cursor
        self.canvas.bind("<Button-3>", self.selection.maybe_show_context_menu)

        # Key bindings for zoom in/out
        for seq in ("<KeyPress-plus>", "<KeyPress-equal>", "<KP_Add>"):
            self.app.bind(seq, lambda _e: self._zoom_step(1))

        for seq in ("<KeyPress-minus>", "<KeyPress-KP_Subtract>"):
            self.app.bind(seq, lambda _e: self._zoom_step(-1))

        # Bottom buttons styled exactly like ProductTypeScreen
        from tkinter import font as tkfont
        # Go Back
        back_text = "Go Back"
        back_font_obj = tkfont.Font(font=("Myriad Pro", 14))
        back_width_px = int(back_font_obj.measure(back_text) + 16)
        back_height_px = int(back_font_obj.metrics("linespace") + 20)
        btn_back_canvas = tk.Canvas(self, width=back_width_px, height=back_height_px, bg=COLOR_BG_DARK,
                                    highlightthickness=0, bd=0, cursor="hand2")
        bx_left = 8
        by_center = back_height_px // 2
        back_text_id = btn_back_canvas.create_text(bx_left, by_center, text=back_text, font=("Myriad Pro", 14), fill=COLOR_TEXT, anchor="w")
        def _back_press(_e, canvas=btn_back_canvas, tid=back_text_id):
            canvas.configure(bg="#3f3f3f"); canvas.move(tid, 1, 1); canvas._pressed = True
        def _back_release(e, canvas=btn_back_canvas, tid=back_text_id):
            canvas.configure(bg=COLOR_BG_DARK); canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height(); inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, self.app.go_back)
            canvas._pressed = False
        btn_back_canvas.bind("<ButtonPress-1>", _back_press)
        btn_back_canvas.bind("<ButtonRelease-1>", _back_release)
        btn_back_canvas.place(relx=0.0, rely=1.0, x=12, y=-12, anchor="sw")

        # Proceed
        next_text = "Proceed!"
        next_font_obj = tkfont.Font(font=("Myriad Pro", 14))
        next_width_px = int(next_font_obj.measure(next_text) + 16)
        next_height_px = int(next_font_obj.metrics("linespace") + 20)
        btn_next_canvas = tk.Canvas(self, width=next_width_px, height=next_height_px, bg=COLOR_BG_DARK,
                                    highlightthickness=0, bd=0, cursor="hand2")
        nx_left = 8
        ny_center = next_height_px // 2
        next_text_id = btn_next_canvas.create_text(nx_left, ny_center, text=next_text, font=("Myriad Pro", 14), fill=COLOR_TEXT, anchor="w")
        def _next_press(_e, canvas=btn_next_canvas, tid=next_text_id):
            canvas.configure(bg="#3f3f3f"); canvas.move(tid, 1, 1); canvas._pressed = True
        def _next_release(e, canvas=btn_next_canvas, tid=next_text_id):
            canvas.configure(bg=COLOR_BG_DARK); canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height(); inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, self._proceed)
            canvas._pressed = False
        btn_next_canvas.bind("<ButtonPress-1>", _next_press)
        btn_next_canvas.bind("<ButtonRelease-1>", _next_release)
        btn_next_canvas.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")

    # UI helpers
    def _snap_mm(self, value: float) -> int:
        """Snap a millimeter value to the nearest integer mm."""
        try:
            return int(round(float(value)))
        except Exception:
            return 0

    
    def _raise_all_labels(self):
        try:
            # Ensure text squares (rect + label) are above normal items
            self.canvas.tag_raise("text_item")
        except Exception:
            pass
        try:
            self.canvas.tag_raise("label")
        except Exception:
            pass
    def _scaled_pt(self, base: int) -> int:
        try:
            return max(1, int(round(base * self._zoom * 0.7)))
        except Exception:
            return max(1, int(base))

    def _update_all_text_fonts(self):
        # Scale fonts of all canvas item labels according to current zoom
        for cid, meta in list(self._items.items()):
            try:
                t = meta.get("type")
            except Exception:
                t = None
            try:
                if t in ("rect", "slot"):
                    tid = meta.get("label_id")
                    if tid:
                        self.canvas.itemconfig(tid, font=("Myriad Pro", self._scaled_pt(10)))
                elif t == "text":
                    tid = meta.get("label_id") or cid
                    self.canvas.itemconfig(tid, font=("Myriad Pro", self._scaled_pt(12), "bold"))
            except Exception:
                pass
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
            try:
                pack_info = icon_lbl.pack_info()
            except Exception:
                pass
            orig_padx = int(pack_info.get("padx", 0) if isinstance(pack_info.get("padx", 0), (int, str)) else 0)
            orig_pady = int(pack_info.get("pady", 0) if isinstance(pack_info.get("pady", 0), (int, str)) else 0)

            def _press():
                try:
                    tile.configure(bg="#bdbdbd", relief="sunken", bd=1)
                    icon_lbl.configure(bg="#bdbdbd")
                    icon_lbl.pack_configure(padx=orig_padx + 2, pady=orig_pady + 2)
                except Exception:
                    pass
                tile.after(90, _release)

            def _release():
                try:
                    tile.configure(bg=original_bg, relief="flat", bd=0)
                    icon_lbl.configure(bg=original_bg)
                    icon_lbl.pack_configure(padx=orig_padx, pady=orig_pady)
                except Exception:
                    pass
                try:
                    command()
                except Exception:
                    pass

            _press()

        tile.bind("<Button-1>", _on_click)
        icon_lbl.bind("<Button-1>", _on_click)
        lbl.bind("<Button-1>", _on_click)

        # Improve affordance
        try:
            tile.configure(cursor="hand2")
            lbl.configure(cursor="hand2")
        except Exception:
            pass

    def _import_image(self):
        # Allow selecting and importing multiple images at once
        paths = filedialog.askopenfilenames(
            title="Import Images",
            filetypes=[
                (".jpg, .png, .svg", ("*.jpg", "*.jpeg", "*.png", "*.svg")),
                ("All files", "*.*"),
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
                ext = str(Path(path).suffix).lower()
                if ext == ".svg":
                    # Keep placeholder for SVGs
                    self.create_placeholder(os.path.basename(path), size[0], size[1])
                else:
                    # Raster images: draw actual content
                    self.create_image_item(path, size[0], size[1])
            except Exception:
                # Ignore failures per-file to allow batch import to proceed
                continue
        # Refresh ordering/labels after batch import
        self._update_scrollregion()
        self._raise_all_labels()
        try:
            self.selection._reorder_by_z()
        except Exception:
            pass

    def _on_jig_change(self, *_):
        # Redraw jig and re-create slots to fill new area
        self._redraw_jig()
        # Recreate slots based on current parameters
        self._place_slots(silent=True)
        try:
            self._renumber_slots()
        except Exception:
            pass

    def _create_slot_at_mm(self, label: str, w_mm: float, h_mm: float, x_mm: float, y_mm: float):
        x0, y0, x1, y1 = self._jig_inner_rect_px()
        # For slots, allow touching jig border without the +1px inward offset
        ox = 0.0
        oy = 0.0
        # snap all inputs to integer mm
        w_mm_i = self._snap_mm(w_mm)
        h_mm_i = self._snap_mm(h_mm)
        x_mm_i = self._snap_mm(x_mm)
        y_mm_i = self._snap_mm(y_mm)
        w = w_mm_i * MM_TO_PX * self._zoom
        h = h_mm_i * MM_TO_PX * self._zoom
        # clamp top-left within inner jig
        min_left = x0 + ox
        min_top = y0 + oy
        max_left = x1 - ox - w
        max_top = y1 - oy - h
        left = x0 + x_mm_i * MM_TO_PX * self._zoom + ox
        top = y0 + y_mm_i * MM_TO_PX * self._zoom + oy
        new_left = max(min_left, min(left, max_left))
        new_top = max(min_top, min(top, max_top))
        rect = self.canvas.create_rectangle(new_left, new_top, new_left + w, new_top + h, fill="#5a5a5a", outline="#898989", width=1)
        txt = self.canvas.create_text(new_left + w / 2, new_top + h / 2, text=label, fill="#898989", font=("Myriad Pro", self._scaled_pt(10)), tags=("slot_label",))
        # keep provided mm unless clamped
        if new_left != left or new_top != top:
            x_mm_i = self._snap_mm((new_left - (x0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6)))
            y_mm_i = self._snap_mm((new_top - (y0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6)))
        # next z
        try:
            min_z = min(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        except Exception:
            min_z = 0
        self._items[rect] = CanvasObject(
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

    def _place_slots(self, silent: bool = False):
        # Validate and read inputs
        try:
            jx = float(self.jig_x.get()); jy = float(self.jig_y.get())
            sw = float(self.slot_w.get()); sh = float(self.slot_h.get())
            ox = float(self.origin_x.get()); oy = float(self.origin_y.get())
            sx = float(self.step_w.get() or 0.0); sy = float(self.step_h.get() or 0.0)
        except Exception:
            if not silent:
                messagebox.showerror("Invalid input", "Enter numeric jig, slot, origin and step values (mm).")
            return
        # Basic validation
        if sw <= 0 or sh <= 0:
            if not silent:
                messagebox.showerror("Invalid slot size", "Slot width and height must be > 0 mm.")
            return
        if sw > jx or sh > jy:
            # If slot doesn't fit the jig, remove any existing slots and stop
            for cid, meta in list(self._items.items()):
                if meta.get("type") == "slot":
                    try:
                        if meta.get("label_id"):
                            self.canvas.delete(meta.get("label_id"))
                    except Exception:
                        pass
                    try:
                        self.canvas.delete(cid)
                    except Exception:
                        pass
                    self._items.pop(cid, None)
            self._update_scrollregion()
            if not silent:
                messagebox.showerror("Slot too large", "Slot must fit inside the jig size.")
            return
        if ox < 0 or oy < 0:
            if not silent:
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
        for cid, meta in list(self._items.items()):
            if meta.get("type") == "slot":
                try:
                    if meta.get("label_id"):
                        self.canvas.delete(meta.get("label_id"))
                except Exception:
                    pass
                try:
                    self.canvas.delete(cid)
                except Exception:
                    pass
                self._items.pop(cid, None)

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
                    self._create_slot_at_mm(f"Slot {counter}", sw, sh, x_mm, y_mm)
                    counter += 1
                    placed_any = True
                col += 1
            if not placed_any and row > 0:
                # No more space vertically
                break
            row += 1
        # Finalize visuals
        self._update_scrollregion()
        self._raise_all_labels()
        try:
            self.selection._reorder_by_z()
        except Exception:
            pass
        # After repositioning items, ensure slot labels are sequential in desired order
        try:
            self._renumber_slots()
        except Exception:
            pass
        # Ensure labels are contiguous and ordered right-to-left, bottom-to-top
        try:
            self._renumber_slots()
        except Exception:
            pass

    def _renumber_slots(self):
        # Build list of (left_px, top_px, rect_id, label_id) for slot rectangles using current canvas positions
        slots = []
        for cid, meta in self._items.items():
            if meta.get("type") == "slot":
                try:
                    x1, y1, x2, y2 = self.canvas.bbox(cid)
                except Exception:
                    continue
                slots.append((float(x1), float(y1), cid, meta.get("label_id")))
        # Sort rows first: bottom-to-top (y desc), then within row right-to-left (x desc)
        slots.sort(key=lambda t: (-t[1], -t[0]))
        # Apply contiguous labels starting from 1
        for idx, (_lx, _ty, _cid, lbl_id) in enumerate(slots, start=1):
            if lbl_id:
                try:
                    self.canvas.itemconfig(lbl_id, text=f"Slot {idx}")
                except Exception:
                    pass

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
        rect = self.canvas.create_rectangle(
            cx - scaled_w / 2 + ox, cy - scaled_h / 2 + oy, cx + scaled_w / 2 - ox, cy + scaled_h / 2 - oy,
            fill="#2b2b2b", outline=outline, width=2, tags=("text_item",) if outline == "#17a24b" else None
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
        try:
            max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        except Exception:
            max_z = 0
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
        self.selection.select(rect)
        self._update_scrollregion()
        self._raise_all_labels()
        try:
            self.selection._reorder_by_z()
        except Exception:
            pass

    def _drop_text(self):
        # Create a square rectangle with a text label inside, so it behaves like images
        default_w = 40.0
        default_h = 40.0
        # Text rectangles use green outline
        self.create_placeholder("Text", default_w, default_h, text_fill="#17a24b", outline="#17a24b")

    # ---- Image support ----
    def _render_photo(self, meta: dict, w_px: int, h_px: int) -> Optional[tk.PhotoImage]:
        # Returns a tk.PhotoImage of requested size; stores reference on meta to avoid GC
        if w_px < 1 or h_px < 1:
            return None
        path = meta.get("path")
        if not path or not os.path.exists(path):
            return None
        # Try high-quality resize via PIL
        try:
            if Image is not None and ImageTk is not None:
                pil = meta.get("pil")
                if pil is None:
                    pil = Image.open(path)
                    meta["pil"] = pil
                resized = pil.resize((int(w_px), int(h_px)), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized)
                meta["photo"] = photo
                return photo
        except Exception:
            pass
        # Fallback to tk.PhotoImage (best-effort; may not scale exactly)
        try:
            photo = tk.PhotoImage(file=path)
            meta["photo"] = photo
            return photo
        except Exception:
            return None

    def create_image_item(self, path: str, w_mm: float, h_mm: float, x_mm: Optional[float] = None, y_mm: Optional[float] = None) -> None:
        # place at the center of current viewport similar to placeholders
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        cx = self.canvas.canvasx(cw // 2)
        cy = self.canvas.canvasy(ch // 2)
        # snap width/height to integer millimeters
        qw_mm = self._snap_mm(w_mm)
        qh_mm = self._snap_mm(h_mm)
        base_w = float(qw_mm) * MM_TO_PX
        base_h = float(qh_mm) * MM_TO_PX
        scaled_w = int(round(base_w * self._zoom))
        scaled_h = int(round(base_h * self._zoom))
        # Ensure within jig; compute snapped top-left mm
        ox = self._item_outline_half_px()
        oy = self._item_outline_half_px()
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        if x_mm is None:
            x_mm = (cx - scaled_w / 2 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
        if y_mm is None:
            y_mm = (cy - scaled_h / 2 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
        sx_mm = self._snap_mm(x_mm)
        sy_mm = self._snap_mm(y_mm)
        new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
        new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
        # Build meta and render
        meta = CanvasObject(
            type="image",
            path=path,
            w_mm=float(qw_mm),
            h_mm=float(qh_mm),
            x_mm=float(sx_mm),
            y_mm=float(sy_mm),
        )
        photo = self._render_photo(meta, scaled_w, scaled_h)
        if photo is None:
            # fallback to placeholder if render failed
            self.create_placeholder(os.path.basename(path), qw_mm, qh_mm)
            return
        img_id = self.canvas.create_image(new_left, new_top, image=photo, anchor="nw")
        meta.canvas_id = img_id
        # assign next z
        try:
            max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        except Exception:
            max_z = 0
        try:
            meta["z"] = int(max_z + 1)
        except Exception:
            pass
        self._items[img_id] = meta
        self.selection.select(img_id)
        self._update_scrollregion()
        try:
            self.selection._reorder_by_z()
        except Exception:
            pass

    def _ai_arrange(self):
        # Arrange non-slot items into existing slots.
        # Order for both slots and items: right-to-left within a row, bottom-to-top across rows
        # so the first item goes to the lower-right slot, then leftwards, then rows upwards.

        # Collect and order slots by current canvas position
        slot_entries = []  # (left_px, top_px, slot_cid, slot_meta)
        for scid, smeta in self._items.items():
            if smeta.get("type") != "slot":
                continue
            try:
                bx = self.canvas.bbox(scid)
            except Exception:
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
        item_entries = []  # (left_px, top_px, cid, meta)
        for cid, meta in self._items.items():
            if meta.get("type") not in ("rect", "image"):
                continue
            try:
                bx = self.canvas.bbox(cid)
            except Exception:
                bx = None
            if not bx:
                # For images sometimes bbox can be None until drawn; use coords as fallback
                try:
                    cx, cy = self.canvas.coords(cid)
                    bx = (float(cx), float(cy), float(cx), float(cy))
                except Exception:
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
            try:
                item_w_mm = float(meta.get("w_mm", 0.0))
                item_h_mm = float(meta.get("h_mm", 0.0))
                x_mm = float(slot_meta.get("x_mm", 0.0))
                y_mm = float(slot_meta.get("y_mm", 0.0))
            except Exception:
                continue

            # Item size in pixels (keep as-is, do NOT resize)
            w_px = int(round(item_w_mm * MM_TO_PX * self._zoom))
            h_px = int(round(item_h_mm * MM_TO_PX * self._zoom))
            # Slot size and top-left in pixels
            slot_w_mm = float(slot_meta.get("w_mm", 0.0))
            slot_h_mm = float(slot_meta.get("h_mm", 0.0))
            slot_w_px = int(round(slot_w_mm * MM_TO_PX * self._zoom))
            slot_h_px = int(round(slot_h_mm * MM_TO_PX * self._zoom))
            slot_left_px = jx0 + ox + x_mm * MM_TO_PX * self._zoom
            slot_top_px = jy0 + oy + y_mm * MM_TO_PX * self._zoom
            # Desired top-left so that item is centered within the slot
            desired_left = slot_left_px + (slot_w_px - w_px) / 2.0
            desired_top = slot_top_px + (slot_h_px - h_px) / 2.0
            # Clamp to keep item fully inside jig
            min_left = jx0 + ox
            min_top = jy0 + oy
            max_left = jx1 - ox - w_px
            max_top = jy1 - oy - h_px
            left = max(min_left, min(desired_left, max_left))
            top = max(min_top, min(desired_top, max_top))

            if meta.get("type") == "rect":
                self.canvas.coords(cid, left, top, left + w_px, top + h_px)
                lbl_id = meta.get("label_id")
                if lbl_id:
                    self.canvas.coords(lbl_id, left + w_px / 2, top + h_px / 2)
                meta["x_mm"] = float(self._snap_mm((left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))))
                meta["y_mm"] = float(self._snap_mm((top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))))
                self._raise_all_labels()
            else:
                # Ensure image rendered at current size (based on its own mm)
                photo = self._render_photo(meta, max(1, int(w_px)), max(1, int(h_px)))
                if photo is not None:
                    self.canvas.itemconfig(cid, image=photo)
                self.canvas.coords(cid, left, top)
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, left, top, left + w_px, top + h_px)
                meta["x_mm"] = float(self._snap_mm((left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))))
                meta["y_mm"] = float(self._snap_mm((top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))))

        try:
            self.selection._reorder_by_z()
        except Exception:
            pass

    # Selection/drag delegated to CanvasSelection

    def _redraw_jig(self, _evt=None, center=True):
        self.canvas.delete("jig")
        try:
            jx = float(self.jig_x.get())
            jy = float(self.jig_y.get())
        except ValueError:
            jx, jy = 296, 415
        # Draw jig scaled by current zoom
        w = int(jx * MM_TO_PX * self._zoom)
        h = int(jy * MM_TO_PX * self._zoom)
        pad = 20
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
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
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#dddddd", width=3, tags="jig")
        self._update_scrollregion()
        if center:
            self._center_view()
        # Reposition all items using persisted mm
        for cid, meta in self._items.items():
            t = meta.get("type")
            if t == "rect" or t == "slot":
                try:
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                    w_mm = float(meta.get("w_mm", 0.0))
                    h_mm = float(meta.get("h_mm", 0.0))
                except Exception:
                    continue
                # Allow touching jig border for rects and slots
                ox = 0.0
                oy = 0.0
                w = w_mm * MM_TO_PX * self._zoom
                h = h_mm * MM_TO_PX * self._zoom
                min_left = x0 + ox
                min_top = y0 + oy
                max_left = x1 - ox - w
                max_top = y1 - oy - h
                left = x0 + x_mm * MM_TO_PX * self._zoom + ox
                top = y0 + y_mm * MM_TO_PX * self._zoom + oy
                new_left = max(min_left, min(left, max_left))
                new_top = max(min_top, min(top, max_top))
                self.canvas.coords(cid, new_left, new_top, new_left + w, new_top + h)
                if meta.get("label_id"):
                    self.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                    try:
                        self.canvas.itemconfig(meta["label_id"], font=("Myriad Pro", self._scaled_pt(10)))
                    except Exception:
                        pass
                self._raise_all_labels()
                # don't mutate stored mm during redraw
            elif t == "image":
                try:
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                    w_mm = float(meta.get("w_mm", 0.0))
                    h_mm = float(meta.get("h_mm", 0.0))
                except Exception:
                    continue
                # Allow touching jig border for images
                ox = 0.0
                oy = 0.0
                w = int(round(w_mm * MM_TO_PX * self._zoom))
                h = int(round(h_mm * MM_TO_PX * self._zoom))
                min_left = x0 + ox
                min_top = y0 + oy
                max_left = x1 - ox - w
                max_top = y1 - oy - h
                left = x0 + x_mm * MM_TO_PX * self._zoom + ox
                top = y0 + y_mm * MM_TO_PX * self._zoom + oy
                new_left = max(min_left, min(left, max_left))
                new_top = max(min_top, min(top, max_top))
                photo = self._render_photo(meta, max(1, int(w)), max(1, int(h)))
                if photo is not None:
                    self.canvas.itemconfig(cid, image=photo)
                self.canvas.coords(cid, new_left, new_top)
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, new_left, new_top, new_left + w, new_top + h)
                # don't mutate stored mm during redraw
            elif t == "text":
                try:
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                except Exception:
                    continue
                cx = x0 + x_mm * MM_TO_PX * self._zoom
                cy = y0 + y_mm * MM_TO_PX * self._zoom
                new_cx = max(x0, min(cx, x1))
                new_cy = max(y0, min(cy, y1))
                self.canvas.coords(cid, new_cx, new_cy)
                try:
                    self.canvas.itemconfig(cid, font=("Myriad Pro", self._scaled_pt(12), "bold"))
                except Exception:
                    pass
                # don't mutate stored mm during redraw
        # Re-apply stacking order after positions were updated
        try:
            self.selection._reorder_by_z()
        except Exception:
            pass

    def _jig_rect_px(self):
        objs = self.canvas.find_withtag("jig")
        if not objs:
            return (20, 20, self.canvas.winfo_width() - 20, self.canvas.winfo_height() - 20)
        return self.canvas.bbox(objs[0])

    def _jig_inner_rect_px(self):
        x0, y0, x1, y1 = self._jig_rect_px()
        # compensate for jig border width (3px) drawing centered on the rectangle edge
        stroke = 3.0
        half = stroke / 2.0
        return (x0 + half, y0 + half, x1 - half, y1 - half)

    def _item_outline_half_px(self) -> float:
        # Rectangle outline width is 2 px (see _create_placeholder); keep fully inside jig
        return 1.0

    def _update_scrollregion(self):
        # still maintain scrollregion internally for centering math
        bbox = self.canvas.bbox("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if bbox is None:
            self.canvas.configure(scrollregion=(0, 0, cw, ch))
            return
        x0, y0, x1, y1 = bbox
        pad = 20
        left = min(0, x0 - pad)
        top = min(0, y0 - pad)
        right = max(cw, x1 + pad)
        bottom = max(ch, y1 + pad)
        self.canvas.configure(scrollregion=(left, top, right, bottom))

    def _center_view(self):
        # Center viewport on the jig if content is larger than the viewport
        jig_bbox = self.canvas.bbox("jig")
        all_bbox = self.canvas.bbox("all")
        if not jig_bbox or not all_bbox:
            return
        x0, y0, x1, y1 = jig_bbox
        ax0, ay0, ax1, ay1 = all_bbox
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        total_w = max(1, ax1 - ax0)
        total_h = max(1, ay1 - ay0)
        # Only move if we actually have scrollable overflow
        if total_w > cw:
            target_x = (x0 + x1) / 2 - cw / 2
            frac_x = (target_x - ax0) / max(1, total_w - cw)
            frac_x = min(1.0, max(0.0, frac_x))
            try:
                self.canvas.xview_moveto(frac_x)
            except Exception:
                pass
        if total_h > ch:
            target_y = (y0 + y1) / 2 - ch / 2
            frac_y = (target_y - ay0) / max(1, total_h - ch)
            frac_y = min(1.0, max(0.0, frac_y))
            try:
                self.canvas.yview_moveto(frac_y)
            except Exception:
                pass

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
            except Exception:
                pass
            return None
        # Raster: Pillow first
        try:
            from PIL import Image  # type: ignore
            with Image.open(path) as im:
                w_px, h_px = im.size
            return (float(w_px) / MM_TO_PX, float(h_px) / MM_TO_PX)
        except Exception:
            pass
        # Fallback to tk.PhotoImage (PNG/GIF)
        try:
            img = tk.PhotoImage(file=path)
            w_px, h_px = int(img.width()), int(img.height())
            return (float(w_px) / MM_TO_PX, float(h_px) / MM_TO_PX)
        except Exception:
            pass
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
        except Exception:
            pass
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
        except Exception:
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
        state.pkg_x = self.jig_x.get().strip()
        state.pkg_y = self.jig_y.get().strip()
        # Count only rectangle items (images). Text items are stored with type 'text'
        try:
            # Count only non-text rectangles (text placeholders use green outline)
            img_count = sum(
                1
                for _cid, meta in self._items.items()
                if meta.get("type") == "rect" and str(meta.get("outline", "")) != "#17a24b"
            )
        except Exception:
            img_count = 0
        state.nonsticker_image_count = int(img_count)
        # Snapshot current side (exclude slots) so both sides are up-to-date
        try:
            current_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
            self._scene_store[self._current_side] = current_no_slots
        except Exception:
            pass
        # Collect slots from the current canvas (slots are shared across sides)
        try:
            slots_only = [it for it in self._serialize_scene() if it.get("type") == "slot"]
        except Exception:
            slots_only = []
        # Ask where to save the two PDFs and render them
        # folder = filedialog.askdirectory(title="Select folder to save 2 files")
        try:
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

            self._render_scene_to_pdf(p_jig, front_items, jx, jy, only_jig=True, dpi=1200)
            self._render_scene_to_pdf(p_front, front_items, jx, jy, dpi=1200)
            self._render_scene_to_pdf(p_back, back_items, jx, jy, dpi=1200)
            # messagebox.showinfo("Saved", f"Saved 2 files to:\n{folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not process files:\n{e}")
        self.app.show_screen(NStickerResultsDownloadScreen)

    def _zoom_step(self, direction: int):
        # direction: +1 zoom in, -1 zoom out
        old_zoom = self._zoom
        if direction > 0:
            self._zoom = min(5.0, self._zoom * 1.1)
        else:
            self._zoom = max(0.2, self._zoom / 1.1)
        if abs(self._zoom - old_zoom) < 1e-6:
            return
        # Compute current viewport center pivot in mm relative to jig
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        px = self.canvas.canvasx(cw // 2)
        py = self.canvas.canvasy(ch // 2)
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        pivot_x_mm = (px - jx0) / (MM_TO_PX * max(old_zoom, 1e-6))
        pivot_y_mm = (py - jy0) / (MM_TO_PX * max(old_zoom, 1e-6))
        # Recompute all coordinates from mm at the new zoom
        self._redraw_jig(center=False)
        # Keep the same pivot at the center of the viewport
        try:
            njx0, njy0, njx1, njy1 = self._jig_inner_rect_px()
            target_px = njx0 + pivot_x_mm * MM_TO_PX * self._zoom
            target_py = njy0 + pivot_y_mm * MM_TO_PX * self._zoom
            # Update scrollregion and move view so target pivot is centered
            self._update_scrollregion()
            sx0, sy0, sx1, sy1 = [float(v) for v in str(self.canvas.cget("scrollregion")).split()]
            total_w = max(1.0, sx1 - sx0)
            total_h = max(1.0, sy1 - sy0)
            desired_left = max(sx0, min(target_px - cw / 2, sx1 - cw))
            desired_top = max(sy0, min(target_py - ch / 2, sy1 - ch))
            if total_w > cw:
                self.canvas.xview_moveto((desired_left - sx0) / (total_w - cw))
            if total_h > ch:
                self.canvas.yview_moveto((desired_top - sy0) / (total_h - ch))
        except Exception:
            pass
        # After zooming, scale all text fonts to match the new zoom
        try:
            self._update_all_text_fonts()
        except Exception:
            pass


    # ---- Front/Back scene state management ----
    def _clear_scene(self, keep_slots: bool = False):
        try:
            for cid, meta in list(self._items.items()):
                if keep_slots and meta.get("type") == "slot":
                    continue
                try:
                    self.canvas.delete(cid)
                except Exception:
                    pass
                try:
                    lbl_id = meta.get("label_id")
                    if lbl_id:
                        self.canvas.delete(lbl_id)
                except Exception:
                    pass
                self._items.pop(cid, None)
        finally:
            try:
                self.selection.select(None)
            except Exception:
                pass

    def _create_rect_at_mm(self, label: str, w_mm: float, h_mm: float, x_mm: float, y_mm: float, outline: str = "#d0d0d0", text_fill: str = "white"):
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
        # clamp top-left within inner jig
        min_left = x0 + ox
        min_top = y0 + oy
        max_left = x1 - ox - w
        max_top = y1 - oy - h
        left = x0 + x_mm_i * MM_TO_PX * self._zoom + ox
        top = y0 + y_mm_i * MM_TO_PX * self._zoom + oy
        new_left = max(min_left, min(left, max_left))
        new_top = max(min_top, min(top, max_top))
        rect = self.canvas.create_rectangle(new_left, new_top, new_left + w, new_top + h, fill="#2b2b2b", outline=outline, width=2, tags=("text_item",) if outline == "#17a24b" else None)
        txt = self.canvas.create_text(new_left + w / 2, new_top + h / 2, text=label, fill=text_fill, font=("Myriad Pro", self._scaled_pt(10)), tags=("label",))

        # keep provided mm unless clamped
        if new_left != left or new_top != top:
            x_mm_i = self._snap_mm((new_left - (x0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6)))
            y_mm_i = self._snap_mm((new_top - (y0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6)))
        # next z
        try:
            max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
        except Exception:
            max_z = 0
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
        )

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
                    })
                except Exception:
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
                    })
                except Exception:
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
                    })
                except Exception:
                    continue
        return items

    def _restore_scene(self, items: list[dict]):
        for it in items:
            t = it.get("type")
            if t == "rect":
                outline = str(it.get("outline", "#d0d0d0"))
                # If restored rect is a Text rect, it may have green outline
                text_fill = "#17a24b" if outline == "#17a24b" else "white"
                self._create_rect_at_mm(
                    it.get("label", ""),
                    float(it.get("w_mm", 0.0)),
                    float(it.get("h_mm", 0.0)),
                    float(it.get("x_mm", 0.0)),
                    float(it.get("y_mm", 0.0)),
                    outline=outline,
                    text_fill=text_fill,
                )
            elif t == "slot":
                outline = str(it.get("outline", "#9a9a9a"))
                self._create_slot_at_mm(
                    it.get("label", ""),
                    float(it.get("w_mm", 0.0)),
                    float(it.get("h_mm", 0.0)),
                    float(it.get("x_mm", 0.0)),
                    float(it.get("y_mm", 0.0)),
                )
            elif t == "image":
                path = str(it.get("path", ""))
                if path and os.path.exists(path):
                    # Create image at specified mm top-left
                    x_mm = float(it.get("x_mm", 0.0))
                    y_mm = float(it.get("y_mm", 0.0))
                    w_mm = float(it.get("w_mm", 0.0))
                    h_mm = float(it.get("h_mm", 0.0))
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
                    )
                    photo = self._render_photo(meta, max(1, int(w_px)), max(1, int(h_px)))
                    if photo is not None:
                        img_id = self.canvas.create_image(left, top, image=photo, anchor="nw")
                        meta.canvas_id = img_id
                        # assign next z
                        try:
                            max_z = max(int(m.get("z", 0)) for _cid, m in self._items.items()) if self._items else 0
                        except Exception:
                            max_z = 0
                        try:
                            meta["z"] = int(max_z + 1)
                        except Exception:
                            pass
                        self._items[img_id] = meta
            elif t == "text":
                self._create_text_at_mm(
                    it.get("text", "Text"),
                    float(it.get("x_mm", 0.0)),
                    float(it.get("y_mm", 0.0)),
                    str(it.get("fill", "white")),
                )

    def _on_backside_toggle(self, *_):
        # Deselect any current selection before switching sides
        try:
            self.selection.select(None)
        except Exception:
            pass
        # Save current scene under current side (exclude slots)
        try:
            data_no_slots = [it for it in self._serialize_scene() if it.get("type") != "slot"]
            self._scene_store[self._current_side] = data_no_slots
        except Exception:
            pass
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

    def _render_scene_to_pdf(
        self, 
        path: str, 
        items: list[dict], 
        jig_w_mm: float, 
        jig_h_mm: float, 
        only_jig: bool = False, 
        dpi: int = 300
    ) -> None:
        """Render a scene (slots + items) into a single-page PDF.

        - Places the jig rectangle at the lower-right corner of a US Letter page.
        - Draws slots, rectangles, text, and raster images at exact mm coordinates.
        - Requires Pillow; raises if unavailable.
        """
        try:
            from PIL import Image as _PIL_Image  # type: ignore
            from PIL import ImageDraw as _PIL_Draw  # type: ignore
            from PIL import ImageFont as _PIL_Font  # type: ignore
        except Exception as _err:
            raise RuntimeError("Pillow (PIL) is required to export PDF.") from _err

        # Page equals jig size in mm
        px_per_mm = float(dpi) / 25.4
        page_w_px = max(1, int(round(jig_w_mm * px_per_mm)))
        page_h_px = max(1, int(round(jig_h_mm * px_per_mm)))
        img = _PIL_Image.new("RGB", (page_w_px, page_h_px), "white")
        draw = _PIL_Draw.Draw(img)
        try:
            font_small = _PIL_Font.load_default()
        except Exception:
            font_small = None

        # Jig covers the entire page; draw its border
        jw = max(1, int(round(jig_w_mm * px_per_mm)))
        jh = max(1, int(round(jig_h_mm * px_per_mm)))
        jx0 = 0
        jy0 = 0
        jx1 = page_w_px - 1
        jy1 = page_h_px - 1
        # Draw jig border (slightly grey to mirror UI)
        draw.rectangle([jx0, jy0, jx1, jy1], outline=(221, 221, 221), width=3)

        def mm_to_px(m: float) -> int:
            return int(round(float(m) * px_per_mm))

        def rect_from_mm(x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> tuple[int, int, int, int]:
            # Round both edges so right/bottom alignment is exact to avoid gaps
            l = int(round(float(x_mm) * px_per_mm))
            t = int(round(float(y_mm) * px_per_mm))
            r = int(round(float(x_mm + w_mm) * px_per_mm))
            b = int(round(float(y_mm + h_mm) * px_per_mm))
            if r <= l:
                r = l + 1
            if b <= t:
                b = t + 1
            return l, t, r, b

        # Draw each item
        if only_jig:
            items = [it for it in items if it.get("type") == "slot"]

        for it in items:
            t = str(it.get("type", ""))
            if t == "slot":
                try:
                    # Items are positioned within jig; with jig at page origin
                    # use their mm directly from page origin
                    l, t, r, b = rect_from_mm(it.get("x_mm", 0.0), it.get("y_mm", 0.0), it.get("w_mm", 0.0), it.get("h_mm", 0.0))
                    # outline only (no fill) for slots
                    draw.rectangle([l, t, r - 1, b - 1], outline=(137, 137, 137), width=1)
                    label = str(it.get("label", ""))
                    if label and font_small is not None:
                        cx = l + (r - l) // 2
                        cy = t + (b - t) // 2
                        try:
                            tw, th = draw.textsize(label, font=font_small)
                            draw.text((cx - tw // 2, cy - th // 2), label, fill=(200, 200, 200), font=font_small)
                        except Exception:
                            pass
                except Exception:
                    continue
            elif t == "rect":
                try:
                    l, t, r, b = rect_from_mm(it.get("x_mm", 0.0), it.get("y_mm", 0.0), it.get("w_mm", 0.0), it.get("h_mm", 0.0))
                    outline = str(it.get("outline", "#d0d0d0"))
                    # parse outline color hex
                    try:
                        if outline.startswith("#") and len(outline) == 7:
                            r_col = int(outline[1:3], 16); g_col = int(outline[3:5], 16); b_col = int(outline[5:7], 16)
                            oc = (r_col, g_col, b_col)
                        else:
                            oc = (208, 208, 208)
                    except Exception:
                        oc = (208, 208, 208)
                    # fill same as UI for placeholders
                    draw.rectangle([l, t, r - 1, b - 1], fill=(43, 43, 43), outline=oc, width=2)
                    label = str(it.get("label", ""))
                    if label and font_small is not None:
                        try:
                            tw, th = draw.textsize(label, font=font_small)
                            cx = l + (r - l) // 2
                            cy = t + (b - t) // 2
                            draw.text((cx - tw // 2, cy - th // 2), label, fill=(255, 255, 255), font=font_small)
                        except Exception:
                            pass
                except Exception:
                    continue
            elif t == "image":
                try:
                    path_img = str(it.get("path", ""))
                    if not path_img:
                        continue
                    l, t, r, b = rect_from_mm(it.get("x_mm", 0.0), it.get("y_mm", 0.0), it.get("w_mm", 0.0), it.get("h_mm", 0.0))
                    rw = max(1, r - l)
                    rh = max(1, b - t)
                    with _PIL_Image.open(path_img) as im:
                        # Preserve alpha to avoid white background for PNGs
                        im = im.convert("RGBA")
                        im_resized = im.resize((int(rw), int(rh)), _PIL_Image.LANCZOS)
                        # Split alpha as mask if present
                        try:
                            _r, _g, _b, _a = im_resized.split()
                            mask = _a
                        except Exception:
                            mask = None
                        if mask is not None:
                            img.paste(im_resized.convert("RGB"), (int(l), int(t)), mask)
                        else:
                            img.paste(im_resized.convert("RGB"), (int(l), int(t)))
                except Exception:
                    continue
            elif t == "text":
                try:
                    txt = str(it.get("text", ""))
                    fill = str(it.get("fill", "#17a24b"))
                    # hex to rgb
                    try:
                        if fill.startswith("#") and len(fill) == 7:
                            r = int(fill[1:3], 16); g = int(fill[3:5], 16); b = int(fill[5:7], 16)
                            col = (r, g, b)
                        else:
                            col = (23, 162, 75)
                    except Exception:
                        col = (23, 162, 75)
                    cx = jx0 + mm_to_px(it.get("x_mm", 0.0))
                    cy = jy0 + mm_to_px(it.get("y_mm", 0.0))
                    if font_small is not None and txt:
                        try:
                            tw, th = draw.textsize(txt, font=font_small)
                            draw.text((int(cx - tw / 2), int(cy - th / 2)), txt, fill=col, font=font_small)
                        except Exception:
                            pass
                except Exception:
                    continue

        # Save as PDF
        img.save(path, "PDF", resolution=dpi)