import logging

import tkinter as tk

from src.core import Screen, vcmd_int, vcmd_float, warn, COLOR_PILL, COLOR_BG_SCREEN, COLOR_BG_DARK, COLOR_BG_SCREEN_FOR_LABELS, COLOR_TEXT, font_from_pt, scale_px
from src.core.app import COLOR_BG_LIGHT, UI_SCALE
from src.core.state import state
from src.utils import *
from .font_info import StickerFontInfoScreen


logger = logging.getLogger(__name__)

class StickerBasicInfoScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.brand_bar(self)
        self.app = app

        self.pack(fill="both", expand=True)

        tk.Label(self,
                 text="Add a new product",
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))
            
        # Body
        def _sku_input():
            def _on_sku_change():
                state.sku = self.sku_entry_obj.get()
                
            sku_info = PillLabelInfo(
                width=750,
                parent=self,
                text_info=TextInfo(
                    text="Give your SKU number:",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=12,
            )
            self.sku_number = create_pill_label(sku_info)
            self.sku_number, entry_canvas, self.sku_entry_obj = append_object_to_pill_label(
                sku_info,
                pill_canvas=self.sku_number, 
                object_info=EntryInfo(
                    parent=self.sku_number,
                    width=275,
                    text_info=TextInfo(
                        text="1324-2342-5433",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    radius=10,
                    fill=COLOR_PILL,
                    padding_x=5,
                    padding_y=5,
                ),
                object_padding_x=-50,
            )
            self.sku_number.place(relx=0.5, rely=0.25, anchor="center")

            self.sku_entry_obj.bind("<KeyRelease>", lambda _e: _on_sku_change())
            self.sku_entry_obj.bind("<FocusOut>", lambda _e: _on_sku_change())
            self.sku_entry_obj.bind("<Return>", lambda _e: _on_sku_change())
            self.sku_entry_obj.bind("<KP_Enter>", lambda _e: _on_sku_change())

        def _pkg_size_input():
            def _on_pkg_size_change():
                state.pkg_x = self.x_entry_obj.get()
                state.pkg_y = self.y_entry_obj.get()

            pkg_size_info = PillLabelInfo(
                width=750,
                parent=self,
                text_info=TextInfo(
                    text="Your package size:",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=12,
            )
            self.pkg_size_pill = create_pill_label(pkg_size_info)
            base_x = -230
            self.pkg_size_pill, x_label_canvas, _ = append_object_to_pill_label(
                pkg_size_info,
                pill_canvas=self.pkg_size_pill, 
                object_info=PillLabelInfo(
                    parent=self.pkg_size_pill,
                    text_info=TextInfo(
                        text="X:",
                        color=COLOR_TEXT,
                        font_size=24,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_x,
            )
            self.pkg_size_pill, x_canvas, self.x_entry_obj = append_object_to_pill_label(
                pkg_size_info,
                pill_canvas=self.pkg_size_pill, 
                object_info=EntryInfo(
                    parent=self.pkg_size_pill,
                    width=65,
                    text_info=TextInfo(
                        text="80",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    fill=COLOR_PILL,
                    radius=10,
                    padding_x=5,
                    padding_y=5
                ),
                object_padding_x=base_x + 60,
            )
            self.pkg_size_pill, x_mm_canvas, _ = append_object_to_pill_label(
                pkg_size_info,
                pill_canvas=self.pkg_size_pill, 
                object_info=PillLabelInfo(
                    parent=self.pkg_size_pill,
                    text_info=TextInfo(
                        text="mm",
                        color=COLOR_TEXT,
                        font_size=15,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_x + 73,
                object_padding_y=4,
            )
            base_y = -120
            self.pkg_size_pill, y_label_canvas, _ = append_object_to_pill_label(
                pkg_size_info,
                pill_canvas=self.pkg_size_pill, 
                object_info=PillLabelInfo(
                    parent=self.pkg_size_pill,
                    text_info=TextInfo(
                        text="Y:",
                        color=COLOR_TEXT,
                        font_size=24,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_y,
            )
            self.pkg_size_pill, y_canvas, self.y_entry_obj = append_object_to_pill_label(
                pkg_size_info,
                pill_canvas=self.pkg_size_pill, 
                object_info=EntryInfo(
                    parent=self.pkg_size_pill,
                    width=75,
                    text_info=TextInfo(
                        text="80",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    radius=10,
                    fill=COLOR_PILL,
                    padding_x=5,
                    padding_y=5
                ),
                object_padding_x=base_y + 67,
            )
            self.pkg_size_pill, y_mm_canvas, _ = append_object_to_pill_label(
                pkg_size_info,
                pill_canvas=self.pkg_size_pill, 
                object_info=PillLabelInfo(
                    parent=self.pkg_size_pill,
                    text_info=TextInfo(
                        text="mm",
                        color=COLOR_TEXT,
                        font_size=15,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_y + 80,
                object_padding_y=4,
            )
            y = self.sku_number.winfo_height() + 15
            self.pkg_size_pill.place(relx=0.5, rely=0.25, y=y, anchor="center")

            self.x_entry_obj.bind("<KeyRelease>", lambda _e: _on_pkg_size_change())
            self.x_entry_obj.bind("<FocusOut>", lambda _e: _on_pkg_size_change())
            self.x_entry_obj.bind("<Return>", lambda _e: _on_pkg_size_change())
            self.x_entry_obj.bind("<KP_Enter>", lambda _e: _on_pkg_size_change())

            self.y_entry_obj.bind("<KeyRelease>", lambda _e: _on_pkg_size_change())
            self.y_entry_obj.bind("<FocusOut>", lambda _e: _on_pkg_size_change())
            self.y_entry_obj.bind("<Return>", lambda _e: _on_pkg_size_change())
            self.y_entry_obj.bind("<KP_Enter>", lambda _e: _on_pkg_size_change())

        def _ensure_variations_scroll_area():
            if getattr(self, "variations_container", None):
                return
            self.variations_container = tk.Frame(self, bg=COLOR_BG_SCREEN)
            # Fixed viewport size; content will scroll
            self.variations_container.configure(width=750, height=280)
            self.variations_canvas = tk.Canvas(self.variations_container, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
            self.variations_vsb = tk.Scrollbar(self.variations_container, orient="vertical", command=self.variations_canvas.yview)
            self.variations_canvas.configure(yscrollcommand=self.variations_vsb.set)
            self.variations_canvas.pack(side="left", fill="both", expand=True)
            self.variations_vsb.pack(side="right", fill="y")
            self.variations_inner = tk.Frame(self.variations_canvas, bg=COLOR_BG_SCREEN)
            self.variations_canvas_window = self.variations_canvas.create_window((0, 0), window=self.variations_inner, anchor="nw")

            def _update_scrollbar_visibility():
                bbox = self.variations_canvas.bbox("all")
                view_h = int(self.variations_canvas.winfo_height())
                total_h = 0 if not bbox else max(0, int(bbox[3] - bbox[1]))
                has_overflow = total_h > view_h
                if has_overflow:
                    if not self.variations_vsb.winfo_ismapped():
                        self.variations_vsb.pack(side="right", fill="y")
                    self.variations_canvas.configure(yscrollcommand=self.variations_vsb.set)
                else:
                    self.variations_canvas.configure(yscrollcommand=(lambda *_a: None))
                    if self.variations_vsb.winfo_ismapped():
                        self.variations_vsb.pack_forget()
                    self.variations_canvas.yview_moveto(0.0)

            def _on_inner_configure(_e=None):
                self.variations_canvas.configure(scrollregion=self.variations_canvas.bbox("all"))
                _update_scrollbar_visibility()
            self.variations_inner.bind("<Configure>", _on_inner_configure)

            def _on_canvas_configure(e):
                self.variations_canvas.itemconfigure(self.variations_canvas_window, width=int(e.width))
                _update_scrollbar_visibility()
            self.variations_canvas.bind("<Configure>", _on_canvas_configure)

            def _on_mousewheel(e):
                try:
                    delta = int(getattr(e, "delta", 0))
                except Exception:
                    delta = 0
                if delta == 0:
                    return "break"
                bbox = self.variations_canvas.bbox("all")
                view_h = int(self.variations_canvas.winfo_height())
                total_h = 0 if not bbox else max(0, int(bbox[3] - bbox[1]))
                if total_h <= view_h:
                    return "break"
                step = -1 if delta > 0 else 1
                self.variations_canvas.yview_scroll(step * 3, "units")
                return "break"
            for w in (self.variations_canvas, self.variations_inner, self.variations_container):
                w.bind("<MouseWheel>", _on_mousewheel)

            # Global handler to capture scroll over child widgets
            def _on_global_mousewheel(e):
                try:
                    x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
                    widget = self.winfo_containing(x_root, y_root)
                except Exception:
                    widget = None
                # Determine if pointer is over the variations container or its descendants
                cur = widget
                is_inside = False
                while cur is not None:
                    if cur is self.variations_container or cur is self.variations_canvas or cur is self.variations_inner:
                        is_inside = True
                        break
                    try:
                        cur = cur.master
                    except Exception:
                        cur = None
                if not is_inside:
                    return
                return _on_mousewheel(e)
            try:
                self.app.bind_all("<MouseWheel>", _on_global_mousewheel, add=True)
            except Exception:
                pass

        def _render_variations(count: int):
            _ensure_variations_scroll_area()
            count = int(count) if isinstance(count, (int,)) else 1
            if count <= 0:
                count = 1
            # Clear existing rows
            for child in list(self.variations_inner.winfo_children()):
                child.destroy()
            # Track entry widgets for state updates
            self.variation_entries = []

            def _update_variation_counts_from_entries():
                values = []
                for ent in getattr(self, "variation_entries", []):
                    try:
                        text = ent.get().strip()
                        values.append(int(text) if text else 0)
                    except Exception:
                        values.append(0)
                state.variation_design_counts = values
                
            # Build rows
            existing_counts = list(getattr(state, "variation_design_counts", []) or [])
            for i in range(count):
                variation_info = PillLabelInfo(
                    width=600,
                    parent=self.variations_inner,
                    text_info=TextInfo(
                        text=f"Variation {i+1} Designs total:",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    fill=COLOR_BG_LIGHT,
                    background_color=COLOR_BG_SCREEN,
                    radius=15,
                    padding_x=20,
                    padding_y=12,
                )
                pill = create_pill_label(variation_info)
                # Append entry on the right
                default_text = str(existing_counts[i]) if i < len(existing_counts) else "4"
                pill, _variation_canvas, _variation_entry = append_object_to_pill_label(
                    variation_info,
                    pill_canvas=pill,
                    object_info=EntryInfo(
                        parent=pill,
                        width=100,
                        text_info=TextInfo(
                            text=default_text,
                            color=COLOR_TEXT,
                            font_size=22,
                        ),
                        radius=10,
                        fill=COLOR_PILL,
                        padding_x=25,
                        padding_y=5
                    ),
                    object_padding_x=-45,
                )
                pill.pack_configure(pady=6, anchor="center")
                # Save entry and bind updates
                if _variation_entry is not None:
                    self.variation_entries.append(_variation_entry)
                    for seq in ("<KeyRelease>", "<FocusOut>", "<Return>", "<KP_Enter>"):
                        _variation_entry.bind(seq, lambda _e: _update_variation_counts_from_entries())
            # Ensure scrollregion updates
            self.variations_inner.update_idletasks()
            self.variations_canvas.configure(scrollregion=self.variations_canvas.bbox("all"))
            # Initialize state after render
            _update_variation_counts_from_entries()

        def _on_major_variations_change():
            try:
                raw = self.size_variations_entry.get()
                n = int(raw) if raw.strip() else 1
            except Exception:
                n = 1
            state.major_variations = max(1, n)
            _render_variations(max(1, n))

        def _size_variations_input():
            size_variations_info = PillLabelInfo(
                width=750,
                parent=self,
                text_info=TextInfo(
                    text="Number of size variations:",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=12,
            )
            self.size_variations_pill = create_pill_label(size_variations_info)
            self.size_variations_pill, size_variations_canvas, size_variations_entry_obj = append_object_to_pill_label(
                size_variations_info,
                pill_canvas=self.size_variations_pill, 
                object_info=EntryInfo(
                    parent=self.size_variations_pill,
                    width=100,
                    text_info=TextInfo(
                        text="3",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    radius=10,
                    fill=COLOR_PILL,
                    padding_x=25,
                    padding_y=5
                ),
                object_padding_x=-95,
            )
            # Keep reference to entry to drive dynamic list size
            self.size_variations_entry = size_variations_entry_obj
            # Alias for clarity when accessing major variations entry elsewhere
            self.major_variations_entry = self.size_variations_entry
            y = self.pkg_size_pill.winfo_height() + 85
            self.size_variations_pill.place(relx=0.5, rely=0.25, y=y, anchor="center")
            # React to changes
            self.size_variations_entry.bind("<KeyRelease>", lambda _e: _on_major_variations_change())
            self.size_variations_entry.bind("<FocusOut>", lambda _e: _on_major_variations_change())

        def _variation_input():
            _ensure_variations_scroll_area()
            # Position the scroll viewport under the count input
            self.update_idletasks()
            y = self.size_variations_pill.winfo_height() + 125
            try:
                self.variations_container.place(relx=0.5, rely=0.25, y=y, anchor="n", width=750, height=220)
            except Exception:
                self.variations_container.place(relx=0.5, rely=0.25, y=y, anchor="n")
            # Initial render
            _on_major_variations_change()

        def _fonts_total_input():
            def _on_fonts_total_change():
                total = self.fonts_total_entry_obj.get()
                state.font_variations_total = 1 if total.strip() else int(self.fonts_total_entry_obj.get())

            fonts_total_info = PillLabelInfo(
                width=750,
                parent=self,
                text_info=TextInfo(
                    text="Total fonts Variations:",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=12,
            )
            self.fonts_total_pill = create_pill_label(fonts_total_info)
            self.fonts_total_pill, fonts_total_canvas, self.fonts_total_entry_obj = append_object_to_pill_label(
                fonts_total_info,
                pill_canvas=self.fonts_total_pill,
                object_info=EntryInfo(
                    parent=self.fonts_total_pill,
                    width=100,
                    text_info=TextInfo(
                        text="7",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    radius=10,
                    fill=COLOR_PILL,
                    padding_x=25,
                    padding_y=5
                ),
                object_padding_x=-95,
            )
            self.fonts_total_entry = self.fonts_total_entry_obj
            y = self.size_variations_pill.winfo_height() + 385
            self.fonts_total_pill.place(relx=0.5, rely=0.25, y=y, anchor="center")

            self.fonts_total_entry_obj.bind("<KeyRelease>", lambda _e: _on_fonts_total_change())
            self.fonts_total_entry_obj.bind("<FocusOut>", lambda _e: _on_fonts_total_change())
            self.fonts_total_entry_obj.bind("<Return>", lambda _e: _on_fonts_total_change())
            self.fonts_total_entry_obj.bind("<KP_Enter>", lambda _e: _on_fonts_total_change())

        def _proceed_button():
            button = create_button(
                ButtonInfo(
                    parent=self,
                    text_info=TextInfo(
                        text="Proceed",
                        color=COLOR_TEXT,
                        font_size=22,
                    ),
                    button_color=COLOR_BG_DARK,
                    hover_color="#3f3f3f",
                    active_color=COLOR_BG_DARK,
                    padding_x=20,
                    padding_y=12,
                    command=self._on_proceed,
                )
            )
            button.place(relx=0.995, rely=0.99, anchor="se")

        _sku_input()
        _pkg_size_input()
        _size_variations_input()
        _variation_input()
        _fonts_total_input()
        _proceed_button()

    # -------- logic ----------
    def _on_proceed(self):
        # 1) SKU isn't empty
        sku_val = ""
        try:
            sku_val = self.sku_entry_obj.get().strip()
        except Exception:
            sku_val = str(getattr(state, "sku", "") or "").strip()
        if not sku_val:
            warn("Please enter an SKU before proceeding.", title="Missing SKU")
            return

        # 2) Package size > 0 (both X and Y)
        try:
            x_txt = self.x_entry_obj.get().strip()
            y_txt = self.y_entry_obj.get().strip()
            x_val = float(x_txt)
            y_val = float(y_txt)
        except Exception:
            warn("Package size X and Y must be numbers > 0.", title="Invalid size")
            return
        if x_val <= 0 or y_val <= 0:
            warn("Package size X and Y must be > 0.", title="Invalid size")
            return

        # 3) Number of size variations > 0
        try:
            major_txt = self.size_variations_entry.get().strip()
            major_count = int(major_txt)
        except Exception:
            warn("Number of size variations must be an integer > 0.", title="Invalid variations")
            return
        if major_count <= 0:
            warn("Number of size variations must be > 0.", title="Invalid variations")
            return

        # 4) Each variant design total > 0
        counts: list[int] = []
        try:
            for ent in getattr(self, "variation_entries", [])[:major_count]:
                try:
                    txt = ent.get().strip()
                    val = int(txt)
                except Exception:
                    val = 0
                if val <= 0:
                    warn("Each variation design total must be an integer > 0.", title="Invalid design totals")
                    return
                counts.append(val)
        except Exception:
            warn("Please enter design totals for each variation.", title="Missing design totals")
            return

        if len(counts) < int(major_count):
            warn("Please enter design totals for each variation.", title="Missing design totals")
            return

        # 5) Fonts variations > 0
        try:
            fonts_txt = self.fonts_total_entry_obj.get().strip()
            fonts_total = int(fonts_txt)
        except Exception:
            warn("Total fonts Variations must be an integer > 0.", title="Invalid fonts total")
            return
        if fonts_total <= 0:
            warn("Total fonts Variations must be > 0.", title="Invalid fonts total")
            return

        # Persist validated values
        state.sku = sku_val
        state.pkg_x = str(x_val)
        state.pkg_y = str(y_val)
        state.major_variations = int(major_count)
        state.variation_design_counts = counts
        state.font_variations_total = int(fonts_total)

        # Proceed
        self.app.show_screen(StickerFontInfoScreen)