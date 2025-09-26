import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

from src.core.state import state
from src.core import Screen, COLOR_BG_DARK, COLOR_BG_SCREEN, COLOR_TEXT, scale_px, font_from_pt, UI_SCALE
from .process_orders import ProcessOrdersScreen


class OrderRangeScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        # Top line identical to LauncherSelectProduct
        self.brand_bar(self)

        # Product tag (dark pill) below the top line
        tk.Label(self,
                 text=state.saved_product,
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))

        # Center area with header and inputs (no background panel)
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

        # Centered dark plaque title
        plaque = tk.Frame(content, bg=COLOR_BG_DARK)
        tk.Label(plaque,
                 text="Write order numbers to produce files:",
                 bg=COLOR_BG_DARK, fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(20 * UI_SCALE))))\
            .pack(padx=scale_px(12), pady=scale_px(6))
        plaque.pack(pady=(0, scale_px(12)))

        # Inputs row (compact, centered)
        lbl_font = ("Myriad Pro", int(round(24 * UI_SCALE)))
        ent_font = ("Myriad Pro", int(round(22 * UI_SCALE)))

        row_inputs = tk.Frame(content, bg=COLOR_BG_SCREEN)
        row_inputs.pack()

        tk.Label(row_inputs, text="From:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=lbl_font).pack(side="left", padx=(0, 0))
        self.from_var = tk.StringVar(value=state.order_from)
        tk.Entry(row_inputs, textvariable=self.from_var, width=8, justify="center",
                 font=ent_font, bg="#ffffff", relief="flat").pack(side="left")

        tk.Label(row_inputs, text="To:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=lbl_font).pack(side="left", padx=(scale_px(50), 0))
        self.to_var = tk.StringVar(value=state.order_to)
        tk.Entry(row_inputs, textvariable=self.to_var, width=8, justify="center",
                 font=ent_font, bg="#ffffff", relief="flat").pack(side="left")

        # Bottom-right Start button (single)
        start_text = "Start"
        start_font_obj = font_from_pt(14.4)
        start_font = tkfont.Font(font=start_font_obj)
        start_width_px = int(start_font.measure(start_text) + scale_px(16))
        start_height_px = int(start_font.metrics("linespace") + scale_px(20))
        btn_start_canvas = tk.Canvas(self, width=start_width_px, height=start_height_px, bg=COLOR_BG_DARK,
                                     highlightthickness=0, bd=0, cursor="hand2")
        sx_left = 8
        sy_center = start_height_px // 2
        start_text_id = btn_start_canvas.create_text(sx_left, sy_center, text=start_text, font=start_font_obj, fill=COLOR_TEXT, anchor="w")
        def _start_press(_e, canvas=btn_start_canvas, tid=start_text_id):
            canvas.configure(bg="#3f3f3f")
            canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _start_release(e, canvas=btn_start_canvas, tid=start_text_id):
            canvas.configure(bg=COLOR_BG_DARK)
            canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, self._start)
            canvas._pressed = False
        btn_start_canvas.bind("<ButtonPress-1>", _start_press)
        btn_start_canvas.bind("<ButtonRelease-1>", _start_release)
        btn_start_canvas.place(relx=1.0, rely=1.0, x=-scale_px(12), y=-scale_px(12), anchor="se")

        # Bottom-left Go Back button (styled like Start)
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

        # Hotkeys: Enter → Start, Escape → Back (accept optional event)
        self.app.bind("<Return>", lambda _e=None: self._start())
        self.app.bind("<Escape>", lambda _e=None: self.app.go_back())

    def _start(self):
        from_s = self.from_var.get().strip()
        to_s = self.to_var.get().strip()

        # 1) Order number does not exist / invalid
        if not from_s or not to_s:
            messagebox.showerror("Error", "Order number does not exist.")
            return

        # Both must be integers
        try:
            from_n = int(from_s)
            to_n = int(to_s)
        except ValueError:
            messagebox.showerror("Error", "Order number does not exist.")
            return

        # Range sanity
        if from_n > to_n:
            messagebox.showwarning("Warning", "'From' must be less than or equal to 'To'.")
            return

        state.order_from = from_s
        state.order_to = to_s
        self.app.show_screen(ProcessOrdersScreen)