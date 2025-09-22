import logging
import os
import io
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
from state import state, ALL_PRODUCTS, APP_TITLE, IMAGES_PATH
from core import App, Screen
from screens_sticker import Screen1


class LauncherSelectProduct(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        # Fall back to previous UI layout/styles for main screen
        title = tk.Frame(self, bg="#474747", height="31p"); title.pack(fill="x")
        title.pack_propagate(False)
        tk.Label(title, text=APP_TITLE, bg="#474747", fg="#000000",
                 font=("Myriad Pro", 24)).pack(side="left", padx=8, pady=0)

        mid = tk.Frame(self, bg="#878787"); mid.pack(expand=True, fill="both")
        label_select = tk.Label(mid, text="Select product:", bg="#878787", fg="#000000",
                 font=("Myriad Pro", 24))

        # DPI-aware font helper (must be defined before first use)
        dpi_px_per_inch = float(self.winfo_fpixels("1i"))
        def font_from_pt(pt_value: float) -> tkfont.Font:
            px = int(round(pt_value * dpi_px_per_inch / 72.0))
            return tkfont.Font(family="Myriad Pro", size=-px)

        # Custom combobox (text + arrow) replacing ttk visuals
        self.product_var = tk.StringVar(value=state.saved_product)
        cb_font = font_from_pt(21.8)
        cb_font_metrics = tkfont.Font(font=cb_font)
        cb_height_px = int(cb_font_metrics.metrics("linespace") + 20)  # 10px top/bottom

        self.combo_frame = tk.Frame(mid, bg="#3d3d3d", bd=0, highlightthickness=0)
        self.combo_text = tk.Canvas(self.combo_frame, height=cb_height_px, bg="#3d3d3d", highlightthickness=0, bd=0)
        self.combo_arrow = tk.Canvas(self.combo_frame, width=cb_height_px, height=cb_height_px, bg="#000000", highlightthickness=0, bd=0, cursor="hand2")
        self.combo_text.pack(side="left")
        self.combo_arrow.pack(side="left")

        def _render_combo_text():
            self.combo_text.delete("all")
            s = self.product_var.get()
            padding_lr = 8
            w_text = cb_font_metrics.measure(s)
            self.combo_text.configure(width=w_text + padding_lr * 2)
            self.combo_text.create_text(padding_lr, cb_height_px // 2, text=s, font=cb_font, fill="#000000", anchor="w")
            # redraw arrow strictly from SVG (no procedural drawing)
            c = self.combo_arrow
            c.delete("all")
            c.configure(width=cb_height_px, height=cb_height_px, bg="#000000")
            # Load prerendered PNG and scale to an exact fraction of box height
            png_path = os.path.join(IMAGES_PATH, "arrow_down.png")
            arrow_scale = 0.4  # supports 0.4, 0.45, 0.5, etc.
            target_h = max(1, int(cb_height_px * arrow_scale))
            try:
                from PIL import Image, ImageTk  # type: ignore
                img = Image.open(png_path).convert("RGBA")
                target_w = max(1, int(round(img.width * (target_h / img.height))))
                img = img.resize((target_w, target_h), Image.LANCZOS)
                self._arrow_img = ImageTk.PhotoImage(img)
            except Exception:
                base_img = tk.PhotoImage(file=png_path)
                factor = max(1, int(round(base_img.height() / target_h)))
                self._arrow_img = base_img.subsample(factor, factor) if factor > 1 else base_img
            # Move arrow down by ~4.5pt
            try:
                y_offset = int(round(float(self.winfo_fpixels("1p")) * 2))
            except Exception:
                y_offset = 4
            c.create_image(cb_height_px // 2, (cb_height_px // 2) + y_offset, image=self._arrow_img)



        _render_combo_text()

        # Native dropdown popup via Listbox in a borderless Toplevel
        self._combo_popup = None
        def _open_popup(_e=None):
            try:
                if self._combo_popup and self._combo_popup.winfo_exists():
                    self._combo_popup.destroy()
                self._combo_popup = tk.Toplevel(self)
                self._combo_popup.overrideredirect(True)
                self._combo_popup.configure(bg="#000000")
                # position
                rx = self.combo_frame.winfo_rootx()
                ry = self.combo_frame.winfo_rooty() + self.combo_frame.winfo_height()
                pw = self.combo_frame.winfo_width()
                self._combo_popup.geometry(f"{pw}x{min(240, 28*len(ALL_PRODUCTS))}+{rx}+{ry}")
                lb = tk.Listbox(self._combo_popup, font=cb_font, bg="#555555", fg="#ffffff",
                                selectbackground="#3f3f3f", activestyle="none", highlightthickness=0, bd=0)
                for item in ALL_PRODUCTS:
                    lb.insert("end", item)
                try:
                    idx = ALL_PRODUCTS.index(self.product_var.get())
                    lb.selection_set(idx)
                    lb.see(idx)
                except Exception:
                    pass
                lb.pack(fill="both", expand=True)
                def _choose(_evt=None):
                    try:
                        sel = lb.get(lb.curselection())
                    except Exception:
                        sel = None
                    if sel:
                        self.product_var.set(sel)
                        _render_combo_text()
                    self._combo_popup.destroy()
                lb.bind("<Double-Button-1>", _choose)
                lb.bind("<Return>", _choose)
                # close on focus out or click outside
                self._combo_popup.bind("<FocusOut>", lambda _e: self._combo_popup.destroy())
                self._combo_popup.focus_force()
            except Exception:
                pass

        self.combo_text.bind("<Button-1>", _open_popup)
        self.combo_arrow.bind("<Button-1>", _open_popup)
        # Place label and combobox precisely (label at 54pt from top of mid, dropdown 20pt under it)
        def _position_select():
            try:
                y_label = int(mid.winfo_fpixels("54p"))
                label_select.place(relx=0.5, x=0, y=y_label, anchor="n")
                mid.update_idletasks()
                gap_px = int(mid.winfo_fpixels("20p"))
                y_top = label_select.winfo_y() + label_select.winfo_height() + gap_px
                self.combo_frame.place(relx=0.5, x=0, y=y_top, anchor="n")
                _render_combo_text()
            except Exception:
                pass
        self.after_idle(_position_select)

        # Resize custom combobox when selection changes programmatically
        def _on_change(*_a):
            try:
                _render_combo_text()
            except Exception:
                pass
        self.product_var.trace_add("write", lambda *_a: _on_change())

        # Bottom-left buttons (fixed pixel size and placement)
        add_text = "Add a new product"
        add_font_obj = font_from_pt(23.5)
        add_font = tkfont.Font(font=add_font_obj)
        add_tracking_px = 1.2  # increase spacing per request
        add_char_widths = [add_font.measure(ch) for ch in add_text]
        add_text_width_px = sum(add_char_widths) + add_tracking_px * max(0, len(add_text) - 1)
        add_height_px = int(add_font.metrics("linespace") + 10)
        add_padding_lr = 8
        add_width_px = int(add_text_width_px + add_padding_lr * 2)
        btn_add_canvas = tk.Canvas(
            self,
            width=add_width_px,
            height=add_height_px,
            bg="#474747",
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )
        x_cursor_add = add_padding_lr
        y_center_add = add_height_px // 2
        add_text_ids = []
        for ch, cw in zip(add_text, add_char_widths):
            tid = btn_add_canvas.create_text(x_cursor_add, y_center_add, text=ch, font=add_font_obj, fill="#000000", anchor="w")
            add_text_ids.append(tid)
            x_cursor_add += cw + add_tracking_px
        def _add_press(_e, canvas=btn_add_canvas, ids=add_text_ids):
            canvas.configure(bg="#3f3f3f")
            for tid in ids:
                canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _add_release(e, canvas=btn_add_canvas, ids=add_text_ids):
            canvas.configure(bg="#474747")
            for tid in ids:
                canvas.move(tid, -1, -1)
            # Trigger click only if released inside the canvas
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, self._add_new)
            canvas._pressed = False
        btn_add_canvas.bind("<ButtonPress-1>", _add_press)
        btn_add_canvas.bind("<ButtonRelease-1>", _add_release)
        btn_add_canvas.place(relx=0.0, rely=1.0, x=12, y=-12, anchor="sw")

        # UPDATE EXISTING PRODUCT using Canvas to reduce letter spacing
        update_text = "UPDATE EXISTING PRODUCT"
        update_font = font_from_pt(15.74)
        upd_font = tkfont.Font(font=update_font)
        tracking_px = -0.64  # reduce letter spacing by 1px between glyphs
        char_widths = [upd_font.measure(ch) for ch in update_text]
        text_width_px = sum(char_widths) + tracking_px * max(0, len(update_text) - 1)
        upd_height_px = int(upd_font.metrics("linespace") + 20)
        padding_lr = 8
        upd_width_px = int(text_width_px + padding_lr * 2)
        gap_px = 12
        btn_update_canvas = tk.Canvas(
            self,
            width=upd_width_px,
            height=upd_height_px,
            bg="#474747",
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )
        # draw text with custom tracking
        x_cursor = padding_lr
        y_center = upd_height_px // 2
        upd_text_ids = []
        for ch, cw in zip(update_text, char_widths):
            tid = btn_update_canvas.create_text(x_cursor, y_center, text=ch, font=update_font, fill="#000000", anchor="w")
            upd_text_ids.append(tid)
            x_cursor += cw + tracking_px
        def _upd_press(_e, canvas=btn_update_canvas, ids=upd_text_ids):
            canvas.configure(bg="#3f3f3f")
            for tid in ids:
                canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _upd_release(e, canvas=btn_update_canvas, ids=upd_text_ids):
            canvas.configure(bg="#474747")
            for tid in ids:
                canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, lambda: None)  # no action bound for update yet
            canvas._pressed = False
        btn_update_canvas.bind("<ButtonPress-1>", _upd_press)
        btn_update_canvas.bind("<ButtonRelease-1>", _upd_release)
        btn_update_canvas.place(relx=0.0, rely=1.0, x=12, y=-(12 + add_height_px + gap_px), anchor="sw")

        # Proceed button on Canvas with press animation
        proceed_text = "Proceed"
        proceed_font_obj = font_from_pt(14.4)
        proceed_font = tkfont.Font(font=proceed_font_obj)
        proceed_width_px = int(proceed_font.measure(proceed_text) + 16)
        proceed_height_px = int(proceed_font.metrics("linespace") + 20)
        btn_proceed_canvas = tk.Canvas(
            self,
            width=proceed_width_px,
            height=proceed_height_px,
            bg="#474747",
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )
        px_left = 8
        py_center = proceed_height_px // 2
        proc_text_id = btn_proceed_canvas.create_text(px_left, py_center, text=proceed_text, font=proceed_font_obj, fill="#000000", anchor="w")
        def _proc_press(_e, canvas=btn_proceed_canvas, tid=proc_text_id):
            canvas.configure(bg="#3f3f3f")
            canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _proc_release(e, canvas=btn_proceed_canvas, tid=proc_text_id):
            canvas.configure(bg="#474747")
            canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                canvas.after(10, self._proceed)
            canvas._pressed = False
        btn_proceed_canvas.bind("<ButtonPress-1>", _proc_press)
        btn_proceed_canvas.bind("<ButtonRelease-1>", _proc_release)
        btn_proceed_canvas.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")
        try:
            self.combo_text.focus_set()
        except Exception:
            pass

    def _proceed(self):
        state.saved_product = self.product_var.get()
        self.app.show_screen(LauncherOrderRange)

    def _add_new(self):
        logging.info("Starting new product flow (sticker/non-sticker chooser)")
        self.app.show_screen(Screen1)


class LauncherOrderRange(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        bar = ttk.Frame(self, style="Title.TFrame"); bar.pack(fill="x")
        ttk.Label(bar, text=APP_TITLE, style="Brand.TLabel").pack(side="left", padx=10, pady=6)

        ttk.Label(self, text=state.saved_product, style="H2.TLabel").pack(anchor="w", padx=10, pady=(8, 0))

        mid = ttk.Frame(self, style="Screen.TFrame"); mid.pack(expand=True)
        card = ttk.Frame(mid, style="Card.TFrame", padding=16); card.pack(pady=(32, 18))
        ttk.Label(card, text="Write order numbers to produce files:", style="H2.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        ttk.Label(card, text="From:", style="Label.TLabel").grid(row=1, column=0, padx=(0, 8))
        self.from_var = tk.StringVar(value=state.order_from)
        ttk.Entry(card, textvariable=self.from_var, width=12, justify="center").grid(row=1, column=1, padx=(0, 28))

        ttk.Label(card, text="To:", style="Label.TLabel").grid(row=1, column=2, padx=(0, 8))
        self.to_var = tk.StringVar(value=state.order_to)
        ttk.Entry(card, textvariable=self.to_var, width=12, justify="center").grid(row=1, column=3)

        self.bottom_nav(self, on_back=self.app.go_back, on_next=self._start, next_text="Start")

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
        self.app.show_screen(Screen1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = App(title=APP_TITLE)
    app.show_screen(LauncherSelectProduct)
    app.mainloop()