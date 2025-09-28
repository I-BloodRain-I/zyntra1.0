import tkinter as tk
from tkinter import messagebox, filedialog

from src.core import Screen, warn, COLOR_TEXT, COLOR_BG_LIGHT, COLOR_BG_SCREEN, COLOR_BG_DARK, COLOR_PILL, UI_SCALE, scale_px
from src.core.state import state
from src.utils import *
from .sticker_copy import Screen4

class StickerFontInfoScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.brand_bar(self)
        self.app = app

        self.pack(fill="both", expand=True)

        tk.Label(self,
                 text=state.sku,
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))

        header = create_pill_label(
            PillLabelInfo(
                parent=self,
                text_info=TextInfo(
                    text="Upload all fonts",
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
        header.place(relx=0.5, rely=0.15, anchor="center")

        # Ensure state arrays are sized to total variations
        total = max(1, int(getattr(state, "font_variations_total", 1) or 1))
        if len(state.uploaded_fonts) < total:
            state.uploaded_fonts.extend([""] * (total - len(state.uploaded_fonts)))
        state.uploaded_fonts = [""] * total

        # Build scroll area and render rows
        self._ensure_fonts_scroll_area()
        try:
            self.fonts_container.place(relx=0.5, rely=0.25, anchor="n", width=850, height=450)
        except Exception:
            self.fonts_container.place(relx=0.5, rely=0.25, anchor="n")
        self._render_font_rows()

        def _proceed_button():
            def _on_proceed():
                if not all(state.uploaded_fonts):
                    missing = [str(i + 1) for i, ok in enumerate(state.uploaded_fonts) if not ok]
                    messagebox.showwarning("Upload required", f"Please upload all fonts: {', '.join(missing)}")
                    return
                self.app.show_screen(Screen4)

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
                    command=_on_proceed,
                )
            )
            button.place(relx=0.995, rely=0.99, anchor="se")

        _proceed_button()

    def _upload(self, idx):
        # Persist current name then mark as uploaded
        try:
            name_text = self.font_name_entries[idx].get().strip()
        except Exception:
            name_text = ""

        if not name_text:
            warn(f"Please enter a font {idx+1} name before uploading!", title="Missing font name")
            return

        file_path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf *.otf")])
        if not file_path:
            # warn(f"Please select a font {idx+1} file before uploading!", title="Missing font file")
            return

        state.uploaded_fonts[idx] = name_text
        # Update the Upload button to an Uploaded disabled state
        btn_canvas = self.font_upload_buttons[idx]

        self.font_name_entries[idx].configure(state="disabled")
        state.uploaded_fonts[idx] = (name_text, file_path)
        
        self._mark_button_uploaded(btn_canvas)

    def _ensure_fonts_scroll_area(self):
        if getattr(self, "fonts_container", None):
            return
        self.fonts_container = tk.Frame(self, bg=COLOR_BG_SCREEN)
        self.fonts_container.configure(width=750, height=380)
        self.fonts_canvas = tk.Canvas(self.fonts_container, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
        self.fonts_vsb = tk.Scrollbar(self.fonts_container, orient="vertical", command=self.fonts_canvas.yview)
        self.fonts_canvas.configure(yscrollcommand=self.fonts_vsb.set)
        self.fonts_canvas.pack(side="left", fill="both", expand=True)
        self.fonts_vsb.pack(side="right", fill="y")
        self.fonts_inner = tk.Frame(self.fonts_canvas, bg=COLOR_BG_SCREEN)
        self.fonts_canvas_window = self.fonts_canvas.create_window((0, 0), window=self.fonts_inner, anchor="nw")

        def _update_scrollbar_visibility():
            bbox = self.fonts_canvas.bbox("all")
            view_h = int(self.fonts_canvas.winfo_height())
            total_h = 0 if not bbox else max(0, int(bbox[3] - bbox[1]))
            has_overflow = total_h > view_h
            if has_overflow:
                if not self.fonts_vsb.winfo_ismapped():
                    self.fonts_vsb.pack(side="right", fill="y")
                self.fonts_canvas.configure(yscrollcommand=self.fonts_vsb.set)
            else:
                self.fonts_canvas.configure(yscrollcommand=(lambda *_a: None))
                if self.fonts_vsb.winfo_ismapped():
                    self.fonts_vsb.pack_forget()
                self.fonts_canvas.yview_moveto(0.0)

        def _on_inner_configure(_e=None):
            self.fonts_canvas.configure(scrollregion=self.fonts_canvas.bbox("all"))
            _update_scrollbar_visibility()
        self.fonts_inner.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(e):
            self.fonts_canvas.itemconfigure(self.fonts_canvas_window, width=int(e.width))
            _update_scrollbar_visibility()
        self.fonts_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            try:
                delta = int(getattr(e, "delta", 0))
            except Exception:
                delta = 0
            if delta == 0:
                return "break"
            bbox = self.fonts_canvas.bbox("all")
            view_h = int(self.fonts_canvas.winfo_height())
            total_h = 0 if not bbox else max(0, int(bbox[3] - bbox[1]))
            if total_h <= view_h:
                return "break"
            step = -1 if delta > 0 else 1
            self.fonts_canvas.yview_scroll(step * 3, "units")
            return "break"
        for w in (self.fonts_canvas, self.fonts_inner, self.fonts_container):
            w.bind("<MouseWheel>", _on_mousewheel)

        # Global handler to capture scroll over child widgets
        def _on_global_mousewheel(e):
            try:
                x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
                widget = self.winfo_containing(x_root, y_root)
            except Exception:
                widget = None
            cur = widget
            is_inside = False
            while cur is not None:
                if cur is self.fonts_container or cur is self.fonts_canvas or cur is self.fonts_inner:
                    is_inside = True
                    break
                try:
                    cur = cur.master
                except Exception:
                    cur = None
            if not is_inside:
                return
            return _on_mousewheel(e)

        self.app.bind_all("<MouseWheel>", _on_global_mousewheel, add=True)

    def _render_font_rows(self):
        self._ensure_fonts_scroll_area()
        for child in list(self.fonts_inner.winfo_children()):
            child.destroy()
        self.font_name_entries = []
        self.font_upload_buttons = []

        total = max(1, int(getattr(state, "font_variations_total", 1) or 1))
        # Ensure state sizing
        if len(state.uploaded_fonts) < total:
            state.uploaded_fonts.extend([""] * (total - len(state.uploaded_fonts)))
        if len(state.uploaded_fonts) < total:
            state.uploaded_fonts.extend([""] * (total - len(state.uploaded_fonts)))

        for i in range(total):
            row_info = PillLabelInfo(
                width=750,
                parent=self.fonts_inner,
                text_info=TextInfo(
                    text=f"Font {i+1}",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                fill=COLOR_BG_LIGHT,
                background_color=COLOR_BG_SCREEN,
                radius=15,
                padding_x=20,
                padding_y=12,
            )
            row_pill = create_pill_label(row_info)
            base_x = -350
            # Name label
            row_pill, _lbl_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill,
                object_info=PillLabelInfo(
                    parent=row_pill,
                    text_info=TextInfo(
                        text="Name",
                        color=COLOR_TEXT,
                        font_size=18,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_x,
                object_padding_y=-3,
            )
            # Subtitle
            row_pill, _sub_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill,
                object_info=PillLabelInfo(
                    parent=row_pill,
                    text_info=TextInfo(
                        text="(same as Amazon)",
                        color=COLOR_TEXT,
                        font_size=10,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_x,
                object_padding_y=10,
            )
            # Name entry
            default_text = state.uploaded_fonts[i] if i < len(state.uploaded_fonts) else ""
            row_pill, _entry_canvas, entry_widget = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill,
                object_info=EntryInfo(
                    parent=row_pill,
                    width=200,
                    text_info=TextInfo(
                        text=default_text or "",
                        color=COLOR_TEXT,
                        font_size=18,
                    ),
                    fill=COLOR_PILL,
                    radius=10,
                    padding_x=15,
                    padding_y=5,
                ),
                object_padding_x=base_x + 215,
            )
            if entry_widget is not None:
                self.font_name_entries.append(entry_widget)
            else:
                raise ValueError(f"Entry widget is None for font {i+1}")

            # Upload button
            row_pill, btn_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill,
                object_info=ButtonInfo(
                    width=150,
                    parent=row_pill,
                    text_info=TextInfo(
                        text="    Upload",
                        color=COLOR_TEXT,
                        font_size=18,
                        justify="left",
                    ),
                    button_color=COLOR_PILL,
                    hover_color="#3f3f3f",
                    active_color=COLOR_PILL,
                    radius=10,
                    padding_x=5,
                    padding_y=5,
                    command=lambda k=i: self._upload(k),
                ),
                object_padding_x=base_x + 330,
            )
            self.font_upload_buttons.append(btn_canvas)

            # If already uploaded, reflect disabled state on button
            if i < len(state.uploaded_fonts) and state.uploaded_fonts[i]:
                self._mark_button_uploaded(btn_canvas)

            # pack row
            row_pill.pack_configure(pady=6, anchor="center")

        # Update scrollregion
        self.fonts_inner.update_idletasks()
        self.fonts_canvas.configure(scrollregion=self.fonts_canvas.bbox("all"))

    def _mark_button_uploaded(self, button_canvas: tk.Canvas) -> None:
        # Change text label to "Uploaded"
        button_canvas.itemconfig("btntxt", text="   Uploaded", fill="#228B22")
        # Gray out the button background
        button_canvas.itemconfig("btnbg", fill="#b3b3b3")
        # Disable interactions and change cursor
        for seq in ("<Enter>", "<Leave>", "<ButtonPress-1>", "<ButtonRelease-1>"):
            button_canvas.unbind(seq)
        button_canvas.configure(cursor="arrow")