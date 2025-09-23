from typing import Optional, Tuple
import os
from pathlib import Path
import re
import struct

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.core import Screen, vcmd_float, mm_to_px, COLOR_TEXT
from src.state import state, MM_TO_PX, IMAGES_PATH

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


class NStickerPlanScreen(Screen):
    """Non-sticker designer: SKU, jig, import, place, size."""
    def __init__(self, master, app):
        super().__init__(master, app)

        # App title + left-aligned header row with SKU input
        self.brand_bar(self)
        header_row = ttk.Frame(self, style="Screen.TFrame")
        header_row.pack(padx=0, pady=(25, 25))
        tk.Label(header_row, text=" Write Name for sku ", bg="#737373", fg=COLOR_TEXT,
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

        self.btn_import_vec = ttk.Button(bar, text=f"Import Vector\n{self.sku_var.get()}", command=self._import_vector)
        self.btn_import_vec.pack(side="left", padx=8, pady=8)
        self.sku_var.trace_add("write", lambda *_: self.btn_import_vec.configure(text=f"Import Vector\n{self.sku_var.get()}"))

        tk.Label(bar, text="Jig size:", fg="white", bg="black", font=("Myriad Pro", 20, "bold")).pack(side="left", padx=(16, 6))
        self.jig_x = tk.StringVar(value=state.pkg_x or "296")
        self.jig_y = tk.StringVar(value=state.pkg_y or "415")
        self._chip(bar, "X:", self.jig_x)
        self._chip(bar, "Y:", self.jig_y)
        # live redraw when jig size changes
        self.jig_x.trace_add("write", lambda *_: self._redraw_jig())
        self.jig_y.trace_add("write", lambda *_: self._redraw_jig())

        tk.Frame(bar, bg="black").pack(side="left", padx=16)
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
            command=lambda: self._set_tool("select"),
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
        self.current_tool = "select"

        row2 = tk.Frame(self, bg="black")
        row2.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(row2, text="Size:", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(2, 8))
        self.sel_w = tk.StringVar(value="59")
        self.sel_h = tk.StringVar(value="80")
        self._chip(row2, "X:", self.sel_w, width=8)
        self._chip(row2, "Y:", self.sel_h, width=8)
        # live scale selection on size change
        self.sel_w.trace_add("write", self._on_size_change)
        self.sel_h.trace_add("write", self._on_size_change)
        # removed Apply button; live updates handle both selection and jig
        tk.Label(row2, text="Import:", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(2, 8))
        for fmt in ("Png", "Jpg", "Svg"):
            ttk.Button(row2, text=fmt, command=lambda f=fmt: self._import_placeholder(f)).pack(side="left", padx=4)

        
        right = tk.Frame(row2, bg="black")
        right.pack(side="right", padx=10)
        tk.Label(right, text="Backside", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="left", padx=(0, 6))
        self.backside = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, variable=self.backside).pack(side="left", pady=8)

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
        self._zoom: float = 1.0

        # Key bindings for zoom in/out
        for seq in ("<KeyPress-+>", "<KeyPress-equal>", "<KP_Add>"):
            self.app.bind(seq, lambda _e: self._zoom_step(1))
        for seq in ("<KeyPress-minus>", "<KP_Subtract>"):
            self.app.bind(seq, lambda _e: self._zoom_step(-1))

        # Навигация: назад — к предыдущему экрану по истории.
        self.bottom_nav(self, on_back=self.app.go_back, on_next=self._proceed, next_text="Proceed!")

    # UI helpers
    def _chip(self, parent, label, var, width=8):
        box = tk.Frame(parent, bg="#6f6f6f")
        box.pack(side="left", padx=6, pady=8)
        tk.Label(box, text=label, bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        tk.Entry(box, textvariable=var, width=width, bg="#d9d9d9", justify="center",
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left")

    def _mini_chip(self, parent, label, var):
        box = tk.Frame(parent, bg="#c7c7c7")
        box.pack(side="left", padx=4)
        tk.Label(box, text=label, bg="#c7c7c7").pack(side="left", padx=(6, 2))
        tk.Entry(box, textvariable=var, width=6,
                 validate="key", validatecommand=(vcmd_float(self), "%P")).pack(side="left", padx=(2, 6))

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
    def _set_tool(self, name):
        self.current_tool = name

    def _import_vector(self):
        path = filedialog.askopenfilename(title="Import Vector",
                                          filetypes=[("Vector", "*.svg *.pdf *.ai"), ("All files", "*.*")])
        if not path or not os.path.exists(path):
            return
        label = os.path.basename(path)
        size = self._compute_import_size_mm(path)
        if size is None:
            try:
                size = (float(self.sel_w.get()), float(self.sel_h.get()))
            except Exception:
                size = (40.0, 60.0)
        w_mm, h_mm = self._fit_to_jig_bounds(*size)
        self._create_placeholder(label, w_mm, h_mm)

    def _import_placeholder(self, fmt):
        path = filedialog.askopenfilename(title=f"Import {fmt}",
                                   filetypes=[(fmt, f"*.{fmt.lower()}"), ("All files", "*.*")])
        if not path or not os.path.exists(path):
            return
        label = os.path.basename(path)
        size = self._compute_import_size_mm(path)
        if size is None:
            try:
                size = (float(self.sel_w.get()), float(self.sel_h.get()))
            except Exception:
                size = (40.0, 50.0)
        # Only scale down to fit jig, never up
        # w_mm, h_mm = self._fit_to_jig_bounds(*size)
        self._create_placeholder(label, size[0], size[1])

    def _create_placeholder(self, label, w_mm, h_mm):
        # place at the center of jig when available
        x0, y0, x1, y1 = self._jig_rect_px()
        cx = max(1, int((x0 + x1) / 2))
        cy = max(1, int((y0 + y1) / 2))
        w = int(mm_to_px(w_mm) * self._zoom)
        h = int(mm_to_px(h_mm) * self._zoom)
        rect = self.canvas.create_rectangle(
            cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2,
            fill="#2b2b2b", outline="#d0d0d0", width=2
        )
        txt = self.canvas.create_text(cx, cy, text=label, fill="white", font=("Myriad Pro", 10))
        self._items[rect] = {"type": "rect", "w_mm": float(w_mm), "h_mm": float(h_mm), "label_id": txt}
        self._select(rect)
        self._update_scrollregion()

    def _drop_text(self):
        cx = self.canvas.winfo_width() // 2
        cy = self.canvas.winfo_height() // 2
        tid = self.canvas.create_text(cx, cy, text="Text", fill="white", font=("Myriad Pro", 12, "bold"))
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
            w = int(meta["w_mm"] * MM_TO_PX * self._zoom)
            h = int(meta["h_mm"] * MM_TO_PX * self._zoom)
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
            if meta.get("type") == "rect":
                x1, y1, x2, y2 = self.canvas.bbox(target)
                self._drag_off = (e.x - x1, e.y - y1)
                rx1, ry1, rx2, ry2 = self.canvas.coords(target)
                self._drag_size = (rx2 - rx1, ry2 - ry1)
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
            w, h = self._drag_size
            self.canvas.coords(self._selected, x1, y1, x1 + w, y1 + h)
            if meta.get("label_id"):
                self.canvas.coords(meta["label_id"], x1 + w / 2, y1 + h / 2)
        elif self._drag_kind == "text":
            cx = e.x - self._drag_off[0]
            cy = e.y - self._drag_off[1]
            self.canvas.coords(self._selected, cx, cy)

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

    def _select(self, cid: Optional[int]):
        if getattr(self, "_selected", None) and self._selected in self._items:
            prev_meta = self._items.get(self._selected, {})
            if prev_meta.get("type") == "rect":
                self.canvas.itemconfig(self._selected, outline="#d0d0d0", width=2)
        self._selected = cid
        if not cid:
            return
        meta = self._items.get(cid, {})
        if meta.get("type") == "rect":
            self.canvas.itemconfig(cid, outline="#6ec8ff", width=3)
            # set fields without triggering live resize
            try:
                self._suppress_size_trace = True
                self.sel_w.set(str(meta["w_mm"]))
                self.sel_h.set(str(meta["h_mm"]))
            finally:
                self._suppress_size_trace = False

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
        w = int(w_mm * MM_TO_PX * self._zoom)
        h = int(h_mm * MM_TO_PX * self._zoom)
        self.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if meta.get("label_id"):
            self.canvas.coords(meta["label_id"], cx, cy)
        self._update_scrollregion()

    def _on_size_change(self, *_):
        # live update selection size while typing, best-effort
        if self._suppress_size_trace:
            return
        if not self._selected:
            return
        meta = self._items.get(self._selected, {})
        if meta.get("type") != "rect":
            return
        try:
            w_mm = float(self.sel_w.get())
            h_mm = float(self.sel_h.get())
        except ValueError:
            return
        meta["w_mm"] = w_mm
        meta["h_mm"] = h_mm
        x1, y1, x2, y2 = self.canvas.bbox(self._selected)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = int(w_mm * MM_TO_PX * self._zoom)
        h = int(h_mm * MM_TO_PX * self._zoom)
        self.canvas.coords(self._selected, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if meta.get("label_id"):
            self.canvas.coords(meta["label_id"], cx, cy)
        self._update_scrollregion()

    def _redraw_jig(self, _evt=None, center=True):
        self.canvas.delete("jig")
        try:
            jx = float(self.jig_x.get())
            jy = float(self.jig_y.get())
        except ValueError:
            jx, jy = 296, 415
        w = int(jx * MM_TO_PX * self._zoom)
        h = int(jy * MM_TO_PX * self._zoom)
        pad = 20
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        # Center jig when it fits; otherwise anchor with padding and allow scroll
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

    def _jig_rect_px(self):
        objs = self.canvas.find_withtag("jig")
        if not objs:
            return (20, 20, self.canvas.winfo_width() - 20, self.canvas.winfo_height() - 20)
        return self.canvas.bbox(objs[0])

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
        right = max(cw, x1 + pad)
        bottom = max(ch, y1 + pad)
        self.canvas.configure(scrollregion=(0, 0, right, bottom))

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

    def _fit_to_jig_bounds(self, w_mm: float, h_mm: float, pad_mm: float = 4.0) -> Tuple[float, float]:
        """Scale (w_mm,h_mm) to fit inside the jig while preserving aspect.
        - Only scales DOWN if the item exceeds jig bounds; never scales up.
        - Applies inner padding pad_mm on all sides.
        """
        try:
            jig_w = float(self.jig_x.get())
            jig_h = float(self.jig_y.get())
        except Exception:
            jig_w, jig_h = 296.0, 415.0
        inner_w = max(1.0, jig_w - 2 * pad_mm)
        inner_h = max(1.0, jig_h - 2 * pad_mm)
        if h_mm <= 0 or w_mm <= 0:
            return min(inner_w, 10.0), min(inner_h, 10.0)
        # Compute scale to fit within both width and height, but don't upscale
        scale_w = inner_w / w_mm
        scale_h = inner_h / h_mm
        scale = min(1.0, scale_w, scale_h)
        new_w = w_mm * scale
        new_h = h_mm * scale
        return (new_w, new_h)

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
            jx, jy = 210.0, 297.0
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
        self.app.show_screen(NScreen4)

    def _zoom_step(self, direction: int):
        # direction: +1 zoom in, -1 zoom out
        old = self._zoom
        if direction > 0:
            self._zoom = min(5.0, self._zoom * 1.1)
        else:
            self._zoom = max(0.2, self._zoom / 1.1)
        if abs(self._zoom - old) < 1e-3:
            return
        # Preserve current viewport center in canvas coordinates
        try:
            x0 = self.canvas.canvasx(0)
            y0 = self.canvas.canvasy(0)
            x1 = self.canvas.canvasx(self.canvas.winfo_width())
            y1 = self.canvas.canvasy(self.canvas.winfo_height())
            view_cx = (x0 + x1) / 2
            view_cy = (y0 + y1) / 2
        except Exception:
            view_cx = view_cy = None
        # Redraw jig and rescale all items around their centers
        self._redraw_jig(center=False)
        for cid, meta in list(self._items.items()):
            if meta.get("type") != "rect":
                continue
            # current center
            x1, y1, x2, y2 = self.canvas.bbox(cid)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            w = int(meta["w_mm"] * MM_TO_PX * self._zoom)
            h = int(meta["h_mm"] * MM_TO_PX * self._zoom)
            self.canvas.coords(cid, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if meta.get("label_id"):
                self.canvas.coords(meta["label_id"], cx, cy)
        self._update_scrollregion()
        # Restore viewport center after zoom change
        if view_cx is not None and view_cy is not None:
            sr = self.canvas.cget("scrollregion")
            try:
                sx0, sy0, sx1, sy1 = [float(v) for v in str(sr).split()]
                cw = max(1, self.canvas.winfo_width())
                ch = max(1, self.canvas.winfo_height())
                total_w = max(1.0, sx1 - sx0)
                total_h = max(1.0, sy1 - sy0)
                target_x = max(sx0, min(view_cx - cw / 2, sx1 - cw))
                target_y = max(sy0, min(view_cy - ch / 2, sy1 - ch))
                if total_w > cw:
                    self.canvas.xview_moveto((target_x - sx0) / (total_w - cw))
                if total_h > ch:
                    self.canvas.yview_moveto((target_y - sy0) / (total_h - ch))
            except Exception:
                pass


class NScreen4(Screen):
    """Non-sticker success + download."""
    def __init__(self, master, app):
        super().__init__(master, app)

        # App title + screen title
        self.header(self, "Product Added Successfully")

        wrap = ttk.Frame(self, style="Screen.TFrame")
        wrap.pack(expand=True, fill="both", padx=20, pady=20)

        # keep main success header within wrap for spacing consistency
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

        self.bottom_nav(self, on_back=self.app.go_back, on_next=self.app.quit_app, next_text="Done")

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