import tkinter as tk
from tkinter import messagebox, filedialog

from src.core import Screen, warn, COLOR_TEXT, COLOR_BG_LIGHT, COLOR_BG_SCREEN, COLOR_BG_DARK, COLOR_PILL, UI_SCALE, scale_px
from src.core.state import state
from src.utils import *
from .define_image import StickerDefineImageScreen


class StickerMajorSizesScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.brand_bar(self)
        self.app = app

        self.pack(fill="both", expand=True)

        tk.Label(self,
                 text=state.sku_name,
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))

        header = create_pill_label(
            PillLabelInfo(
                parent=self,
                text_info=TextInfo(
                    text="Sizes for major variations",
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

        # Build scroll area and render rows
        self._ensure_sizes_scroll_area()
        try:
            self.sizes_container.place(relx=0.5, rely=0.25, anchor="n", width=850, height=450)
        except Exception:
            self.sizes_container.place(relx=0.5, rely=0.25, anchor="n")
        self._render_size_rows()

        def _proceed_button():
            def _on_proceed():
                for i in range(len(state.major_sizes)):
                    x, y, file_path = state.major_sizes[i]
                    x_entry, y_entry = self.size_entry_objs[i]
                    if not file_path:
                        state.major_sizes[i] = (x_entry.get().strip(), y_entry.get().strip(), file_path)

                zero_id = []
                file_path_id = []
                for i, (x, y, file_path) in enumerate(state.major_sizes):
                    if not x.strip() or not y.strip():
                        zero_id.append(i)
                        continue

                    try:
                        x = int(x)
                        y = int(y)
                    except Exception:
                        zero_id.append(i)
                        continue

                    if x <= 0 or y <= 0:
                        zero_id.append(i)
                        continue

                    if not file_path:
                        file_path_id.append(i)
                        continue

                if zero_id:
                    messagebox.showwarning("Incorrect sizes", f"Please set correct sizes for: {', '.join(str(i + 1) for i in zero_id)}")
                    return

                if file_path_id:
                    messagebox.showwarning("Incorrect files", f"Please import vector files for: {', '.join(str(i + 1) for i in file_path_id)}")
                    return

                # state.major_sizes = [(x.get(), y.get(), file_path) for x, y, file_path in self.size_entry_objs]
                self.app.show_screen(StickerDefineImageScreen)

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
        x, y = self.size_entry_objs[idx]
        if not x.get().strip() or not y.get().strip():
            warn(f"Please enter a major size {idx+1} before importing!", title="Missing major size")
            return

        file_path = filedialog.askopenfilename(filetypes=[("Vector files", "*.svg")])
        if not file_path:
            return

        state.major_sizes[idx] = (x.get().strip(), y.get().strip(), file_path)
        # Update the Upload button to an Uploaded disabled state
        btn_canvas = self.size_upload_buttons[idx]

        self.size_entry_objs[idx][0].configure(state="disabled")
        self.size_entry_objs[idx][1].configure(state="disabled")
        
        self._mark_button_uploaded(btn_canvas)

    def _ensure_sizes_scroll_area(self):
        if getattr(self, "sizes_container", None):
            return
        self.sizes_container = tk.Frame(self, bg=COLOR_BG_SCREEN)
        self.sizes_container.configure(width=750, height=380)
        self.sizes_canvas = tk.Canvas(self.sizes_container, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
        self.sizes_vsb = tk.Scrollbar(self.sizes_container, orient="vertical", command=self.sizes_canvas.yview)
        self.sizes_canvas.configure(yscrollcommand=self.sizes_vsb.set)
        self.sizes_canvas.pack(side="left", fill="both", expand=True)
        self.sizes_vsb.pack(side="right", fill="y")
        self.sizes_inner = tk.Frame(self.sizes_canvas, bg=COLOR_BG_SCREEN)
        self.sizes_canvas_window = self.sizes_canvas.create_window((0, 0), window=self.sizes_inner, anchor="nw")

        def _update_scrollbar_visibility():
            bbox = self.sizes_canvas.bbox("all")
            view_h = int(self.sizes_canvas.winfo_height())
            total_h = 0 if not bbox else max(0, int(bbox[3] - bbox[1]))
            has_overflow = total_h > view_h
            if has_overflow:
                if not self.sizes_vsb.winfo_ismapped():
                    self.sizes_vsb.pack(side="right", fill="y")
                self.sizes_canvas.configure(yscrollcommand=self.sizes_vsb.set)
            else:
                self.sizes_canvas.configure(yscrollcommand=(lambda *_a: None))
                if self.sizes_vsb.winfo_ismapped():
                    self.sizes_vsb.pack_forget()
                self.sizes_canvas.yview_moveto(0.0)

        def _on_inner_configure(_e=None):
            self.sizes_canvas.configure(scrollregion=self.sizes_canvas.bbox("all"))
            _update_scrollbar_visibility()
        self.sizes_inner.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(e):
            self.sizes_canvas.itemconfigure(self.sizes_canvas_window, width=int(e.width))
            _update_scrollbar_visibility()
        self.sizes_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            try:
                delta = int(getattr(e, "delta", 0))
            except Exception:
                delta = 0
            if delta == 0:
                return "break"
            bbox = self.sizes_canvas.bbox("all")
            view_h = int(self.sizes_canvas.winfo_height())
            total_h = 0 if not bbox else max(0, int(bbox[3] - bbox[1]))
            if total_h <= view_h:
                return "break"
            step = -1 if delta > 0 else 1
            self.sizes_canvas.yview_scroll(step * 3, "units")
            return "break"
        for w in (self.sizes_canvas, self.sizes_inner, self.sizes_container):
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
                if cur is self.sizes_container or cur is self.sizes_canvas or cur is self.sizes_inner:
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

    def _render_size_rows(self):
        self._ensure_sizes_scroll_area()
        for child in list(self.sizes_inner.winfo_children()):
            child.destroy()
        self.size_upload_buttons = []
        self.size_entry_objs = []

        total = max(1, int(getattr(state, "major_variations", 1) or 1))
        # Ensure state sizing
        if len(state.major_sizes) < total:
            state.major_sizes.extend([("", "", "")] * (total - len(state.major_sizes)))

        for i in range(total):
            row_info = PillLabelInfo(
                width=750,
                parent=self.sizes_inner,
                text_info=TextInfo(
                    text=f"Size {i+1}",
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
            row_pill, x_label_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill, 
                object_info=PillLabelInfo(
                    parent=row_pill,
                    text_info=TextInfo(
                        text="X:",
                        color=COLOR_TEXT,
                        font_size=24,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_x,
            )
            row_pill, x_canvas, x_entry_obj = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill, 
                object_info=EntryInfo(
                    parent=row_pill,
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
            row_pill, x_mm_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill, 
                object_info=PillLabelInfo(
                    parent=row_pill,
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
            base_y = -235
            row_pill, y_label_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill, 
                object_info=PillLabelInfo(
                    parent=row_pill,
                    text_info=TextInfo(
                        text="Y:",
                        color=COLOR_TEXT,
                        font_size=24,
                    ),
                    fill=COLOR_BG_LIGHT,
                ),
                object_padding_x=base_y,
            )
            row_pill, y_canvas, y_entry_obj = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill, 
                object_info=EntryInfo(
                    parent=row_pill,
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
            row_pill, y_mm_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill, 
                object_info=PillLabelInfo(
                    parent=row_pill,
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
            # Upload button
            row_pill, btn_canvas, _ = append_object_to_pill_label(
                row_info,
                pill_canvas=row_pill,
                object_info=ButtonInfo(
                    width=150,
                    parent=row_pill,
                    text_info=TextInfo(
                        text="     Import",
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
            self.size_upload_buttons.append(btn_canvas)
            self.size_entry_objs.append((x_entry_obj, y_entry_obj))

            # If already uploaded, reflect disabled state on button
            if i < len(state.major_sizes) and state.major_sizes[i][2]:
                self._mark_button_uploaded(btn_canvas)

            # pack row
            row_pill.pack_configure(pady=6, anchor="center")

        # Update scrollregion
        self.sizes_inner.update_idletasks()
        self.sizes_canvas.configure(scrollregion=self.sizes_canvas.bbox("all"))

    def _mark_button_uploaded(self, button_canvas: tk.Canvas) -> None:
        # Change text label to "Uploaded"
        button_canvas.itemconfig("btntxt", text="   Imported", fill="#228B22")
        # Gray out the button background
        button_canvas.itemconfig("btnbg", fill="#b3b3b3")
        # Disable interactions and change cursor
        for seq in ("<Enter>", "<Leave>", "<ButtonPress-1>", "<ButtonRelease-1>"):
            button_canvas.unbind(seq)
        button_canvas.configure(cursor="arrow")