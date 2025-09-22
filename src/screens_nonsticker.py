from typing import Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core import Screen, vcmd_float, mm_to_px
from state import state, MM_TO_PX

# ---- tiny helper: write a minimal PDF so Download has content ----
def _write_minimal_pdf(path: str):
    pdf = b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 24 Tf 72 720 Td (Zyntra Test File) Tj ET
endstream
endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000015 00000 n 
0000000062 00000 n 
0000000119 00000 n 
0000000263 00000 n 
0000000404 00000 n 
trailer<</Root 1 0 R /Size 6>>
startxref
517
%%EOF
"""
    with open(path, "wb") as f:
        f.write(pdf)


class NScreen2(Screen):
    """Non-sticker designer: SKU, jig, import, place, size."""
    def __init__(self, master, app):
        super().__init__(master, app)

        header = ttk.Frame(self, style="Screen.TFrame")
        header.pack(fill="x", pady=(10, 6))
        ttk.Label(header, text="Write Name for sku", style="H1.TLabel").pack(side="left", padx=(10, 8))
        self.sku_var = tk.StringVar(value=state.sku or "Carmirror134")
        ttk.Entry(header, textvariable=self.sku_var, width=28).pack(side="left")

        bar = tk.Frame(self, bg="black")
        bar.pack(fill="x", padx=10, pady=(6, 10))

        self.btn_import_vec = ttk.Button(bar, text=f"Import Vector\n{self.sku_var.get()}", command=self._import_vector)
        self.btn_import_vec.pack(side="left", padx=8, pady=8)
        self.sku_var.trace_add("write", lambda *_: self.btn_import_vec.configure(text=f"Import Vector\n{self.sku_var.get()}"))

        tk.Label(bar, text="Jig size:", fg="white", bg="black", font=("Arial", 12, "bold")).pack(side="left", padx=(16, 6))
        self.jig_x = tk.StringVar(value=state.pkg_x or "296")
        self.jig_y = tk.StringVar(value=state.pkg_y or "415")
        self._chip(bar, "X:", self.jig_x)
        self._chip(bar, "Y:", self.jig_y)

        tk.Frame(bar, bg="black").pack(side="left", padx=16)
        tools = tk.Frame(bar, bg="black")
        tools.pack(side="left")
        ttk.Button(tools, text="Select tool", command=lambda: self._set_tool("select")).pack(side="left", padx=6, pady=6)
        ttk.Button(tools, text="Ai arrange", command=self._ai_arrange).pack(side="left", padx=6, pady=6)
        ttk.Button(tools, text="T", width=3, command=self._drop_text).pack(side="left", padx=6, pady=6)
        self.current_tool = "select"

        right = tk.Frame(bar, bg="black")
        right.pack(side="right", padx=10)
        tk.Label(right, text="Backside", fg="white", bg="black", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 6))
        self.backside = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, variable=self.backside).pack(side="left", pady=8)

        row2 = ttk.Frame(self, style="Card.TFrame", padding=8)
        row2.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Label(row2, text="Size:", style="H3.TLabel").pack(side="left", padx=(2, 8))
        self.sel_w = tk.StringVar(value="59")
        self.sel_h = tk.StringVar(value="80")
        self._mini_chip(row2, "X:", self.sel_w)
        self._mini_chip(row2, "Y:", self.sel_h)
        ttk.Button(row2, text="Apply to selection", command=self._apply_size_to_selection).pack(side="left", padx=(8, 16))
        ttk.Label(row2, text="Import:", style="H3.TLabel").pack(side="left", padx=(2, 8))
        for fmt in ("Png", "Jpg", "Svg"):
            ttk.Button(row2, text=fmt, command=lambda f=fmt: self._import_placeholder(f)).pack(side="left", padx=4)

        board = ttk.Frame(self, style="Card.TFrame", padding=10)
        board.pack(expand=True, fill="both", padx=10, pady=10)
        self.canvas = tk.Canvas(board, bg="#5a5a5a", highlightthickness=2, highlightbackground="#2a2a2a")
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<Configure>", self._redraw_jig)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self._items: dict[int, dict] = {}   # canvas_id -> meta
        self._selected: Optional[int] = None
        self._drag_off: Tuple[int, int] = (0, 0)

        # Навигация: назад — к первому экрану с выбором типа (Screen1) в sticker-пакете.
        def _back():
            from screens_sticker import Screen1  # локальный импорт, чтобы избежать циклических зависимостей
            self.app.show_screen(Screen1)

        self.bottom_nav(self, on_back=_back, on_next=self._proceed, next_text="Proceed!")

    # UI helpers
    def _chip(self, parent, label, var):
        box = tk.Frame(parent, bg="#6f6f6f")
        box.pack(side="left", padx=6, pady=8)
        tk.Label(box, text=label, bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(box, textvariable=var, width=8, bg="#d9d9d9",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=6)

    def _mini_chip(self, parent, label, var):
        box = tk.Frame(parent, bg="#c7c7c7")
        box.pack(side="left", padx=4)
        tk.Label(box, text=label, bg="#c7c7c7").pack(side="left", padx=(6, 2))
        tk.Entry(box, textvariable=var, width=6,
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=(2, 6))

    # Actions
    def _set_tool(self, name):
        self.current_tool = name

    def _import_vector(self):
        filedialog.askopenfilename(title="Import Vector",
                                   filetypes=[("Vector", "*.svg *.pdf *.ai"), ("All files", "*.*")])
        self._create_placeholder(self.sku_var.get(), 40, 60)

    def _import_placeholder(self, fmt):
        filedialog.askopenfilename(title=f"Import {fmt}",
                                   filetypes=[(fmt, f"*.{fmt.lower()}"), ("All files", "*.*")])
        self._create_placeholder(f"{fmt} item", 40, 50)

    def _create_placeholder(self, label, w_mm, h_mm):
        cx = max(1, self.canvas.winfo_width() // 2)
        cy = max(1, self.canvas.winfo_height() // 2)
        w = mm_to_px(w_mm)
        h = mm_to_px(h_mm)
        rect = self.canvas.create_rectangle(
            cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2,
            fill="#2b2b2b", outline="#d0d0d0", width=2
        )
        txt = self.canvas.create_text(cx, cy, text=label, fill="white", font=("Arial", 10))
        self._items[rect] = {"type": "rect", "w_mm": w_mm, "h_mm": h_mm, "label_id": txt}
        self._select(rect)

    def _drop_text(self):
        cx = self.canvas.winfo_width() // 2
        cy = self.canvas.winfo_height() // 2
        tid = self.canvas.create_text(cx, cy, text="Text", fill="white", font=("Arial", 12, "bold"))
        self._items[tid] = {"type": "text"}
        self._select(tid)

    def _ai_arrange(self):
        pads = 8
        x0, y0, x1, y1 = self._jig_rect_px()
        x, y = x0 + pads, y0 + pads
        row_h = 0
        max_w = x1 - x0 - 2 * pads
        for cid, meta in self._items.items():
            if meta["type"] != "rect":
                continue
            w = int(meta["w_mm"] * MM_TO_PX)
            h = int(meta["h_mm"] * MM_TO_PX)
            if x + w > x0 + max_w:
                x = x0 + pads
                y += row_h + pads
                row_h = 0
            self.canvas.coords(cid, x, y, x + w, y + h)
            self.canvas.coords(meta["label_id"], x + w / 2, y + h / 2)
            row_h = max(row_h, h)
            x += w + pads

    # Selection/drag
    def _on_click(self, e):
        hit = self.canvas.find_withtag("current")
        if hit:
            self._select(hit[0])
            x1, y1, x2, y2 = self.canvas.bbox(self._selected)
            self._drag_off = (e.x - x1, e.y - y1)
        else:
            self._select(None)

    def _on_drag(self, e):
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        x1 = e.x - self._drag_off[0]
        y1 = e.y - self._drag_off[1]
        bx = self.canvas.bbox(self._selected)
        w = bx[2] - bx[0]
        h = bx[3] - bx[1]
        self.canvas.coords(self._selected, x1, y1, x1 + w, y1 + h)
        if meta.get("label_id"):
            self.canvas.coords(meta["label_id"], x1 + w / 2, y1 + h / 2)

    def _on_release(self, _):
        pass

    def _select(self, cid: Optional[int]):
        if getattr(self, "_selected", None) and self._selected in self._items:
            self.canvas.itemconfig(self._selected, outline="#d0d0d0", width=2)
        self._selected = cid
        if not cid:
            return
        self.canvas.itemconfig(cid, outline="#6ec8ff", width=3)
        meta = self._items.get(cid, {})
        if meta.get("type") == "rect":
            self.sel_w.set(str(meta["w_mm"]))
            self.sel_h.set(str(meta["h_mm"]))

    def _apply_size_to_selection(self):
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        if meta.get("type") != "rect":
            return
        try:
            w_mm = float(self.sel_w.get())
            h_mm = float(self.sel_h.get())
        except ValueError:
            messagebox.showerror("Invalid size", "Enter numeric X/Y (mm).")
            return
        meta["w_mm"] = w_mm
        meta["h_mm"] = h_mm
        x1, y1, x2, y2 = self.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = int(w_mm * MM_TO_PX)
        h = int(h_mm * MM_TO_PX)
        self.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if meta.get("label_id"):
            self.canvas.coords(meta["label_id"], cx, cy)

    def _redraw_jig(self, _evt=None):
        self.canvas.delete("jig")
        try:
            jx = float(self.jig_x.get())
            jy = float(self.jig_y.get())
        except ValueError:
            jx, jy = 296, 415
        w = int(jx * MM_TO_PX)
        h = int(jy * MM_TO_PX)
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        scale = min((cw - 40) / max(w, 1), (ch - 40) / max(h, 1), 1.0)
        self._jig_draw_w = int(w * scale)
        self._jig_draw_h = int(h * scale)
        x0 = (cw - self._jig_draw_w) // 2
        y0 = (ch - self._jig_draw_h) // 2
        x1 = x0 + self._jig_draw_w
        y1 = y0 + self._jig_draw_h
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#dddddd", width=3, tags="jig")

    def _jig_rect_px(self):
        objs = self.canvas.find_withtag("jig")
        if not objs:
            return (20, 20, self.canvas.winfo_width() - 20, self.canvas.winfo_height() - 20)
        return self.canvas.bbox(objs[0])

    def _proceed(self):
        # Сохраняем актуальные значения перед переходом
        state.sku = self.sku_var.get().strip()
        state.pkg_x = self.jig_x.get().strip()
        state.pkg_y = self.jig_y.get().strip()
        self.app.show_screen(NScreen4)


class NScreen4(Screen):
    """Non-sticker success + download."""
    def __init__(self, master, app):
        super().__init__(master, app)

        wrap = ttk.Frame(self, style="Screen.TFrame")
        wrap.pack(expand=True, fill="both", padx=20, pady=20)

        ttk.Label(wrap, text="Product Added Successfully", style="H1.TLabel").pack(pady=(10, 16))

        chk = tk.Canvas(wrap, width=180, height=180, bg="#4d4d4d", highlightthickness=0)
        chk.pack(pady=(0, 12))
        r = 80
        cx, cy = 90, 90
        chk.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#17a24b", width=10)
        chk.create_line(55, 95, 85, 120, fill="#17a24b", width=12, capstyle="round")
        chk.create_line(85, 120, 140, 60, fill="#17a24b", width=12, capstyle="round")

        product_name = state.saved_product if state.saved_product else "Product"
        ttk.Label(wrap, text=f"Sku {product_name}", style="H1.TLabel").pack(pady=(6, 0))
        ttk.Label(wrap, text=(state.sku or "—"), style="H1.TLabel").pack(pady=(0, 16))

        row = ttk.Frame(wrap, style="Screen.TFrame")
        row.pack(pady=(8, 0))
        chip = ttk.Frame(row, style="Card.TFrame", padding=10)
        chip.pack(side="left")
        ttk.Label(chip, text="Test File .pdf", style="H2.TLabel").pack()
        ttk.Button(row, text="Download", command=self._download).pack(side="left", padx=14)

        def _back():
            self.app.show_screen(NScreen2)

        self.bottom_nav(self, on_back=_back, on_next=self.app.quit_app, next_text="Done")

    def _download(self):
        fname = filedialog.asksaveasfilename(
            title="Save Test File",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not fname:
            return
        try:
            _write_minimal_pdf(fname)
            messagebox.showinfo("Saved", f"File saved to:\n{fname}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")