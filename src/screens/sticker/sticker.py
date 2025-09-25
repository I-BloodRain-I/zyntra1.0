import tkinter as tk
from tkinter import ttk

from src.core import Screen, vcmd_int, vcmd_float, warn, COLOR_PILL, COLOR_BG_SCREEN, COLOR_BG_SCREEN_FOR_LABELS, COLOR_TEXT, font_from_pt, scale_px
from src.state import state
from .sticker_copy import Screen3


class StickerBasicInfoScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.pack(fill="both", expand=True)

        # Цвета
        self.bg = "#777777"       # фон всего экрана
        self.block_bg = "#999999" # фон блоков
        self.pill_bg = "#ffffff"  # фон полей
        self.fg = "#000000"

        self.configure(style="Screen.TFrame")

        # Заголовок
        self.header(self, "Add a new product")

        # Тело
        body = tk.Frame(self, bg=self.bg)
        body.pack(fill="both", expand=True)

        # --- SKU ---
        row = self._block(body)
        tk.Label(row, text="Give your sku number:", bg=self.block_bg,
                 fg=self.fg, font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.sku_var = tk.StringVar(value="1324-2342-5433")
        self._pill(row, self.sku_var, w=180).pack(side="left")

        # --- Package size ---
        row = self._block(body)
        tk.Label(row, text="Your package size:", bg=self.block_bg,
                 fg=self.fg, font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self._xy(row, "X:", "80mm").pack(side="left", padx=8)
        self._xy(row, "Y:", "80mm").pack(side="left", padx=8)

        # --- Size variations ---
        row = self._block(body)
        tk.Label(row, text="Number of size variations:", bg=self.block_bg,
                 fg=self.fg, font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.size_var = tk.StringVar(value="3")
        self._pill(row, self.size_var, w=50).pack(side="left", padx=6)

        # --- Variation 1/2/3 ---
        self.v1 = tk.StringVar(value="4")
        self.v2 = tk.StringVar(value="4")
        self.v3 = tk.StringVar(value="4")
        self._variation(body, "Variation 1 Designs total:", self.v1)
        self._variation(body, "Variation 2 Designs total:", self.v2)
        self._variation(body, "Variation 3 Designs total:", self.v3)

        # --- Total fonts ---
        row = self._block(body)
        tk.Label(row, text="Total fonts Variations:", bg=self.block_bg,
                 fg=self.fg, font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.fonts_total = tk.StringVar(value="7")
        self._pill(row, self.fonts_total, w=60).pack(side="left", padx=6)

        # --- Bottom nav ---
        self.bottom_nav(self, on_next=self.on_proceed, next_text="Proceed")

    # -------- helpers ----------
    def _block(self, parent):
        f = tk.Frame(parent, bg=self.block_bg)
        f.pack(fill="x", padx=12, pady=6)
        return f

    def _pill(self, parent, var, w=100):
        wrap = tk.Frame(parent, bg=self.pill_bg, height=28, width=w)
        wrap.pack_propagate(False)
        e = tk.Entry(wrap, textvariable=var, bd=0, font=("Arial", 12),
                     justify="center", bg=self.pill_bg)
        e.pack(fill="both", expand=True, padx=6, pady=2)
        return wrap

    def _xy(self, parent, axis, val):
        cont = tk.Frame(parent, bg=self.block_bg)
        tk.Label(cont, text=axis, bg=self.pill_bg, font=("Arial", 11)).pack(side="left")
        var = tk.StringVar(value=val)
        self._pill(cont, var, w=70).pack(side="left", padx=4)
        return cont

    def _variation(self, parent, label, var):
        row = self._block(parent)
        tk.Label(row, text=label, bg=self.block_bg, fg=self.fg,
                 font=("Arial", 12)).pack(side="left", padx=10)
        self._pill(row, var, w=50).pack(side="right", padx=10)

    # -------- logic ----------
    def on_proceed(self):
        data = {
            "sku": self.sku_var.get(),
            "size_variations": self.size_var.get(),
            "v1": self.v1.get(),
            "v2": self.v2.get(),
            "v3": self.v3.get(),
            "fonts_total": self.fonts_total.get(),
        }
        print("Collected:", data)
# ================================================
# Screen 2 — SKU, package size, major variations
# ================================================
# class StickerBasicInfoScreen(Screen):
#     def __init__(self, master, app):
#         super().__init__(master, app)
#         # Top brand bar
#         self.brand_bar(self)

#         # Centered screen title under the top line
#         title_wrap = ttk.Frame(self, style="Screen.TFrame")
#         title_wrap.pack(pady=(10, 6), fill="x")
#         self._plaque_label(title_wrap, "Add a new product").pack(anchor="center")

#         # Outer white border and centered content column
#         outer = tk.Frame(self, bg="#ffffff")
#         outer.pack(expand=True, fill="both", padx=6, pady=6)
#         column = ttk.Frame(outer, style="Screen.TFrame")
#         column.pack(expand=True, fill="both")

#         # Center column with uniform side margins and standardized vertical spacing
#         SPACING_Y = 24
#         SIDE_PAD_X = 70
#         form = ttk.Frame(column, style="Screen.TFrame")
#         form.pack(padx=SIDE_PAD_X, pady=(SPACING_Y, SPACING_Y // 2), fill="x")

#         # SKU
#         row1 = ttk.Frame(form, style="Screen.TFrame", padding=(0, 6))
#         row1.pack(fill="x")
#         # Bubble label + input INSIDE the same label frame background
#         self.sku_var = tk.StringVar(value=state.sku or "1324-2342-5433")
#         sku_frame = tk.Frame(row1, bg=COLOR_BG_SCREEN_FOR_LABELS)
#         sku_frame.pack(side="left")
#         # Place bubble label; avoid implicit spacing
#         self._bubble_label(sku_frame, "Give your sku number:", width_px=450).pack(side="left", padx=0, pady=0, ipadx=0, ipady=0)
#         pill = self._pill_entry(sku_frame, self.sku_var, width_chars=20)
#         pill.pack(side="left", padx=0, pady=0)
#         try:
#             pill.pack_configure(ipadx=0, ipady=0)
#         except Exception:
#             pass

#         # Package size
#         pack_card = ttk.Frame(form, style="Card.TFrame", padding=14)
#         pack_card.pack(pady=SPACING_Y, fill="x")
#         ttk.Label(pack_card, text="Your package size:", style="H2.TLabel").grid(row=0, column=0, sticky="w")
#         self.pkgx = tk.StringVar(value=state.pkg_x or "80")
#         self.pkgy = tk.StringVar(value=state.pkg_y or "80")
#         # White pill inputs on the same baseline as the label
#         self._mm_row(pack_card, "X:", self.pkgx).grid(row=0, column=1, sticky="w", padx=(14, 14))
#         self._mm_row(pack_card, "Y:", self.pkgy).grid(row=0, column=2, sticky="w", padx=(0, 14))

#         # Major variations
#         var_card = ttk.Frame(form, style="Card.TFrame", padding=14)
#         var_card.pack(pady=SPACING_Y, fill="x")
#         ttk.Label(var_card, text="Number of size variations:", style="H2.TLabel").grid(row=0, column=0, sticky="w")
#         self.major_count = tk.IntVar(value=state.major_variations or 3)
#         self._pill_entry(var_card, self.major_count, width_chars=2, is_int=True).grid(row=0, column=1, padx=8, sticky="e")
#         # Rebuild rows when value changes
#         try:
#             self.major_count.trace_add("write", lambda *_: self._rebuild_variation_rows())
#         except Exception:
#             pass

#         # Per-variation design counts
#         self.variations_frame = ttk.Frame(form, style="Screen.TFrame")
#         self.variations_frame.pack(fill="x", pady=(SPACING_Y // 2, 0))
#         self.design_vars: list[tk.IntVar] = []
#         self._rebuild_variation_rows()

#         # Total fonts variations
#         fonts_card = ttk.Frame(form, style="Card.TFrame", padding=14)
#         fonts_card.pack(pady=SPACING_Y, fill="x")
#         ttk.Label(fonts_card, text="Total fonts Variations:", style="H2.TLabel").pack(side="left")
#         self.font_total = tk.IntVar(value=state.font_variations_total or 7)
#         self._pill_entry(fonts_card, self.font_total, width_chars=3, is_int=True).pack(side="right")

#         # Bottom-right action button (Proceed)
#         self.bottom_nav(self, on_back=self.app.go_back, on_next=self.next, next_text="Proceed")

#     def _rebuild_variation_rows(self):
#         for w in self.variations_frame.winfo_children():
#             w.destroy()
#         self.design_vars.clear()
#         n = int(self.major_count.get() or 0)
#         preset = state.variation_design_counts or [4] * n
#         for i in range(n):
#             # Full-width row for visual consistency
#             row = tk.Frame(self.variations_frame, bg="#bdbdbd")
#             row.pack(fill="x", pady=12)
#             inner = tk.Frame(row, bg="#bdbdbd")
#             inner.pack(fill="x", padx=16, pady=10)
#             tk.Label(inner, text=f"Variation {i+1} Designs total:", bg="#bdbdbd", fg="#000000", font=("Myriad Pro", 12, "bold")).pack(side="left")
#             var = tk.IntVar(value=preset[i] if i < len(preset) else 4)
#             self._pill_entry(inner, var, width_chars=3, is_int=True).pack(side="right")
#             self.design_vars.append(var)

#     def next(self):
#         sku_val = self.sku_var.get().strip()
#         if not sku_val:
#             warn("Please select an SKU before proceeding.", title="Missing SKU")
#             return

#         if len(sku_val) < 3:
#             warn("SKU doesn't exist.", title="Invalid SKU")
#             return

#         try:
#             int(self.pkgx.get()); int(self.pkgy.get())
#         except ValueError:
#             warn("Package size X/Y must be numbers (mm).", title="Numbers only")
#             return

#         state.sku = sku_val
#         state.pkg_x = self.pkgx.get().strip()
#         state.pkg_y = self.pkgy.get().strip()
#         # Ensure at least one major variation
#         mv = int(self.major_count.get()) if int(self.major_count.get() or 0) > 0 else 1
#         state.major_variations = mv
#         state.variation_design_counts = [int(v.get()) for v in self.design_vars]
#         state.font_variations_total = int(self.font_total.get())

#         state.font_names = ["" for _ in range(state.font_variations_total)]
#         state.font_uploaded = [False for _ in range(state.font_variations_total)]

#         self.app.show_screen(Screen3)

#     # ---- UI helpers to match screenshot ----
#     def _bubble_label(self, parent, text: str, width_px: int | None = None):
#         # Draw a rounded rectangle background with the given text
#         f_obj = font_from_pt(20)
#         f = tk.font.Font(font=f_obj) if hasattr(tk, 'font') else None
#         try:
#             import tkinter.font as tkfont  # safe import here to get measure/metrics
#             f = tkfont.Font(font=f_obj)
#         except Exception:
#             f = None
#         pad_x = 12
#         pad_y = 8
#         auto_w = int((f.measure(text) if f else 220) + pad_x * 2)
#         w_px = int(width_px) if isinstance(width_px, (int,)) and width_px else auto_w
#         h_px = int((f.metrics("linespace") if f else 24) + pad_y * 2)
#         cnv = tk.Canvas(parent, width=w_px, height=h_px, bg=self._bg_color(parent), highlightthickness=0, bd=0)
#         r = max(10, int(round(h_px * 0.45)))
#         x1, y1, x2, y2 = 0, 0, w_px, h_px
#         # Core rounded rect pieces
#         cnv.create_rectangle(x1 + r, y1, x2 - r, y2, fill=COLOR_BG_SCREEN_FOR_LABELS, outline="")
#         cnv.create_rectangle(x1, y1 + r, x2, y2 - r, fill=COLOR_BG_SCREEN_FOR_LABELS, outline="")
#         cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=COLOR_BG_SCREEN_FOR_LABELS, outline="")
#         cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=COLOR_BG_SCREEN_FOR_LABELS, outline="")
#         cnv.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill=COLOR_BG_SCREEN_FOR_LABELS, outline="")
#         cnv.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill=COLOR_BG_SCREEN_FOR_LABELS, outline="")
#         cnv.create_text(pad_x, h_px // 2, text=text, font=f_obj, fill=COLOR_TEXT, anchor="w")
#         return cnv

#     def _mm_row(self, parent, label: str, var: tk.StringVar):
#         frm = ttk.Frame(parent, style="Card.TFrame")
#         bg = self._bg_color(frm)
#         tk.Label(frm, text=label, bg=bg, fg="#000000").pack(side="left", padx=(0, 6))
#         self._pill_entry(frm, var, width_chars=5, is_float=True).pack(side="left")
#         tk.Label(frm, text="mm", bg=bg, fg="#000000").pack(side="left", padx=(8, 0))
#         return frm

#     def _pill_entry(self, parent, var, width_chars=4, is_int=False, is_float=False):
#         # Rounded white pill that hosts a borderless entry centered
#         import tkinter.font as tkfont
#         f_obj = font_from_pt(16)
#         f = tkfont.Font(font=f_obj)
#         pad_x = 12
#         pad_y = 10
#         char_w = f.measure("0")
#         w_px = int(char_w * max(2, width_chars) + pad_x * 2)
#         h_px = int(f.metrics("linespace") + pad_y * 2)
#         cnv = tk.Canvas(parent, width=w_px, height=h_px, bg=self._bg_color(parent), highlightthickness=0, bd=0)
#         r = max(12, int(round(h_px * 0.6)))
#         x1, y1, x2, y2 = 0, 0, w_px, h_px
#         for _ in (0,):
#             cnv.create_rectangle(x1 + r, y1, x2 - r, y2, fill="#ffffff", outline="")
#             cnv.create_rectangle(x1, y1 + r, x2, y2 - r, fill="#ffffff", outline="")
#             cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill="#ffffff", outline="")
#             cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill="#ffffff", outline="")
#             cnv.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill="#ffffff", outline="")
#             cnv.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill="#ffffff", outline="")
#         vcmd = None
#         if is_int:
#             vcmd = (vcmd_int(self), "%P")
#         elif is_float:
#             vcmd = (vcmd_float(self), "%P")
#         ent = tk.Entry(cnv, textvariable=var, bg="#ffffff", relief="flat", bd=0,
#                        highlightthickness=0, justify="center", font=f_obj,
#                        width=width_chars, validate=("key" if (is_int or is_float) else "none"),
#                        validatecommand=vcmd if vcmd else None)
#         cnv.create_window(w_px // 2, h_px // 2, window=ent)
#         return cnv

#     def _plaque_label(self, parent, text: str):
#         # Dark rounded rectangle with left-aligned text
#         import tkinter.font as tkfont
#         f_obj = font_from_pt(20)
#         f = tkfont.Font(font=f_obj)
#         pad_x = scale_px(20)
#         pad_y = scale_px(12)
#         w_px = int(f.measure(text) + pad_x * 2)
#         h_px = int(f.metrics("linespace") + pad_y * 2)
#         cnv = tk.Canvas(parent, width=w_px, height=h_px, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
#         r = max(6, int(round(h_px * 0.35)))
#         x1, y1, x2, y2 = 0, 0, w_px, h_px
#         fill = "#4d4d4d"
#         cnv.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
#         cnv.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
#         cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=fill, outline="")
#         cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=fill, outline="")
#         cnv.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill=fill, outline="")
#         cnv.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill=fill, outline="")
#         cnv.create_text(pad_x, h_px // 2, text=text, font=f_obj, fill=COLOR_TEXT, anchor="w")
#         return cnv

#     def _bg_color(self, widget) -> str:
#         # Resolve a reasonable background color for tk or ttk containers
#         # Priority: explicit 'bg' -> 'background' -> ttk style lookup -> fallbacks by style name
#         try:
#             return widget.cget("bg")
#         except Exception:
#             pass
#         try:
#             return widget.cget("background")
#         except Exception:
#             pass
#         try:
#             style_name = str(widget.cget("style"))
#         except Exception:
#             style_name = ""
#         try:
#             from tkinter import ttk as _ttk
#             st = _ttk.Style()
#             if style_name:
#                 val = st.lookup(style_name, "background")
#                 if val:
#                     return str(val)
#         except Exception:
#             pass
#         if "Card" in style_name:
#             return "#a6a6a6"
#         return COLOR_BG_SCREEN
