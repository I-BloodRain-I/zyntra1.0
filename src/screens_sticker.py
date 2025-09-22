import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core import Screen, vcmd_int, vcmd_float, warn
from state import state


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


# ================================================
# Screen 1 — выбор типа продукта (стикер / нет)
# ================================================
class Screen1(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Add a new product")

        card = ttk.Frame(self, style="Card.TFrame", padding=20)
        card.pack(pady=30)
        ttk.Label(card, text="Is your product a sticker/Flex?", style="H2.TLabel").pack(pady=(0, 16))

        default = "yes" if state.is_sticker else ("no" if state.is_sticker is False else "")
        self.choice = tk.StringVar(value=default)

        btns = ttk.Frame(card)
        btns.pack()
        ttk.Radiobutton(btns, text="Yes", value="yes", variable=self.choice, style="Choice.TRadiobutton").grid(row=0, column=0, padx=8, pady=8)
        ttk.Radiobutton(btns, text="No",  value="no",  variable=self.choice, style="Choice.TRadiobutton").grid(row=0, column=1, padx=8, pady=8)

        self.bottom_nav(self, on_back=self.app.quit_app, on_next=self.next)

    def next(self):
        val = self.choice.get()
        if val not in ("yes", "no"):
            messagebox.showwarning("Select an option", "Please choose Yes or No.")
            return
        state.is_sticker = (val == "yes")
        if state.is_sticker:
            self.app.show_screen(Screen2)     # Sticker flow
        else:
            # Локальный импорт, чтобы избежать циклов
            from screens_nonsticker import NScreen2
            self.app.show_screen(NScreen2)    # Non-sticker flow


# ================================================
# Screen 2 — SKU, package size, major variations
# ================================================
class Screen2(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Add a new product")

        form = ttk.Frame(self, style="Screen.TFrame")
        form.pack(pady=10)

        # SKU
        row1 = ttk.Frame(form, padding=(0, 6))
        row1.pack(fill="x")
        ttk.Label(row1, text="Give your SKU number:", style="Label.TLabel").pack(side="left")
        self.sku_var = tk.StringVar(value=state.sku or "1324-2342-5433")
        ttk.Entry(row1, textvariable=self.sku_var, width=22).pack(side="left", padx=10)

        # Package size
        pack_card = ttk.Frame(form, style="Card.TFrame", padding=14)
        pack_card.pack(pady=10, fill="x")
        ttk.Label(pack_card, text="Your package size:", style="H2.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.pkgx = tk.StringVar(value=state.pkg_x or "80")
        self.pkgy = tk.StringVar(value=state.pkg_y or "80")
        ttk.Label(pack_card, text="X (mm):").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Entry(pack_card, textvariable=self.pkgx, width=8,
                  validate="key", validatecommand=(vcmd_float(self), "%P")).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(pack_card, text="Y (mm):").grid(row=1, column=2, sticky="e", padx=4)
        ttk.Entry(pack_card, textvariable=self.pkgy, width=8,
                  validate="key", validatecommand=(vcmd_float(self), "%P")).grid(row=1, column=3, sticky="w", padx=4)

        # Major variations
        var_card = ttk.Frame(form, style="Card.TFrame", padding=14)
        var_card.pack(pady=10, fill="x")
        ttk.Label(var_card, text="Number of size (major) variations:", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        self.major_count = tk.IntVar(value=state.major_variations or 3)
        spin = ttk.Spinbox(var_card, from_=1, to=50, width=5, textvariable=self.major_count,
                            validate="key", validatecommand=(vcmd_int(self), "%P"),
                            command=self._rebuild_variation_rows)
        spin.grid(row=0, column=1, padx=8)

        # Per-variation design counts
        self.variations_frame = ttk.Frame(var_card)
        self.variations_frame.grid(row=1, column=0, columnspan=3, pady=(12, 0), sticky="w")
        self.design_vars: list[tk.IntVar] = []
        self._rebuild_variation_rows()

        # Total fonts variations
        fonts_card = ttk.Frame(form, style="Card.TFrame", padding=14)
        fonts_card.pack(pady=10, fill="x")
        ttk.Label(fonts_card, text="Total fonts Variations:", style="H2.TLabel").pack(side="left")
        self.font_total = tk.IntVar(value=state.font_variations_total or 7)
        ttk.Spinbox(fonts_card, from_=1, to=200, textvariable=self.font_total, width=6,
                    validate="key", validatecommand=(vcmd_int(self), "%P")).pack(side="left", padx=10)

        self.bottom_nav(self, on_back=lambda: self.app.show_screen(Screen1), on_next=self.next)

    def _rebuild_variation_rows(self):
        for w in self.variations_frame.winfo_children():
            w.destroy()
        self.design_vars.clear()
        n = int(self.major_count.get() or 0)
        preset = state.variation_design_counts or [4] * n
        for i in range(n):
            row = ttk.Frame(self.variations_frame)
            row.pack(anchor="w", pady=4)
            ttk.Label(row, text=f"Variation {i+1} Designs total:", style="Label.TLabel").pack(side="left")
            var = tk.IntVar(value=preset[i] if i < len(preset) else 4)
            ttk.Spinbox(row, from_=0, to=999, textvariable=var, width=6,
                        validate="key", validatecommand=(vcmd_int(self), "%P")).pack(side="left", padx=8)
            self.design_vars.append(var)

    def next(self):
        try:
            int(self.pkgx.get()); int(self.pkgy.get())
        except ValueError:
            warn("Package size X/Y must be numbers (mm).", title="Numbers only")
            return

        state.sku = self.sku_var.get().strip()
        state.pkg_x = self.pkgx.get().strip()
        state.pkg_y = self.pkgy.get().strip()
        state.major_variations = int(self.major_count.get())
        state.variation_design_counts = [int(v.get()) for v in self.design_vars]
        state.font_variations_total = int(self.font_total.get())

        state.font_names = ["" for _ in range(state.font_variations_total)]
        state.font_uploaded = [False for _ in range(state.font_variations_total)]

        self.app.show_screen(Screen3)


# ================================================
# Screen 3 — загрузка шрифтов
# ================================================
class Screen3(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Upload all fonts")

        self.rows = ttk.Frame(self, style="Screen.TFrame")
        self.rows.pack(pady=8)

        self.name_vars: list[tk.StringVar] = []
        self.upload_labels: list[ttk.Label] = []

        self._build_rows()
        self.bottom_nav(self, on_back=lambda: self.app.show_screen(Screen2), on_next=self.next)

    def _upload(self, idx):
        state.font_uploaded[idx] = True
        self.upload_labels[idx].configure(text="✔ Uploaded")
        state.font_names[idx] = self.name_vars[idx].get().strip()

    def _build_rows(self):
        for w in self.rows.winfo_children():
            w.destroy()
        self.name_vars.clear()
        self.upload_labels.clear()

        total = state.font_variations_total
        for i in range(total):
            card = ttk.Frame(self.rows, style="Card.TFrame", padding=10)
            card.pack(fill="x", padx=10, pady=6)
            ttk.Label(card, text=f"Font {i+1}", width=10).grid(row=0, column=0, sticky="w", padx=(4, 8))
            ttk.Label(card, text="Name (Same as Amazon)").grid(row=0, column=1, sticky="w")
            var = tk.StringVar(value=state.font_names[i] if i < len(state.font_names) else "")
            ttk.Entry(card, textvariable=var, width=28).grid(row=0, column=2, padx=8)
            self.name_vars.append(var)

            ttk.Button(card, text="Upload", command=lambda k=i: self._upload(k)).grid(row=0, column=3, padx=8)
            status = ttk.Label(card, text="• Pending", style="Muted.TLabel")
            status.grid(row=0, column=4, padx=8)
            self.upload_labels.append(status)

            if i < len(state.font_uploaded) and state.font_uploaded[i]:
                status.configure(text="✔ Uploaded")

    def next(self):
        if not all(state.font_uploaded):
            missing = [str(i + 1) for i, ok in enumerate(state.font_uploaded) if not ok]
            messagebox.showwarning("Upload required", f"Please upload all fonts: {', '.join(missing)}")
            return
        self.app.show_screen(Screen4)


# ================================================
# Screen 4 — размеры major-вариаций
# ================================================
class Screen4(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Sizes for major variations")

        self.rows = ttk.Frame(self, style="Screen.TFrame")
        self.rows.pack(pady=8)

        self.x_vars: list[tk.StringVar] = []
        self.y_vars: list[tk.StringVar] = []
        self.vector_labels: list[ttk.Label] = []

        self._build_rows()
        self.bottom_nav(self, on_back=lambda: self.app.show_screen(Screen3), on_next=self.next)

    def _import_vec(self, idx):
        # здесь могла бы быть логика открытия файла
        self.vector_labels[idx].configure(text="✔ Vector attached")

    def _build_rows(self):
        for w in self.rows.winfo_children():
            w.destroy()
        self.x_vars.clear(); self.y_vars.clear(); self.vector_labels.clear()

        n = state.major_variations
        if len(state.major_sizes) < n:
            state.major_sizes += [("", "") for _ in range(n - len(state.major_sizes))]

        for i in range(n):
            card = ttk.Frame(self.rows, style="Card.TFrame", padding=10)
            card.pack(fill="x", padx=10, pady=6)
            ttk.Label(card, text=f"Size {i+1}", width=10).grid(row=0, column=0, padx=6)
            x0, y0 = state.major_sizes[i]
            xv = tk.StringVar(value=x0 or "5")
            yv = tk.StringVar(value=y0 or "5")
            ttk.Label(card, text="X (mm):").grid(row=0, column=1, sticky="e")
            ttk.Entry(card, textvariable=xv, width=8, validate="key",
                      validatecommand=(vcmd_float(self), "%P")).grid(row=0, column=2, padx=6)
            ttk.Label(card, text="Y (mm):").grid(row=0, column=3, sticky="e")
            ttk.Entry(card, textvariable=yv, width=8, validate="key",
                      validatecommand=(vcmd_float(self), "%P")).grid(row=0, column=4, padx=6)
            ttk.Button(card, text="Import vector", command=lambda k=i: self._import_vec(k)).grid(row=0, column=5, padx=10)
            lab = ttk.Label(card, text="• Pending", style="Muted.TLabel")
            lab.grid(row=0, column=6, padx=6)
            self.x_vars.append(xv); self.y_vars.append(yv); self.vector_labels.append(lab)

    def next(self):
        state.major_sizes = [(x.get().strip(), y.get().strip()) for x, y in zip(self.x_vars, self.y_vars)]
        self.app.show_screen(Screen5)


# ================================================
# Screen 5 — холст/превью и опции (DTS/DIS и пр.)
# ================================================
class Screen5(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Add a new product")

        top = ttk.Frame(self, style="Screen.TFrame")
        top.pack(pady=8, fill="x")

        size_card = ttk.Frame(top, style="Card.TFrame", padding=10)
        size_card.pack(side="left", padx=10)
        ttk.Label(size_card, text=f"Size 1", style="H3.TLabel").grid(row=0, column=0, columnspan=4, pady=(0, 6))
        ttk.Label(size_card, text="X (mm):").grid(row=1, column=0, sticky="e")
        ttk.Entry(size_card, width=8).grid(row=1, column=1, padx=6)
        ttk.Label(size_card, text="Y (mm):").grid(row=1, column=2, sticky="e")
        ttk.Entry(size_card, width=8).grid(row=1, column=3, padx=6)

        rc_card = ttk.Frame(top, style="Card.TFrame", padding=10)
        rc_card.pack(side="left", padx=10)
        ttk.Label(rc_card, text="Rounded corners", style="H3.TLabel").grid(row=0, column=0, columnspan=2)
        ttk.Label(rc_card, text="Units:").grid(row=1, column=0, sticky="e")
        ttk.Entry(rc_card, width=6).grid(row=1, column=1, padx=6)

        col_card = ttk.Frame(self, style="Card.TFrame", padding=10)
        col_card.pack(pady=10, fill="x", padx=10)
        ttk.Label(col_card, text="Background color CMYK code", style="H3.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(col_card, width=24)
        ttk.Entry(col_card, width=24).grid(row=0, column=1, padx=8)

        import_row = ttk.Frame(self, style="Screen.TFrame")
        import_row.pack(fill="x", pady=8)
        ttk.Label(import_row, text="Import:", style="H3.TLabel").pack(side="left", padx=(10, 8))
        for fmt in ("Png", "Jpg", "Svg"):
            ttk.Button(import_row, text=fmt).pack(side="left", padx=6)
        right = ttk.Frame(import_row)
        right.pack(side="right", padx=10)
        self.dts = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="DTS", variable=self.dts).pack(side="left", padx=6)
        self.dis = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="DIS", variable=self.dis).pack(side="left", padx=6)

        canvas_card = ttk.Frame(self, style="Card.TFrame", padding=20)
        canvas_card.pack(expand=True, fill="both", padx=10, pady=10)
        ttk.Label(canvas_card, text="(Artwork preview)\nDefine text space →", style="Muted.TLabel").pack(expand=True)

        self.bottom_nav(self,
                        on_back=lambda: self.app.show_screen(Screen4),
                        on_next=lambda: self.app.show_screen(Screen6),
                        next_text="Proceed!")


# ================================================
# Screen 6 — подсчёты листов, per-major и AI arrange
# ================================================
class Screen6(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Add a new product")

        wrap = ttk.Frame(self, style="Screen.TFrame")
        wrap.pack(pady=12, fill="x")

        total_variations = sum(state.variation_design_counts) if state.variation_design_counts else 0
        major = state.major_variations or 0
        banner = ttk.Frame(wrap, style="Card.TFrame", padding=14)
        banner.pack(pady=6, padx=10, fill="x")
        ttk.Label(banner, text=f"All {total_variations} Variations added under {major} major sizes   ✔", style="H2.TLabel").pack()

        pkg = ttk.Frame(wrap, style="Card.TFrame", padding=14)
        pkg.pack(pady=8, padx=10, fill="x")
        x = state.pkg_x or "—"; y = state.pkg_y or "—"
        ttk.Label(pkg, text=f"package size {x}/{y}mm", style="H2.TLabel").pack()

        counts = ttk.Frame(wrap, style="Card.TFrame", padding=14)
        counts.pack(pady=10, padx=10)
        ttk.Label(counts, text="Number of stickers in 1× sheet:", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        self.total_var = tk.IntVar(value=100)
        ttk.Entry(counts, textvariable=self.total_var, width=8, justify="center").grid(row=0, column=1, padx=10)

        self.size_vars: list[tk.IntVar] = []
        start_row = 1
        default_each = max(1, self.total_var.get() // major) if major else 0
        for i in range(major):
            ttk.Label(counts, text=f"Size major {i+1}", style="Label.TLabel").grid(row=start_row + i, column=0, sticky="e", pady=4, padx=(0, 8))
            v = tk.IntVar(value=default_each)
            self.size_vars.append(v)
            ttk.Entry(counts, textvariable=v, width=8, justify="center").grid(row=start_row + i, column=1)

        bottom_bar = ttk.Frame(self, style="Screen.TFrame")
        bottom_bar.pack(fill="x", padx=10, pady=(8, 0))
        ai_card = ttk.Frame(bottom_bar, style="Card.TFrame", padding=10)
        ai_card.pack(side="left")
        self.ai_arrange = tk.BooleanVar(value=True)
        ttk.Checkbutton(ai_card, text="AiArrange", variable=self.ai_arrange).pack()

        self.bottom_nav(self, on_back=lambda: self.app.show_screen(Screen5), on_next=self._finish, next_text="Proceed!")

    def _finish(self):
        total = self.total_var.get()
        per = sum(v.get() for v in self.size_vars)
        if per != total:
            if not messagebox.askyesno("Counts don't match", f"Per-size total ({per}) doesn't equal overall total ({total}). Continue?"):
                return
        state.sheet_total = total
        state.sheet_per_major = [v.get() for v in self.size_vars]
        state.ai_arrange = self.ai_arrange.get()
        self.app.show_screen(Screen7)


# ================================================
# Screen 7 — макет/превью раскладки
# ================================================
class Screen7(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        bar = tk.Frame(self, bg="#111111", height=50)
        bar.pack(fill="x")

        total = state.sheet_total or 0
        done = total
        tk.Label(bar, text=f"{done}/{total}", bg="#111111", fg="white", font=("Arial", 26, "bold")).pack(side="left", padx=16, pady=8)

        major = state.major_variations or 0
        tk.Label(bar, text=f"{major}/{major} Major variation", bg="#111111", fg="white", font=("Arial", 16)).pack(side="left", padx=16, pady=8)

        right_btns = tk.Frame(bar, bg="#111111")
        right_btns.pack(side="right", padx=12)
        ttk.Button(right_btns, text="ORDER NUMBER\nALLOCATION").pack(side="left", padx=8, pady=8)
        ttk.Button(right_btns, text="Select tool").pack(side="left", padx=8, pady=8)
        ttk.Button(right_btns, text="Ai arrange", state=("normal" if state.ai_arrange else "disabled")).pack(side="left", padx=8, pady=8)

        wrap = ttk.Frame(self, style="Screen.TFrame")
        wrap.pack(expand=True, fill="both")

        board = tk.Frame(wrap, bg="#2f2f2f")
        board.place(relx=0.5, rely=0.54, anchor="center", width=620, height=520)

        self.canvas = tk.Canvas(board, bg="#3f3f3f", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=18, pady=18)
        self._draw_mock_layout()

        self.bottom_nav(self, on_back=lambda: self.app.show_screen(Screen6), on_next=lambda: self.app.show_screen(Screen8), next_text="Save")

    def _draw_mock_layout(self):
        c = self.canvas

        def grid(x0, y0, cols, rows, cell_w, cell_h, gap=8):
            x = x0
            for _ in range(cols):
                y = y0
                for _ in range(rows):
                    c.create_rectangle(x, y, x + cell_w, y + cell_h, fill="white", outline="#5a5a5a", width=2)
                    y += cell_h + gap
                x += cell_w + gap

        grid(x0=20, y0=20, cols=3, rows=14, cell_w=36, cell_h=22, gap=6)
        grid(x0=210, y0=30, cols=6, rows=4, cell_w=70, cell_h=50, gap=10)
        x1, y1, x2, y2 = 360, 350, 560, 450
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#dcdcdc", dash=(8, 6), width=3)


# ================================================
# Screen 8 — успех + скачивание PDF
# ================================================
class Screen8(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        wrap = ttk.Frame(self, style="Screen.TFrame")
        wrap.pack(expand=True, fill="both", padx=20, pady=20)

        ttk.Label(wrap, text="Product Added Successfully", style="H1.TLabel").pack(pady=(10, 16))

        chk = tk.Canvas(wrap, width=180, height=180, bg="#4d4d4d", highlightthickness=0)
        chk.pack(pady=(0, 12))
        r = 80; cx, cy = 90, 90
        chk.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#17a24b", width=10)
        chk.create_line(55, 95, 85, 120, fill="#17a24b", width=12, capstyle="round")
        chk.create_line(85, 120, 140, 60, fill="#17a24b", width=12, capstyle="round")

        product_name = state.saved_product if state.saved_product else "Product"
        sku_line1 = f"Sku {product_name}"
        sku_line2 = state.sku or "—"
        ttk.Label(wrap, text=sku_line1, style="H1.TLabel").pack(pady=(6, 0))
        ttk.Label(wrap, text=sku_line2, style="H1.TLabel").pack(pady=(0, 16))

        file_row = ttk.Frame(wrap, style="Screen.TFrame")
        file_row.pack(pady=(8, 0))
        file_chip = ttk.Frame(file_row, style="Card.TFrame", padding=10)
        file_chip.pack(side="left")
        ttk.Label(file_chip, text="Test File .pdf", style="H2.TLabel").pack()
        ttk.Button(file_row, text="Download", command=self._download).pack(side="left", padx=14)

        self.bottom_nav(self, on_back=lambda: self.app.show_screen(Screen7), on_next=self.app.quit_app, next_text="Done")

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