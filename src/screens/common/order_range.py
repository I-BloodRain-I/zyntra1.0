import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

from src.core.state import state
from src.core import Screen, COLOR_BG_DARK, COLOR_BG_SCREEN, COLOR_TEXT, scale_px, font_from_pt, UI_SCALE
from src.utils import *
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

        # Bottom-right Start button (styled like font_info)
        start_btn = create_button(
            ButtonInfo(
                parent=self,
                text_info=TextInfo(
                    text="Start",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                button_color=COLOR_BG_DARK,
                hover_color="#3f3f3f",
                active_color=COLOR_BG_DARK,
                padding_x=20,
                padding_y=12,
                command=self._start,
            )
        )
        start_btn.place(relx=0.995, rely=0.99, anchor="se")

        # Bottom-left Go Back button (styled like font_info)
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