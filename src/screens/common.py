import logging

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog

from src.state import state, ALL_PRODUCTS, APP_TITLE, IMAGES_PATH
from src.core import Screen, COLOR_BG_DARK, COLOR_BG_SCREEN, COLOR_PILL, COLOR_TEXT, COLOR_CARD
from .sticker import Screen2, _write_minimal_pdf

# ---------- UI constants ----------
UI_SCALE = 1.0
DPI_PX_PER_INCH = 96

def scale_px(value: float) -> int:
    """Scale pixel values by UI_SCALE with rounding."""
    return int(round(value * UI_SCALE))


def font_from_pt(pt_value: float) -> tkfont.Font:
    px = int(round((pt_value * UI_SCALE) * DPI_PX_PER_INCH / 72.0))
    return tkfont.Font(family="Myriad Pro", size=-px)


class SelectProductScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self._popup_just_opened = False
        self._suppress_auto_open = False

        title = tk.Frame(self, bg=COLOR_BG_DARK, height="31p"); title.pack(fill="x")
        title.pack_propagate(False)
        tk.Label(title, text=APP_TITLE, bg=COLOR_BG_DARK, fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
                 .pack(side="left", padx=scale_px(8), pady=0)

        mid = tk.Frame(self, bg=COLOR_BG_SCREEN); mid.pack(expand=True, fill="both")
        label_select = tk.Label(mid, text="Select product:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))

        DPI_PX_PER_INCH = float(self.winfo_fpixels("1i"))

        self.product_var = tk.StringVar(value=state.saved_product)
        cb_font = font_from_pt(21.8)
        cb_font_metrics = tkfont.Font(font=cb_font)

        try:
            self._combo_max_text_px = max(
                (cb_font_metrics.measure(p) for p in ALL_PRODUCTS),
                default=cb_font_metrics.measure(self.product_var.get())
            )
        except Exception:
            self._combo_max_text_px = cb_font_metrics.measure(self.product_var.get())
        cb_height_px = int(cb_font_metrics.metrics("linespace") + scale_px(20))
        text_canvas_w = self._combo_max_text_px + scale_px(8) * 2
        combo_w = text_canvas_w + cb_height_px
        self._SEARCH_W = combo_w + cb_height_px + scale_px(12)
        self._SEARCH_H = cb_height_px

        def _mark_popup_opened():
            self._popup_just_opened = True
            self.after(0, lambda: setattr(self, "_popup_just_opened", False))

        def _is_descendant(widget, ancestor):
            try:
                w = widget
                while w is not None:
                    if w is ancestor:
                        return True
                    w = w.master
            except Exception:
                pass
            return False
        
        # State for expanded search field
        self._expanded = False

        def _draw_search_canvas(show_underline: bool, expanded: bool = None):
            s_w, s_h = self._SEARCH_W, self._SEARCH_H
            cnv = self.search_canvas
            cnv.configure(width=s_w, height=s_h)
            cnv.delete("all")

            r = s_h // 2
            x1, y1, x2, y2 = 0, 0, s_w, s_h
            if expanded is None:
                expanded = getattr(self, "_expanded", False)
            if not expanded:
                cnv.create_rectangle(x1 + r, y1, x2 - r, y2, fill=COLOR_PILL, outline="")
                cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=COLOR_PILL, outline="")
                cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=COLOR_PILL, outline="")
            else:
                cnv.create_rectangle(x1, y1 + r, x2, y2, fill=COLOR_PILL, outline="")
                cnv.create_rectangle(x1 + r, y1, x2 - r, y1 + r, fill=COLOR_PILL, outline="")
                cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=COLOR_PILL, outline="")
                cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=COLOR_PILL, outline="")

            def _load_png_scaled(path: str, target_h: int):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(path).convert("RGBA")
                    target_w = max(1, int(round(img.width * (target_h / max(1, img.height)))))
                    img = img.resize((target_w, target_h), Image.LANCZOS)
                    return ImageTk.PhotoImage(img)
                except Exception:
                    base = tk.PhotoImage(file=path)
                    factor = max(1, int(round(base.height() / max(1, target_h))))
                    return base.subsample(factor, factor) if factor > 1 else base

            try:
                loupe_h = max(12, int(round(s_h * 0.60)))
                if not hasattr(self, "_loupe_img") or getattr(self, "_loupe_img_h", 0) != loupe_h:
                    self._loupe_img = _load_png_scaled(str(IMAGES_PATH / "loupe.png"), loupe_h)
                    self._loupe_img_h = loupe_h
            except Exception:
                self._loupe_img = None

            left_pad = max(scale_px(12), r - scale_px(6))
            ul_x1 = left_pad + 10
            if self._loupe_img:
                cnv.create_image(left_pad, s_h // 2, image=self._loupe_img, anchor="w")

                icon_w = int(self._loupe_img.width()) if self._loupe_img else 0
                ul_x1 = left_pad + icon_w + 10
            ul_x2 = s_w - scale_px(24)

            entry_h = max(18, int(round(s_h * 0.56)))
            entry_y = (s_h - entry_h) // 2 - 2
            self.search_entry.configure(borderwidth=0, highlightthickness=0,
                                        bg=COLOR_PILL, fg=COLOR_TEXT, insertbackground=COLOR_TEXT)
            self.search_entry.place(in_=cnv, x=ul_x1 + 2, y=entry_y,
                                    width=(ul_x2 - ul_x1 - 4), height=entry_h)

            if show_underline:
                uy = entry_y + entry_h + 3
                line_th = scale_px(4)
                cnv.create_rectangle(ul_x1, uy - (line_th // 2),
                                    ul_x2, uy + (line_th // 2),
                                    fill=COLOR_TEXT, outline="")
            return s_w, s_h

        self._combo_popup = None
        self._popup_items = []
        self._popup_anchor = None  # 'search' | 'combo'

        def _close_popup():
            try:
                if self._combo_popup and self._combo_popup.winfo_exists():
                    self._combo_popup.destroy()
            except Exception:
                pass
            finally:
                self._combo_popup = None
                self._popup_anchor = None
                try:
                    if hasattr(self, "_search_trace_id"):
                        self.search_var.trace_remove("write", self._search_trace_id)
                        del self._search_trace_id
                except Exception:
                    pass
                self._expanded = False
                try:
                    _draw_search_canvas(show_underline=False, expanded=False)
                except Exception:
                    pass

                try:
                    self.unbind_all("<Button-1>")
                except Exception:
                    pass

        def _open_popup(anchor_widget: tk.Widget, mode: str):
            """mode: 'search' → substring filter; 'combo' → prefix filter."""
            try:
                if self._combo_popup and self._combo_popup.winfo_exists():
                    self._combo_popup.destroy()
                self._combo_popup = tk.Toplevel(self)
                self._combo_popup.overrideredirect(True)
                self._combo_popup.configure(bg=COLOR_BG_SCREEN)
                self._popup_anchor = mode

                rx = anchor_widget.winfo_rootx()
                ry = anchor_widget.winfo_rooty() + anchor_widget.winfo_height()
                pw = anchor_widget.winfo_width()
                self._combo_popup.geometry(f"{pw}x200+{rx}+{ry}")

                SCREEN_BG = COLOR_BG_SCREEN
                ITEM_BG = COLOR_PILL

                outer_self = self
                class CanvasList:
                    def __init__(self, parent):
                        self.canvas = tk.Canvas(parent, bg=SCREEN_BG, highlightthickness=0, bd=0)
                        self.canvas.pack(fill="both", expand=True)
                        self.items = []
                        self.selected_index = -1
                        self.row_h = int(cb_font_metrics.metrics("linespace") + scale_px(8))
                        self.vsb = tk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
                        self.canvas.configure(yscrollcommand=self.vsb.set)
                        self.canvas.bind("<MouseWheel>", self._on_wheel)
                        self.canvas.bind("<Button-4>", lambda _e: self._scroll(-1))
                        self.canvas.bind("<Button-5>", lambda _e: self._scroll(+1))

                    def set_items(self, items):
                        self.items = list(items)
                        if self.items:
                            self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))
                        else:
                            self.selected_index = -1
                        self._render()

                    def delete(self, *_a):
                        pass

                    def insert(self, *_a):
                        pass

                    def size(self):
                        return len(self.items)

                    def curselection(self):
                        return (self.selected_index,) if self.selected_index >= 0 else tuple()

                    def get(self, idx):
                        if isinstance(idx, (list, tuple)):
                            idx = idx[0] if idx else None
                        if idx is None:
                            return None
                        try:
                            return self.items[int(idx)]
                        except Exception:
                            return None

                    def selection_clear(self, *_a):
                        self.selected_index = -1
                        self._render()

                    def selection_set(self, idx):
                        try:
                            self.selected_index = int(idx)
                        except Exception:
                            self.selected_index = -1
                        self._render()

                    def activate(self, *_a):
                        pass

                    def see(self, *_a):
                        if self.selected_index < 0:
                            return
                        total_h = len(self.items) * self.row_h
                        if total_h <= 0:
                            return
                        try:
                            top_frac, _ = self.canvas.yview()
                            view_h = int(self.canvas.winfo_height())
                        except Exception:
                            return
                        top_px = int(top_frac * total_h)
                        item_top = self.selected_index * self.row_h
                        item_bottom = item_top + self.row_h
                        if item_top < top_px:
                            self.canvas.yview_moveto(item_top / float(total_h))
                        elif item_bottom > top_px + view_h:
                            self.canvas.yview_moveto(max(0.0, (item_bottom - view_h) / float(total_h)))

                    def nearest(self, y):
                        try:
                            cy = self.canvas.canvasy(y)
                            idx = int(cy // self.row_h)
                            return max(0, min(idx, max(0, len(self.items) - 1)))
                        except Exception:
                            return 0

                    def bind(self, seq, func):
                        self.canvas.bind(seq, func)

                    def unbind(self, seq):
                        self.canvas.unbind(seq)

                    def after(self, ms, func):
                        return self.canvas.after(ms, func)

                    def winfo_exists(self):
                        return self.canvas.winfo_exists()

                    def yview_moveto(self, fraction):
                        try:
                            self.canvas.yview_moveto(fraction)
                        except Exception:
                            pass

                    def _render(self):
                        c = self.canvas
                        c.delete("all")
                        try:
                            width = max(pw, int(c.winfo_width()))
                        except Exception:
                            width = pw
                        for i, text in enumerate(self.items):
                            y0 = i * self.row_h
                            if i > 0:
                                c.create_rectangle(0, y0 - scale_px(2), width, y0, fill=SCREEN_BG, outline=SCREEN_BG)
                            is_last = (i == len(self.items) - 1)
                            if not is_last:
                                c.create_rectangle(0, y0, width, y0 + self.row_h, fill=ITEM_BG, outline="")
                            else:
                                r = int(getattr(outer_self, "_SEARCH_H", self.row_h) // 2)
                                r = max(2, min(r, self.row_h // 2))
                                y1 = y0 + self.row_h
                                c.create_rectangle(0, y0, width, y1 - r, fill=ITEM_BG, outline="")
                                c.create_rectangle(r, y1 - r, width - r, y1, fill=ITEM_BG, outline="")
                                c.create_oval(0, y1 - 2 * r, 0 + 2 * r, y1, fill=ITEM_BG, outline="")
                                c.create_oval(width - 2 * r, y1 - 2 * r, width, y1, fill=ITEM_BG, outline="")
                            c.create_text(width // 2, y0 + self.row_h // 2, text=text, font=cb_font,
                                          fill="#000000", anchor="center")
                        total_h = max(0, len(self.items) * self.row_h)
                        c.configure(scrollregion=(0, 0, width, total_h))

                    def _scroll(self, rows):
                        total_h = len(self.items) * self.row_h
                        if total_h <= 0:
                            return
                        try:
                            top_frac, _ = self.canvas.yview()
                            view_h = int(self.canvas.winfo_height())
                        except Exception:
                            return
                        top_px = int(top_frac * total_h)
                        new_top_px = top_px + rows * self.row_h
                        new_top_px = max(0, min(new_top_px, max(0, total_h - view_h)))
                        self.canvas.yview_moveto(new_top_px / float(total_h))

                    def _on_wheel(self, e):
                        try:
                            delta = int(e.delta)
                        except Exception:
                            delta = 0
                        if delta == 0:
                            return "break"
                        self._scroll(-1 if delta > 0 else 1)
                        return "break"

                lb = CanvasList(self._combo_popup)

                def _filtered(q: str, mode: str):
                    ql = (q or "").strip().lower()
                    base = list(ALL_PRODUCTS)
                    if mode == "combo":
                        return base if not ql else [p for p in base if p.lower().startswith(ql)]
                    return base if not ql else [p for p in base if ql in p.lower()]

                def _populate():
                    try:
                        if (not self._combo_popup or
                            not self._combo_popup.winfo_exists() or
                            not lb.winfo_exists()):
                            return
                    except Exception:
                        return

                    items_full = _filtered(self.search_var.get(), mode)
                    self._popup_items = items_full
                    lb.set_items(items_full)

                    if items_full:
                        lb.selection_clear(0, "end")
                        lb.selection_set(0)
                        try:
                            lb.yview_moveto(0.0)
                        except Exception:
                            lb.see(0)
                    row_h = lb.row_h
                    max_rows = 10
                    h = max(1, min(max_rows, len(items_full))) * row_h
                    self._combo_popup.geometry(f"{pw}x{h}+{rx}+{ry}")

                _populate()
                self._expanded = True
                _draw_search_canvas(show_underline=True, expanded=True)
                _mark_popup_opened()

                def _close_if_outside(event):
                    if getattr(self, "_popup_just_opened", False):
                        return
                    if self._combo_popup and self._combo_popup.winfo_exists():
                        if _is_descendant(event.widget, self._combo_popup):
                            return
                    if _is_descendant(event.widget, self.search_canvas):
                        return
                    _close_popup()
                    try:
                        event.widget.focus_set()
                    except Exception:
                        pass

                self.bind_all("<Button-1>", _close_if_outside, add="+")

                def _on_search_change(*_a):
                    try:
                        self.after(0, _populate)
                    except Exception:
                        pass

                try:
                    self._search_trace_id = self.search_var.trace_add("write", lambda *_a: _on_search_change())
                except Exception:
                    pass

                def _apply_selection(do_proceed: bool):
                    try:
                        if not (self._combo_popup and self._combo_popup.winfo_exists() and lb.winfo_exists()):
                            return
                        sel_idx = lb.curselection()
                        sel = lb.get(sel_idx) if sel_idx else None
                    except Exception:
                        sel = None
                    if sel:
                        self.product_var.set(sel)
                        try:
                            self.search_var.set(sel)
                        except Exception:
                            pass
                        self._suppress_auto_open = True
                        _close_popup()
                        try:
                            self.after(200, lambda: setattr(self, "_suppress_auto_open", False))
                        except Exception:
                            self._suppress_auto_open = False
                        if do_proceed:
                            self._proceed()
                    else:
                        _close_popup()

                def _choose_press(evt):
                    try:
                        if not lb.winfo_exists():
                            return "break"
                        idx = lb.nearest(evt.y)
                        if idx is not None and idx >= 0:
                            lb.selection_clear(0, "end")
                            lb.selection_set(idx)
                            lb.activate(idx)
                            lb.see(idx)
                    except Exception:
                        pass
                    lb.after(1, lambda: _apply_selection(False))
                    return "break"

                lb.unbind("<ButtonRelease-1>")
                lb.bind("<Button-1>", _choose_press)
                lb.bind("<Return>", lambda _e: _apply_selection(False))
                lb.bind("<Escape>", lambda _e: _close_popup())

                def _nav(delta):
                    if not (self._combo_popup and self._combo_popup.winfo_exists()):
                        return
                    try:
                        cur = lb.curselection()
                        idx = (cur[0] if cur else -1) + delta
                        idx = max(0, min(idx, max(0, lb.size()-1)))
                        lb.selection_clear(0, "end"); lb.selection_set(idx); lb.activate(idx); lb.see(idx)
                    except Exception:
                        pass

                self.search_entry.bind("<Down>", lambda _e: (_nav(+1), "break"))
                self.search_entry.bind("<Up>",   lambda _e: (_nav(-1), "break"))
                self.search_entry.bind("<Return>", lambda _e: (_apply_selection(True), "break"))
                self.search_entry.bind("<Escape>", lambda _e: (_close_popup(), "break"))

            except Exception:
                pass

        def _ensure_search_popup(*_a):
            if getattr(self, "_suppress_auto_open", False):
                return
            if not (self._combo_popup and self._combo_popup.winfo_exists()):
                _open_popup(self.search_canvas, mode="search")
            elif self._popup_anchor != "search":
                _close_popup()
                _open_popup(self.search_canvas, mode="search")

        # ---------- Layout ----------
        def _position_select():
            try:
                y_label = int(mid.winfo_fpixels("54p"))
                label_select.place(relx=0.5, x=0, y=y_label, anchor="n")
                mid.update_idletasks()

                if not hasattr(self, "search_canvas"):
                    self.search_canvas = tk.Canvas(mid, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
                    self.search_var = tk.StringVar(value="")
                    self.search_entry = tk.Entry(mid, textvariable=self.search_var, relief="flat",
                                                 font=font_from_pt(16))

                y_search = label_select.winfo_y() + label_select.winfo_height() + int(mid.winfo_fpixels("10p"))
                s_w, s_h = _draw_search_canvas(show_underline=False)
                self.search_canvas.place(relx=0.5, x=0, y=y_search, anchor="n")
                if not getattr(self, "_search_bind_done", False):
                    self.search_entry.bind("<FocusIn>", lambda _e: _ensure_search_popup())
                    self.search_entry.bind("<Button-1>", lambda _e: _ensure_search_popup())
                    self.search_entry.bind("<KeyRelease>", lambda _e: _ensure_search_popup())
                    self.search_entry.bind("<Escape>", lambda _e: _close_popup())
                    self._search_bind_done = True
            except Exception:
                pass

        self.after_idle(_position_select)

        def _on_change(*_a):
            try:
                self.search_var.set(self.product_var.get())
            except Exception:
                pass
        self.product_var.trace_add("write", lambda *_a: _on_change())

        # ---------- Actions ----------

        add_text = "Add a new product"
        add_font_obj = font_from_pt(23.5)
        add_font = tkfont.Font(font=add_font_obj)
        add_tracking_px = 1.2
        add_char_widths = [add_font.measure(ch) for ch in add_text]
        add_text_width_px = sum(add_char_widths) + add_tracking_px * max(0, len(add_text) - 1)
        add_height_px = int(add_font.metrics("linespace") + scale_px(10))
        add_padding_lr = scale_px(8)
        add_width_px = int(add_text_width_px + add_padding_lr * 2)
        btn_add_canvas = tk.Canvas(self, width=add_width_px, height=add_height_px, bg=COLOR_BG_DARK,
                                   highlightthickness=0, bd=0, cursor="hand2")
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
            canvas.configure(bg=COLOR_BG_DARK)
            for tid in ids:
                canvas.move(tid, -1, -1)
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
        btn_add_canvas.place(relx=0.0, rely=1.0, x=scale_px(12), y=-scale_px(12), anchor="sw")

        update_text = "UPDATE EXISTING PRODUCT"
        update_font = font_from_pt(15.74)
        upd_font = tkfont.Font(font=update_font)
        tracking_px = -0.64
        char_widths = [upd_font.measure(ch) for ch in update_text]
        text_width_px = sum(char_widths) + tracking_px * max(0, len(update_text) - 1)
        upd_height_px = int(upd_font.metrics("linespace") + scale_px(20))
        padding_lr = scale_px(8)
        upd_width_px = int(text_width_px + padding_lr * 2)
        gap_px = scale_px(12)
        btn_update_canvas = tk.Canvas(self, width=upd_width_px, height=upd_height_px, bg=COLOR_BG_DARK,
                                      highlightthickness=0, bd=0, cursor="hand2")
        x_cursor = padding_lr
        y_center = upd_height_px // 2
        upd_text_ids = []
        for ch, cw in zip(update_text, char_widths):
            tid = btn_update_canvas.create_text(x_cursor, y_center, text=ch, font=update_font, fill=COLOR_TEXT, anchor="w")
            upd_text_ids.append(tid)
            x_cursor += cw + tracking_px
        def _upd_press(_e, canvas=btn_update_canvas, ids=upd_text_ids):
            canvas.configure(bg="#3f3f3f")
            for tid in ids:
                canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _upd_release(e, canvas=btn_update_canvas, ids=upd_text_ids):
            canvas.configure(bg=COLOR_BG_DARK)
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
        btn_update_canvas.place(relx=0.0, rely=1.0, x=scale_px(12), y=-(scale_px(12) + add_height_px + gap_px), anchor="sw")

        proceed_text = "Proceed"
        proceed_font_obj = font_from_pt(14.4)
        proceed_font = tkfont.Font(font=proceed_font_obj)
        proceed_width_px = int(proceed_font.measure(proceed_text) + scale_px(16))
        proceed_height_px = int(proceed_font.metrics("linespace") + scale_px(20))
        btn_proceed_canvas = tk.Canvas(self, width=proceed_width_px, height=proceed_height_px, bg=COLOR_BG_DARK,
                                       highlightthickness=0, bd=0, cursor="hand2")
        px_left = 8
        py_center = proceed_height_px // 2
        proc_text_id = btn_proceed_canvas.create_text(px_left, py_center, text=proceed_text, font=proceed_font_obj, fill=COLOR_TEXT, anchor="w")
        def _proc_press(_e, canvas=btn_proceed_canvas, tid=proc_text_id):
            canvas.configure(bg="#3f3f3f")
            canvas.move(tid, 1, 1)
            canvas._pressed = True
        def _proc_release(e, canvas=btn_proceed_canvas, tid=proc_text_id):
            canvas.configure(bg=COLOR_BG_DARK)
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
        btn_proceed_canvas.place(relx=1.0, rely=1.0, x=-scale_px(12), y=-scale_px(12), anchor="se")

    def _proceed(self):
        product = self.product_var.get()
        if not product:
            messagebox.showerror("Error", "Please select a product")
            return
        if product not in ALL_PRODUCTS:
            messagebox.showerror("Error", "Invalid product")
            return
        state.saved_product = product
        self.app.show_screen(OrderRangeScreen)

    def _add_new(self):
        logging.info("Starting new product flow (sticker/non-sticker chooser)")
        self.app.show_screen(ProductTypeScreen)


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
        self.app.show_screen(Screen2)

    def _show_non_sticker_screen(self):
        from .nonsticker import NScreen2
        self.app.show_screen(NScreen2)