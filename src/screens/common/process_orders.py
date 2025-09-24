import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog

from src.state import state
from src.core import Screen, COLOR_BG_DARK, COLOR_BG_SCREEN, COLOR_PILL, COLOR_TEXT, scale_px, font_from_pt, UI_SCALE
from src.screens.sticker import Screen2, _write_minimal_pdf


class ProcessOrdersScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.brand_bar(self)
        
        # Top-left selected product tag (dark pill)
        tk.Label(self,
                 text=state.saved_product,
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))

        # Center area: place content exactly at center
        mid = ttk.Frame(self, style="Screen.TFrame"); mid.pack(expand=True, fill="both")
        try:
            mid.grid_columnconfigure(0, weight=1)
            mid.grid_columnconfigure(1, weight=0)
            mid.grid_columnconfigure(2, weight=1)
            mid.grid_rowconfigure(0, weight=1)
            mid.grid_rowconfigure(1, weight=0)
            mid.grid_rowconfigure(2, weight=2)  # slightly more bottom weight → raise content a bit
        except Exception:
            pass

        content = tk.Frame(mid, bg=COLOR_BG_SCREEN)
        content.grid(row=1, column=1)

        # Centered text: "Processing......." and progress line
        proc_font = ("Myriad Pro", int(round(22 * UI_SCALE)))
        tk.Label(content, text="Processing...", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=proc_font).pack(anchor="center")

        # Compute simple total orders (e.g., 2/2)
        try:
            f = int(state.order_from or 0)
            t = int(state.order_to or 0)
            total = (t - f + 1) if t >= f else 0
        except Exception:
            total = 0
        tk.Label(content, text=f"{total}/{total}", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(22 * UI_SCALE)))).pack(pady=(scale_px(6), scale_px(16)))

        # Centered rounded "Download" pill button (black bg, white text)
        btn_text = "Download"
        f_obj = font_from_pt(14.4)
        f = tkfont.Font(font=f_obj)
        pad_x = scale_px(16)
        pad_y = scale_px(10)
        w_px = int(f.measure(btn_text) + pad_x * 2)
        h_px = int(f.metrics("linespace") + pad_y * 2)
        btn = tk.Canvas(content, width=w_px, height=h_px, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0, cursor="hand2")
        r = max(6, int(round(h_px * 0.5)))
        x1, y1, x2, y2 = 0, 0, w_px, h_px
        # Draw pill background (black)
        shapes = []
        shapes.append(btn.create_rectangle(x1 + r, y1, x2 - r, y2, fill="#000000", outline=""))
        shapes.append(btn.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill="#000000", outline=""))
        shapes.append(btn.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill="#000000", outline=""))
        txt_id = btn.create_text(pad_x, h_px // 2, text=btn_text, font=f_obj, fill="#ffffff", anchor="w")

        def _press(_e):
            for sid in shapes:
                btn.itemconfigure(sid, fill="#2a2a2a")
            btn.move(txt_id, 1, 1)
            btn._pressed = True

        def _release(e):
            for sid in shapes:
                btn.itemconfigure(sid, fill="#000000")
            btn.move(txt_id, -1, -1)
            try:
                w = btn.winfo_width(); h = btn.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(btn, "_pressed", False) and inside:
                self._download()
            btn._pressed = False

        btn.bind("<ButtonPress-1>", _press)
        btn.bind("<ButtonRelease-1>", _release)
        btn.pack(pady=(scale_px(24), 0))

        # Bottom-left Cancel button (style like "Go Back")
        cancel_text = "Cancel"
        cancel_font_obj = font_from_pt(14.4)
        cancel_font = tkfont.Font(font=cancel_font_obj)
        cancel_width_px = int(cancel_font.measure(cancel_text) + scale_px(16))
        cancel_height_px = int(cancel_font.metrics("linespace") + scale_px(20))
        btn_cancel_canvas = tk.Canvas(self, width=cancel_width_px, height=cancel_height_px, bg=COLOR_BG_DARK,
                                      highlightthickness=0, bd=0, cursor="hand2")
        cx_left = 8
        cy_center = cancel_height_px // 2
        cancel_text_id = btn_cancel_canvas.create_text(cx_left, cy_center, text=cancel_text, font=cancel_font_obj, fill=COLOR_TEXT, anchor="w")
        def _cancel_press(_e, canvas=btn_cancel_canvas, tid=cancel_text_id):
            canvas.configure(bg="#3f3f3f")
            canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _cancel_release(e, canvas=btn_cancel_canvas, tid=cancel_text_id):
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
        btn_cancel_canvas.bind("<ButtonPress-1>", _cancel_press)
        btn_cancel_canvas.bind("<ButtonRelease-1>", _cancel_release)
        btn_cancel_canvas.place(relx=0.0, rely=1.0, x=scale_px(12), y=-scale_px(12), anchor="sw")

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