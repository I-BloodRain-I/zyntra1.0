import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from src.core import Screen, COLOR_BG_DARK, COLOR_BG_SCREEN, COLOR_PILL, COLOR_TEXT, scale_px, font_from_pt, UI_SCALE
from src.core.state import state
from src.screens.sticker import StickerBasicInfoScreen
from src.screens.nonsticker import NStickerCanvasScreen


class ProductTypeScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        # Top brand bar (don't touch top line)
        self.brand_bar(self)

        # Center area similar to OrderRangeScreen
        mid = ttk.Frame(self, style="Screen.TFrame"); mid.pack(expand=True, fill="both")
        try:
            mid.grid_columnconfigure(0, weight=1)
            mid.grid_columnconfigure(1, weight=0)
            mid.grid_columnconfigure(2, weight=1)
            mid.grid_rowconfigure(0, weight=1)
            mid.grid_rowconfigure(1, weight=0)
            mid.grid_rowconfigure(2, weight=2)
        except Exception:
            pass

        # Centered content container
        content = tk.Frame(mid, bg=COLOR_BG_SCREEN)
        content.grid(row=1, column=1)

        # Centered dark plaque title ("Add a new product")
        plaque = tk.Frame(content, bg=COLOR_BG_DARK)
        tk.Label(plaque,
                 text="Add a new product",
                 bg=COLOR_BG_DARK, fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(22 * UI_SCALE))))\
            .pack(padx=scale_px(12), pady=scale_px(6))
        plaque.pack(pady=(0, scale_px(30)))

        # Question bubble (separate item with its own light background)
        q_text = "Is your product a sticker/Flex?"
        q_font_obj = font_from_pt(20)
        q_font = tkfont.Font(font=q_font_obj)
        q_pad_x = scale_px(20)
        q_pad_y = scale_px(25)
        q_w = int(q_font.measure(q_text) + q_pad_x * 2)
        q_h = int(q_font.metrics("linespace") + q_pad_y * 2)
        q_canvas = tk.Canvas(content, width=q_w, height=q_h, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
        qr = max(6, int(round(q_h * 0.22)))
        q_x1, q_y1, q_x2, q_y2 = 0, 0, q_w, q_h
        # Rounded rectangle (same corner style as Yes/No buttons)
        q_canvas.create_rectangle(q_x1 + qr, q_y1, q_x2 - qr, q_y2, fill=COLOR_PILL, outline="")
        q_canvas.create_rectangle(q_x1, q_y1 + qr, q_x2, q_y2 - qr, fill=COLOR_PILL, outline="")
        q_canvas.create_oval(q_x1, q_y1, q_x1 + 2 * qr, q_y1 + 2 * qr, fill=COLOR_PILL, outline="")
        q_canvas.create_oval(q_x2 - 2 * qr, q_y1, q_x2, q_y1 + 2 * qr, fill=COLOR_PILL, outline="")
        q_canvas.create_oval(q_x1, q_y2 - 2 * qr, q_x1 + 2 * qr, q_y2, fill=COLOR_PILL, outline="")
        q_canvas.create_oval(q_x2 - 2 * qr, q_y2 - 2 * qr, q_x2, q_y2, fill=COLOR_PILL, outline="")
        q_canvas.create_text(q_pad_x, q_h // 2, text=q_text, font=q_font_obj, fill=COLOR_TEXT, anchor="w")
        q_canvas.pack(pady=(0, scale_px(30)))

        # Yes/No pills (canvas-based for exact look)
        row = tk.Frame(content, bg=COLOR_BG_SCREEN)
        row.pack()

        def make_pill(parent, text: str, fill_color: str, on_click):
            f_obj = font_from_pt(21.8)
            f = tkfont.Font(font=f_obj)
            pad_x = scale_px(20)
            pad_y = scale_px(20)
            w_px = int(f.measure(text) + pad_x * 2)
            h_px = int(f.metrics("linespace") + pad_y * 2)
            cnv = tk.Canvas(parent, width=w_px, height=h_px, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0, cursor="hand2")
            # Draw rounded rectangle corners to match screenshot
            r = max(6, int(round(h_px * 0.22)))
            x1, y1, x2, y2 = 0, 0, w_px, h_px
            shape_ids = []
            # Core rectangles
            shape_ids.append(cnv.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill_color, outline=""))
            shape_ids.append(cnv.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill_color, outline=""))
            # Four corner arcs (quarter circles)
            shape_ids.append(cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=fill_color, outline=""))
            shape_ids.append(cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=fill_color, outline=""))
            shape_ids.append(cnv.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill=fill_color, outline=""))
            shape_ids.append(cnv.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill=fill_color, outline=""))
            tx = pad_x
            ty = h_px // 2
            tid = cnv.create_text(tx, ty, text=text, font=f_obj, fill=COLOR_TEXT, anchor="w")
            def _press(_e, c=cnv, t=tid):
                for sid in shape_ids:
                    c.itemconfigure(sid, fill="#3f3f3f")
                c.move(t, 1, 1)
                c._pressed = True
            def _release(e, c=cnv, t=tid):
                for sid in shape_ids:
                    c.itemconfigure(sid, fill=fill_color)
                c.move(t, -1, -1)
                try:
                    w = c.winfo_width(); h = c.winfo_height()
                    inside = 0 <= e.x <= w and 0 <= e.y <= h
                except Exception:
                    inside = True
                if getattr(c, "_pressed", False) and inside:
                    on_click()
                c._pressed = False
            cnv.bind("<ButtonPress-1>", _press)
            cnv.bind("<ButtonRelease-1>", _release)
            return cnv

        btn_yes = make_pill(row, "Yes", COLOR_PILL, lambda: self._show_sticker_screen())
        btn_no  = make_pill(row, "No",  COLOR_BG_DARK, lambda: self._show_non_sticker_screen())
        btn_yes.grid(row=0, column=0, padx=scale_px(25), pady=scale_px(4))
        btn_no.grid(row=0, column=1, padx=scale_px(25), pady=scale_px(4))

        # Bottom-left Go Back (style like OrderRangeScreen)
        back_text = "Go Back"
        back_font_obj = font_from_pt(14.4)
        back_font = tkfont.Font(font=back_font_obj)
        back_width_px = int(back_font.measure(back_text) + scale_px(16))
        back_height_px = int(back_font.metrics("linespace") + scale_px(20))
        btn_back_canvas = tk.Canvas(self, width=back_width_px, height=back_height_px, bg=COLOR_BG_DARK,
                                    highlightthickness=0, bd=0, cursor="hand2")
        bx_left = 8
        by_center = back_height_px // 2
        back_text_id = btn_back_canvas.create_text(bx_left, by_center, text=back_text, font=back_font_obj, fill=COLOR_TEXT, anchor="w")
        def _back_press(_e, canvas=btn_back_canvas, tid=back_text_id):
            canvas.configure(bg="#3f3f3f")
            canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _back_release(e, canvas=btn_back_canvas, tid=back_text_id):
            canvas.configure(bg=COLOR_BG_DARK)
            canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, self.app.go_back)
            canvas._pressed = False
        btn_back_canvas.bind("<ButtonPress-1>", _back_press)
        btn_back_canvas.bind("<ButtonRelease-1>", _back_release)
        btn_back_canvas.place(relx=0.0, rely=1.0, x=scale_px(12), y=-scale_px(12), anchor="sw")

        # Hotkeys (accept optional event)
        self.app.bind("<Escape>", lambda _e=None: self.app.go_back())

    def _show_sticker_screen(self):
        state.saved_product = ""
        self.app.show_screen(StickerBasicInfoScreen)

    def _show_non_sticker_screen(self):
        state.saved_product = ""
        self.app.show_screen(NStickerCanvasScreen)