import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from src.core.app import UI_SCALE, scale_px
from src.utils import *

from src.core import Screen, warn, COLOR_TEXT, COLOR_BG_LIGHT, COLOR_BG_SCREEN, COLOR_BG_DARK, COLOR_PILL, UI_SCALE, scale_px
from src.core.state import state
from src.utils import *
# from .sticker_copy import Screen6


class StickerDefineImageScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.brand_bar(self)
        self.app = app

        tk.Label(self,
                 text=state.sku_name,
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))
            
        i = 0
        var_i = 0
        header_major = create_pill_label(
            PillLabelInfo(
                parent=self,
                text_info=TextInfo(
                    text=f"Major {i+1}/{state.major_variations}  |  X: {state.major_sizes[i][0]}mm, Y: {state.major_sizes[i][1]}mm",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=20
            )
        )
        header_major.place(relx=0.5, rely=0.15, anchor="center")
        header_var = create_pill_label(
            PillLabelInfo(
                parent=self,
                text_info=TextInfo(
                    text=f"Variation {var_i+1}/{state.variation_design_counts[i]}",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=20,
            )
        )
        header_var.place(relx=0.5, rely=0.15, y=header_major.winfo_height() + 60, anchor="center")
        tk.Misc.lift(header_major)

        import_line_info = PillLabelInfo(
            width=app.screen_width,
            height=60,
            parent=self,
            fill="black",
        )
        import_line = create_pill_label(import_line_info)

        import_line, import_line_canvas, _ = append_object_to_pill_label(
            import_line_info,
            pill_canvas=import_line,
            object_info=ButtonInfo(
                parent=import_line,
                text_info=TextInfo(
                    text="DTS",
                    color=COLOR_TEXT,
                    font_size=14,
                ),
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_LIGHT,
                active_color=COLOR_PILL,
                radius=15,
                padding_x=20,
                padding_y=10,
            ),
            object_padding_x=70,
            object_padding_y=20,
        )

        import_line, import_line_canvas, _ = append_object_to_pill_label(
            import_line_info,
            pill_canvas=import_line,
            object_info=ButtonInfo(
                parent=import_line,
                text_info=TextInfo(
                    text="DIS",
                    color=COLOR_TEXT,
                    font_size=14,
                ),
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_LIGHT,
                active_color=COLOR_PILL,
                radius=15,
                padding_x=25,
                padding_y=10,
            ),
            object_padding_x=140,
            object_padding_y=20,
        )

        import_line, import_line_canvas, _ = append_object_to_pill_label(
            import_line_info,
            pill_canvas=import_line,
            object_info=ButtonInfo(
                parent=import_line,
                text_info=TextInfo(
                    text="Import Image",
                    color=COLOR_TEXT,
                    font_size=14,
                ),
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_LIGHT,
                active_color=COLOR_PILL,
                radius=15,
                padding_x=10,
                padding_y=10,
            ),
            object_padding_x=215,
            object_padding_y=20,
        )

        import_line.place(relx=0.5, rely=0.4, anchor="center")

        # self.header(self, "Add a new product")

        # top = ttk.Frame(self, style="Screen.TFrame")
        # top.pack(pady=8, fill="x")

        # size_card = ttk.Frame(top, style="Card.TFrame", padding=10)
        # size_card.pack(side="left", padx=10)
        # ttk.Label(size_card, text=f"Size 1", style="H3.TLabel").grid(row=0, column=0, columnspan=4, pady=(0, 6))
        # ttk.Label(size_card, text="X (mm):").grid(row=1, column=0, sticky="e")
        # ttk.Entry(size_card, width=8).grid(row=1, column=1, padx=6)
        # ttk.Label(size_card, text="Y (mm):").grid(row=1, column=2, sticky="e")
        # ttk.Entry(size_card, width=8).grid(row=1, column=3, padx=6)

        # rc_card = ttk.Frame(top, style="Card.TFrame", padding=10)
        # rc_card.pack(side="left", padx=10)
        # ttk.Label(rc_card, text="Rounded corners", style="H3.TLabel").grid(row=0, column=0, columnspan=2)
        # ttk.Label(rc_card, text="Units:").grid(row=1, column=0, sticky="e")
        # ttk.Entry(rc_card, width=6).grid(row=1, column=1, padx=6)

        # col_card = ttk.Frame(self, style="Card.TFrame", padding=10)
        # col_card.pack(pady=10, fill="x", padx=10)
        # ttk.Label(col_card, text="Background color CMYK code", style="H3.TLabel").grid(row=0, column=0, sticky="w")
        # ttk.Entry(col_card, width=24)
        # ttk.Entry(col_card, width=24).grid(row=0, column=1, padx=8)

        # import_row = ttk.Frame(self, style="Screen.TFrame")
        # import_row.pack(fill="x", pady=8)
        # ttk.Label(import_row, text="Import:", style="H3.TLabel").pack(side="left", padx=(10, 8))
        # for fmt in ("Png", "Jpg", "Svg"):
        #     ttk.Button(import_row, text=fmt).pack(side="left", padx=6)
        # right = ttk.Frame(import_row)
        # right.pack(side="right", padx=10)
        # self.dts = tk.BooleanVar(value=True)
        # ttk.Checkbutton(right, text="DTS", variable=self.dts).pack(side="left", padx=6)
        # self.dis = tk.BooleanVar(value=False)
        # ttk.Checkbutton(right, text="DIS", variable=self.dis).pack(side="left", padx=6)

        # canvas_card = ttk.Frame(self, style="Card.TFrame", padding=20)
        # canvas_card.pack(expand=True, fill="both", padx=10, pady=10)
        # ttk.Label(canvas_card, text="(Artwork preview)\nDefine text space →", style="Muted.TLabel").pack(expand=True)

        # self.bottom_nav(self, on_back=self.app.go_back, on_next=None, next_text=None, back_text=None)
        # back_btn = create_button(
        #     ButtonInfo(
        #         parent=self,
        #         text_info=TextInfo(
        #             text="Go Back",
        #             color=COLOR_TEXT,
        #             font_size=22,
        #         ),
        #         button_color=COLOR_BG_DARK,
        #         hover_color="#3f3f3f",
        #         active_color=COLOR_BG_DARK,
        #         padding_x=20,
        #         padding_y=12,
        #         command=self.app.go_back,
        #     )
        # )
        # back_btn.place(relx=0.005, rely=0.99, anchor="sw")
        # proceed_btn = create_button(
        #     ButtonInfo(
        #         parent=self,
        #         text_info=TextInfo(
        #             text="Proceed",
        #             color=COLOR_TEXT,
        #             font_size=22,
        #         ),
        #         button_color=COLOR_BG_DARK,
        #         hover_color="#3f3f3f",
        #         active_color=COLOR_BG_DARK,
        #         padding_x=20,
        #         padding_y=12,
        #         command=lambda: self.app.show_screen(Screen6),
        #     )
        # )
        # proceed_btn.place(relx=0.995, rely=0.99, anchor="se")