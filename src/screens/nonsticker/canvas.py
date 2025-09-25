import os
import re
import struct
from pathlib import Path
from typing import Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.core import Screen, vcmd_float, COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL
from src.state import state, MM_TO_PX, IMAGES_PATH
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
        # live redraw when jig size changes
        self.jig_x.trace_add("write", lambda *_: self._redraw_jig())
        self.jig_y.trace_add("write", lambda *_: self._redraw_jig())

        # 4) White vertical separator
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
        self._create_tool_tile(
            tools,
            icon_image=self._img_cursor,
            icon_text=None,
            label_text="Select tool",
            command=lambda: None,
        )
        self._create_tool_tile(
            tools,
            icon_image=self._img_stick,
            icon_text=None,
            label_text="AI arrange",
            command=self._ai_arrange,
        )
        self._create_tool_tile(
            tools,
            icon_image=None,
            icon_text="T",
            label_text="Text",
            command=self._drop_text,
        )
        

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
        self.sel_x.trace_add("write", self._on_pos_change)
        self.sel_y.trace_add("write", self._on_pos_change)
        # Width/Height controls
        self.sel_w = tk.StringVar(value=state.pkg_x or "296")
        self.sel_h = tk.StringVar(value=state.pkg_y or "415")
        _wb = self._chip(row2, "Width:", self.sel_w, width=8)
        tk.Label(_wb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        _hb = self._chip(row2, "Height:", self.sel_h, width=8)
        tk.Label(_hb, text="mm", bg="#6f6f6f", fg="white").pack(side="left", padx=0)
        # live scale selection on size change
        self.sel_w.trace_add("write", self._on_size_change)
        self.sel_h.trace_add("write", self._on_size_change)

        
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
        self.canvas = tk.Canvas(board, bg="#5a5a5a", highlightthickness=2, highlightbackground="#2a2a2a")
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<Configure>", self._redraw_jig)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        # delete selected with keyboard Delete
        self.canvas.bind("<Delete>", self._on_delete)
        # middle-mouse panning
        self.canvas.bind("<Button-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_move)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        # zoom via Ctrl + MouseWheel / Ctrl + Button-4/5 (Linux)
        self.canvas.bind("<Control-MouseWheel>", self._on_wheel_zoom)
        self.canvas.bind("<Control-Button-4>", lambda _e: self._zoom_step(+1))
        self.canvas.bind("<Control-Button-5>", lambda _e: self._zoom_step(-1))
        # initial jig draw
        self.after(0, self._redraw_jig)
        # initialize jig size from Size fields when no saved size
        self._did_autosize = False
        self.after(0, self._ensure_initial_jig_size)

        self._items: dict[int, dict] = {}   # canvas_id -> meta
        self._selected: Optional[int] = None
        self._drag_off: Tuple[int, int] = (0, 0)
        self._drag_kind: Optional[str] = None  # 'rect' or 'text'
        self._drag_size: Tuple[int, int] = (0, 0)
        self._suppress_size_trace: bool = False
        self._suppress_pos_trace: bool = False
        self._zoom: float = 0.9
        # Per-side scene storage
        self._scene_store: dict[str, list[dict]] = {"front": [], "back": []}
        self._current_side: str = "front"

        # Key bindings for zoom in/out
        for seq in ("<KeyPress-+>", "<KeyPress-equal>", "<KP_Add>"):
            self.app.bind(seq, lambda _e: self._zoom_step(1))
        for seq in ("<KeyPress-minus>", "<KP_Subtract>"):
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

    # Actions
    

    

    def _import_image(self):
        path = filedialog.askopenfilename(
            title="Import Image",
            filetypes=[
                (".jpg, .png, .svg", ("*.jpg", "*.jpeg", "*.png", "*.svg")),
                ("All files", "*.*"),
            ],
        )
        if not path or not os.path.exists(path):
            return
        label = os.path.basename(path)
        size = self._compute_import_size_mm(path)
        if size is None:
            try:
                size = (float(self.sel_w.get()), float(self.sel_h.get()))
            except Exception:
                size = (40.0, 50.0)
        # For SVGs, keep placeholder since rasterization may not be available
        if str(Path(path).suffix).lower() == ".svg":
            self._create_placeholder(label, size[0], size[1])
            return
        # For raster images, render real content
        self._create_image_item(path, size[0], size[1])

    def _create_placeholder(self, label, w_mm, h_mm, text_fill: str = "white", outline: str = "#d0d0d0"):
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
        txt = self.canvas.create_text(cx, cy, text=label, fill=text_fill, font=("Myriad Pro", 10), tags=("label",))
        # Persist position in mm relative to jig for stability on jig resize
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        x_mm = (cx - scaled_w / 2 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
        y_mm = (cy - scaled_h / 2 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
        # snap to integer mm and align rectangle to snapped grid
        sx_mm = self._snap_mm(x_mm)
        sy_mm = self._snap_mm(y_mm)
        new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
        new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
        self.canvas.coords(rect, new_left, new_top, new_left + scaled_w, new_top + scaled_h)
        self.canvas.coords(txt, new_left + scaled_w / 2, new_top + scaled_h / 2)
        
        self._items[rect] = {
            "type": "rect",
            "w_mm": float(qw_mm),
            "h_mm": float(qh_mm),
            "x_mm": float(sx_mm),
            "y_mm": float(sy_mm),
            "label_id": txt,
            "outline": outline,
        }
        self._select(rect)
        self._update_scrollregion()
        self._raise_all_labels()

    def _drop_text(self):
        # Create a square rectangle with a text label inside, so it behaves like images
        default_w = 40.0
        default_h = 40.0
        # Text rectangles use green outline
        self._create_placeholder("Text", default_w, default_h, text_fill="#17a24b", outline="#17a24b")

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

    def _create_image_item(self, path: str, w_mm: float, h_mm: float) -> None:
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
        x_mm = (cx - scaled_w / 2 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
        y_mm = (cy - scaled_h / 2 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
        sx_mm = self._snap_mm(x_mm)
        sy_mm = self._snap_mm(y_mm)
        new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
        new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
        # Build meta and render
        meta = {
            "type": "image",
            "path": path,
            "w_mm": float(qw_mm),
            "h_mm": float(qh_mm),
            "x_mm": float(sx_mm),
            "y_mm": float(sy_mm),
            "photo": None,
            "pil": None,
            "border_id": None,
        }
        photo = self._render_photo(meta, scaled_w, scaled_h)
        if photo is None:
            # fallback to placeholder if render failed
            self._create_placeholder(os.path.basename(path), qw_mm, qh_mm)
            return
        img_id = self.canvas.create_image(new_left, new_top, image=photo, anchor="nw")
        self._items[img_id] = meta
        self._select(img_id)
        self._update_scrollregion()

    def _ai_arrange(self):
        pads = int(round(8 * self._zoom))
        x0, y0, x1, y1 = self._jig_inner_rect_px()
        x, y = x0 + pads, y0 + pads
        row_h = 0
        max_w = x1 - x0 - 2 * pads
        for cid, meta in self._items.items():
            if meta["type"] not in ("rect", "image"):
                continue
            w = int(round(meta["w_mm"] * MM_TO_PX * self._zoom))
            h = int(round(meta["h_mm"] * MM_TO_PX * self._zoom))
            if x + w > x0 + max_w:
                x = x0 + pads
                y += row_h + pads
                row_h = 0
            # compute clamped left/top
            ox = self._item_outline_half_px()
            oy = self._item_outline_half_px()
            jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
            min_left = jx0 + ox
            min_top = jy0 + oy
            max_left = jx1 - ox - w
            max_top = jy1 - oy - h
            left = max(min_left, min(x, max_left))
            top = max(min_top, min(y, max_top))
            if meta["type"] == "rect":
                self.canvas.coords(cid, left, top, left + w, top + h)
                if meta.get("label_id"):
                    self.canvas.coords(meta["label_id"], left + w / 2, top + h / 2)
                self._raise_all_labels()
            else:
                # image: ensure image rendered at current size
                photo = self._render_photo(meta, max(1, int(w)), max(1, int(h)))
                if photo is not None:
                    self.canvas.itemconfig(cid, image=photo)
                self.canvas.coords(cid, left, top)
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, left, top, left + w, top + h)
            # snap placed to nearest 1mm grid and persist
            raw_x_mm = (left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            raw_y_mm = (top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            sx_mm = self._snap_mm(raw_x_mm)
            sy_mm = self._snap_mm(raw_y_mm)
            # clamp snapped mm to bounds
            min_mm_x = (min_left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            max_mm_x = (max_left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            min_mm_y = (min_top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            max_mm_y = (max_top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            sx_mm = int(max(min_mm_x, min(sx_mm, max_mm_x)))
            sy_mm = int(max(min_mm_y, min(sy_mm, max_mm_y)))
            new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
            new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
            if meta["type"] == "rect":
                self.canvas.coords(cid, new_left, new_top, new_left + w, new_top + h)
                if meta.get("label_id"):
                    self.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
            else:
                self.canvas.coords(cid, new_left, new_top)
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, new_left, new_top, new_left + w, new_top + h)
            meta["x_mm"] = float(sx_mm)
            meta["y_mm"] = float(sy_mm)
            row_h = max(row_h, h)
            x += w + pads

    # Selection/drag
    def _on_click(self, e):
        try:
            self.canvas.focus_set()
        except Exception:
            pass
        hit = self.canvas.find_withtag("current")
        target = None
        if hit:
            cid = hit[0]
            if cid in self._items:
                target = cid
            else:
                # If user clicked on a label inside a rect, select its owning rect
                for rid, meta in self._items.items():
                    if meta.get("label_id") == cid:
                        target = rid
                        break
        self._select(target)
        if target:
            meta = self._items.get(target, {})
            if meta.get("type") in ("rect", "image"):
                x1, y1, x2, y2 = self.canvas.bbox(target)
                self._drag_off = (e.x - x1, e.y - y1)
                # Use bbox size for both rects and images
                self._drag_size = (x2 - x1, y2 - y1)
                self._drag_kind = "rect"
            else:
                cx, cy = self.canvas.coords(target)
                self._drag_off = (e.x - cx, e.y - cy)
                self._drag_kind = "text"
        else:
            self._drag_kind = None

    def _on_drag(self, e):
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        if self._drag_kind == "rect":
            x1 = e.x - self._drag_off[0]
            y1 = e.y - self._drag_off[1]
            # constrain to inner jig bounds
            jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
            w, h = self._drag_size
            ox = self._item_outline_half_px()
            oy = self._item_outline_half_px()
            x1 = max(jx0 + ox, min(x1, jx1 - ox - w))
            y1 = max(jy0 + oy, min(y1, jy1 - oy - h))
            # compute raw mm from clamped px, then snap to nearest 1mm
            raw_x_mm = (x1 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            raw_y_mm = (y1 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            sx_mm = self._snap_mm(raw_x_mm)
            sy_mm = self._snap_mm(raw_y_mm)
            # clamp snapped mm to allowed integer range
            min_mm_x = (jx0 + ox - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            max_mm_x = (jx1 - ox - w - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            min_mm_y = (jy0 + oy - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            max_mm_y = (jy1 - oy - h - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            sx_mm = int(max(min_mm_x, min(sx_mm, max_mm_x)))
            sy_mm = int(max(min_mm_y, min(sy_mm, max_mm_y)))
            # if snapped mm didn't change, skip redundant updates for smoother feel
            prev_mm_x = int(round(float(meta.get("x_mm", 0))))
            prev_mm_y = int(round(float(meta.get("y_mm", 0))))
            if sx_mm == prev_mm_x and sy_mm == prev_mm_y:
                return
            new_left = (jx0 + ox) + sx_mm * MM_TO_PX * self._zoom
            new_top = (jy0 + oy) + sy_mm * MM_TO_PX * self._zoom
            if meta.get("type") == "rect":
                self.canvas.coords(self._selected, new_left, new_top, new_left + w, new_top + h)
                if meta.get("label_id"):
                    self.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                    self._raise_all_labels()
            elif meta.get("type") == "image":
                self.canvas.coords(self._selected, new_left, new_top)
                # move selection border if present
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, new_left, new_top, new_left + w, new_top + h)
            # update integer position fields and persist
            try:
                self._suppress_pos_trace = True
                if self.sel_x.get() != str(int(sx_mm)):
                    self.sel_x.set(str(int(sx_mm)))
                if self.sel_y.get() != str(int(sy_mm)):
                    self.sel_y.set(str(int(sy_mm)))
                meta["x_mm"], meta["y_mm"] = float(int(sx_mm)), float(int(sy_mm))
            finally:
                self._suppress_pos_trace = False
        elif self._drag_kind == "text":
            cx = e.x - self._drag_off[0]
            cy = e.y - self._drag_off[1]
            self.canvas.coords(self._selected, cx, cy)
            # persist text center in mm
            try:
                jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
                x_mm = (cx - jx0) / (MM_TO_PX * max(self._zoom, 1e-6))
                y_mm = (cy - jy0) / (MM_TO_PX * max(self._zoom, 1e-6))
                meta["x_mm"], meta["y_mm"] = float(x_mm), float(y_mm)
            except Exception:
                pass

    def _on_release(self, _):
        self._drag_kind = None

    def _on_delete(self, _evt=None):
        if not self._selected:
            return
        cid = self._selected
        meta = self._items.pop(cid, None)
        if meta is None:
            return
        try:
            self.canvas.delete(cid)
        except Exception:
            pass
        # delete selection border if any
        try:
            bid = meta.get("border_id")
            if bid:
                self.canvas.delete(bid)
        except Exception:
            pass
        try:
            lbl_id = meta.get("label_id")
            if lbl_id:
                self.canvas.delete(lbl_id)
        except Exception:
            pass
        self._selected = None
        self._update_scrollregion()

    # Middle mouse panning helpers
    def _on_pan_start(self, e):
        try:
            self.canvas.scan_mark(e.x, e.y)
        except Exception:
            pass

    def _on_pan_move(self, e):
        try:
            self.canvas.scan_dragto(e.x, e.y, gain=1)
        except Exception:
            pass

    def _on_pan_end(self, _e):
        # no-op; keep for symmetry/future logic
        pass

    def _on_wheel_zoom(self, e):
        try:
            delta = int(e.delta)
        except Exception:
            delta = 0
        if delta == 0:
            return "break"
        self._zoom_step(1 if delta > 0 else -1)
        return "break"

    def _select(self, cid: Optional[int]):
        if getattr(self, "_selected", None) and self._selected in self._items:
            prev_meta = self._items.get(self._selected, {})
            if prev_meta.get("type") == "rect":
                # restore prior outline color for rect on deselect
                outline_col = prev_meta.get("outline", "#d0d0d0")
                self.canvas.itemconfig(self._selected, outline=outline_col, width=2)
            elif prev_meta.get("type") == "text":
                # restore default text color when deselected
                self.canvas.itemconfig(self._selected, fill=prev_meta.get("default_fill", "white"))
            elif prev_meta.get("type") == "image":
                # remove selection border if present
                bid = prev_meta.get("border_id")
                if bid:
                    try:
                        self.canvas.delete(bid)
                    except Exception:
                        pass
                    prev_meta["border_id"] = None
        self._selected = cid
        if not cid:
            # clear fields when no selection
            try:
                self._suppress_size_trace = True
                self._suppress_pos_trace = True
                self.sel_w.set("")
                self.sel_h.set("")
                self.sel_x.set("")
                self.sel_y.set("")
            finally:
                self._suppress_pos_trace = False
                self._suppress_size_trace = False
            return
        meta = self._items.get(cid, {})
        if meta.get("type") == "rect":
            self.canvas.itemconfig(cid, outline="#6ec8ff", width=3)
            # set size fields without triggering live resize
            try:
                self._suppress_size_trace = True
                self.sel_w.set(str(int(round(float(meta["w_mm"] or 0)))))
                self.sel_h.set(str(int(round(float(meta["h_mm"] or 0)))))
            finally:
                self._suppress_size_trace = False
            # set position from stored mm without triggering move
            try:
                self._suppress_pos_trace = True
                self.sel_x.set(str(int(round(float(meta.get("x_mm", 0.0))))))
                self.sel_y.set(str(int(round(float(meta.get("y_mm", 0.0))))))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") == "image":
            # draw selection border around image
            try:
                x1, y1, x2, y2 = self.canvas.bbox(cid)
                bid = self.canvas.create_rectangle(x1, y1, x2, y2, outline="#6ec8ff", width=3)
                meta["border_id"] = bid
            except Exception:
                pass
            try:
                self._suppress_size_trace = True
                self.sel_w.set(str(int(round(float(meta["w_mm"] or 0)))))
                self.sel_h.set(str(int(round(float(meta["h_mm"] or 0)))))
            finally:
                self._suppress_size_trace = False
            try:
                self._suppress_pos_trace = True
                self.sel_x.set(str(int(round(float(meta.get("x_mm", 0.0))))))
                self.sel_y.set(str(int(round(float(meta.get("y_mm", 0.0))))))
            finally:
                self._suppress_pos_trace = False
        elif meta.get("type") == "text":
            # highlight selected text in blue
            self.canvas.itemconfig(cid, fill="#6ec8ff")

    def _apply_size_to_selection(self):
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image"):
            return
        # Treat empty inputs as 0mm without overwriting the entry text
        raw_w = (self.sel_w.get() or "").strip()
        raw_h = (self.sel_h.get() or "").strip()
        try:
            w_mm = 0 if raw_w == "" else self._snap_mm(raw_w)
            h_mm = 0 if raw_h == "" else self._snap_mm(raw_h)
        except ValueError:
            messagebox.showerror("Invalid size", "Enter numeric X/Y (mm).")
            return
        meta["w_mm"] = float(w_mm)
        meta["h_mm"] = float(h_mm)
        x1, y1, x2, y2 = self.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = int(round(w_mm * MM_TO_PX * self._zoom))
        h = int(round(h_mm * MM_TO_PX * self._zoom))
        if meta.get("type") == "rect":
            self.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if meta.get("label_id"):
                self.canvas.coords(meta["label_id"], cx, cy)
                self._raise_all_labels()
        elif meta.get("type") == "image":
            # re-render image at new size and keep center
            photo = self._render_photo(meta, max(1, int(w)), max(1, int(h)))
            if photo is not None:
                # move to top-left to keep same center
                self.canvas.coords(self._selected, cx - w / 2, cy - h / 2)
                self.canvas.itemconfig(self._selected, image=photo)
                bid = meta.get("border_id")
                if bid:
                    self.canvas.coords(bid, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        self._update_scrollregion()
        # update position fields to new top-left after resize
        try:
            self._suppress_pos_trace = True
            bx1, by1, bx2, by2 = self.canvas.bbox(self._selected)
            jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
            ox = self._item_outline_half_px(); oy = self._item_outline_half_px()
            raw_x_mm = (bx1 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            raw_y_mm = (by1 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            sx_mm = self._snap_mm(raw_x_mm)
            sy_mm = self._snap_mm(raw_y_mm)
            self.sel_x.set(str(int(sx_mm)))
            self.sel_y.set(str(int(sy_mm)))
            meta["x_mm"] = float(int(sx_mm))
            meta["y_mm"] = float(int(sy_mm))
        finally:
            self._suppress_pos_trace = False

    def _on_size_change(self, *_):
        # live update selection size while typing, best-effort
        if self._suppress_size_trace:
            return
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image"):
            return
        raw_w = (self.sel_w.get() or "").strip()
        raw_h = (self.sel_h.get() or "").strip()
        try:
            w_mm = 0 if raw_w == "" else self._snap_mm(raw_w)
            h_mm = 0 if raw_h == "" else self._snap_mm(raw_h)
        except ValueError:
            return
        # Reflect integer values only if user did not clear the input
        try:
            self._suppress_size_trace = True
            if raw_w != "":
                self.sel_w.set(str(int(w_mm)))
            if raw_h != "":
                self.sel_h.set(str(int(h_mm)))
        finally:
            self._suppress_size_trace = False
        meta["w_mm"] = float(w_mm)
        meta["h_mm"] = float(h_mm)
        x1, y1, x2, y2 = self.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        if meta.get("type") == "rect":
            w = w_mm * MM_TO_PX * self._zoom
            h = h_mm * MM_TO_PX * self._zoom
            self.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if meta.get("label_id"):
                self.canvas.coords(meta["label_id"], cx, cy)
                self._raise_all_labels()
        else:
            # image: re-render at new size and keep center
            w_px = max(1, int(round(w_mm * MM_TO_PX * self._zoom)))
            h_px = max(1, int(round(h_mm * MM_TO_PX * self._zoom)))
            photo = self._render_photo(meta, w_px, h_px)
            if photo is not None:
                self.canvas.itemconfig(self._selected, image=photo)
            # move image so center remains the same
            self.canvas.coords(self._selected, cx - w_px / 2, cy - h_px / 2)
            bid = meta.get("border_id")
            if bid:
                self.canvas.coords(bid, cx - w_px / 2, cy - h_px / 2, cx + w_px / 2, cy + h_px / 2)
        self._update_scrollregion()
        # update position fields to new top-left after resize
        try:
            self._suppress_pos_trace = True
            bx1, by1, bx2, by2 = self.canvas.bbox(self._selected)
            jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
            ox = self._item_outline_half_px(); oy = self._item_outline_half_px()
            raw_x_mm = (bx1 - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6))
            raw_y_mm = (by1 - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6))
            sx_mm = self._snap_mm(raw_x_mm)
            sy_mm = self._snap_mm(raw_y_mm)
            self.sel_x.set(str(int(sx_mm)))
            self.sel_y.set(str(int(sy_mm)))
            meta["x_mm"], meta["y_mm"] = float(int(sx_mm)), float(int(sy_mm))
        finally:
            self._suppress_pos_trace = False

    def _on_pos_change(self, *_):
        if self._suppress_pos_trace:
            return
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        if meta.get("type") not in ("rect", "image"):
            return
        try:
            x_mm = self._snap_mm(self.sel_x.get())
            y_mm = self._snap_mm(self.sel_y.get())
        except ValueError:
            return
        w_mm = float(meta.get("w_mm", 0) or 0)
        h_mm = float(meta.get("h_mm", 0) or 0)
        jx0, jy0, jx1, jy1 = self._jig_inner_rect_px()
        ox = self._item_outline_half_px(); oy = self._item_outline_half_px()
        # desired top-left in px from typed mm
        desired_left = jx0 + ox + int(x_mm) * MM_TO_PX * self._zoom
        desired_top = jy0 + oy + int(y_mm) * MM_TO_PX * self._zoom
        w = w_mm * MM_TO_PX * self._zoom
        h = h_mm * MM_TO_PX * self._zoom
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
                x_mm = self._snap_mm((new_left - (jx0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6)))
                y_mm = self._snap_mm((new_top - (jy0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6)))
                self.sel_x.set(str(int(x_mm)))
                self.sel_y.set(str(int(y_mm)))
            finally:
                self._suppress_pos_trace = False
        # move selection and label
        if meta.get("type") == "rect":
            self.canvas.coords(self._selected, new_left, new_top, new_left + w, new_top + h)
            if meta.get("label_id"):
                self.canvas.coords(meta["label_id"], new_left + w / 2, new_top + h / 2)
                self._raise_all_labels()
        elif meta.get("type") == "image":
            self.canvas.coords(self._selected, new_left, new_top)
            bid = meta.get("border_id")
            if bid:
                self.canvas.coords(bid, new_left, new_top, new_left + w, new_top + h)
        # persist mm
        meta["x_mm"], meta["y_mm"] = float(int(x_mm)), float(int(y_mm))
        self._update_scrollregion()

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
            if t == "rect":
                try:
                    x_mm = float(meta.get("x_mm", 0.0))
                    y_mm = float(meta.get("y_mm", 0.0))
                    w_mm = float(meta.get("w_mm", 0.0))
                    h_mm = float(meta.get("h_mm", 0.0))
                except Exception:
                    continue
                ox = self._item_outline_half_px()
                oy = self._item_outline_half_px()
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
                ox = self._item_outline_half_px()
                oy = self._item_outline_half_px()
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
                # don't mutate stored mm during redraw

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


    # ---- Front/Back scene state management ----
    def _clear_scene(self):
        try:
            for cid, meta in list(self._items.items()):
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
        finally:
            self._items.clear()
            self._selected = None

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
        txt = self.canvas.create_text(new_left + w / 2, new_top + h / 2, text=label, fill=text_fill, font=("Myriad Pro", 10), tags=("label",))
        
        # keep provided mm unless clamped
        if new_left != left or new_top != top:
            x_mm_i = self._snap_mm((new_left - (x0 + ox)) / (MM_TO_PX * max(self._zoom, 1e-6)))
            y_mm_i = self._snap_mm((new_top - (y0 + oy)) / (MM_TO_PX * max(self._zoom, 1e-6)))
        self._items[rect] = {
            "type": "rect",
            "w_mm": float(w_mm_i),
            "h_mm": float(h_mm_i),
            "x_mm": float(x_mm_i),
            "y_mm": float(y_mm_i),
            "label_id": txt,
            "outline": outline,
        }

    def _create_text_at_mm(self, text: str, x_mm: float, y_mm: float, fill: str = "#17a24b"):
        x0, y0, x1, y1 = self._jig_inner_rect_px()
        cx = x0 + x_mm * MM_TO_PX * self._zoom
        cy = y0 + y_mm * MM_TO_PX * self._zoom
        # clamp center within inner jig
        cx = max(x0, min(cx, x1))
        cy = max(y0, min(cy, y1))
        tid = self.canvas.create_text(cx, cy, text=text, fill=fill, font=("Myriad Pro", 12, "bold"), tags=("label",))
        self._items[tid] = {"type": "text", "default_fill": fill, "x_mm": float((cx - x0) / (MM_TO_PX * max(self._zoom, 1e-6))), "y_mm": float((cy - y0) / (MM_TO_PX * max(self._zoom, 1e-6)))}

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
                    meta = {
                        "type": "image",
                        "path": path,
                        "w_mm": float(self._snap_mm(w_mm)),
                        "h_mm": float(self._snap_mm(h_mm)),
                        "x_mm": float(self._snap_mm(x_mm)),
                        "y_mm": float(self._snap_mm(y_mm)),
                        "photo": None,
                        "pil": None,
                        "border_id": None,
                    }
                    photo = self._render_photo(meta, max(1, int(w_px)), max(1, int(h_px)))
                    if photo is not None:
                        img_id = self.canvas.create_image(left, top, image=photo, anchor="nw")
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
            self._select(None)
        except Exception:
            pass
        # Save current scene under current side
        try:
            self._scene_store[self._current_side] = self._serialize_scene()
        except Exception:
            pass
        # Switch side based on checkbox
        self._current_side = "back" if self.backside.get() else "front"
        # Clear and restore the target scene
        self._clear_scene()
        data = self._scene_store.get(self._current_side) or []
        if data:
            self._restore_scene(data)
        # Keep jig in place without recentering
        self._redraw_jig(center=False)
        # Ensure labels on top after switching sides
        self._raise_all_labels()