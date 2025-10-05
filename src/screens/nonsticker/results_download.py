import os
import shutil
import logging
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog

from src.core import Screen, COLOR_BG_DARK, COLOR_TEXT, COLOR_PILL, COLOR_BG_SCREEN, UI_SCALE, scale_px, COLOR_BG_SCREEN_FOR_LABELS
from src.core.app import TEMP_FOLDER
from src.core.state import state

logger = logging.getLogger(__name__)


class NStickerResultsDownloadScreen(Screen):
    """Non-sticker results screen exactly like the screenshot."""

    def __init__(self, master, app):
        super().__init__(master, app)

        # Top brand bar and left-top SKU pill like OrderRangeScreen
        self.brand_bar(self)
        tk.Label(self,
                 text=(state.sku_name or "—"),
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))

        # Center layout area (like OrderRangeScreen)
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
        content = tk.Frame(mid, bg=COLOR_BG_SCREEN)
        content.grid(row=1, column=1)

        # Compute uniform chip width so all labels start at same x
        chip_font = tkfont.Font(font=("Myriad Pro", 24))
        pad_px = 32
        self._chip_w = max(
            chip_font.measure("Co2 laser cut Jig"),
            chip_font.measure("Test File .pdf"),
            chip_font.measure("Test File Backside .pdf"),
        ) + pad_px
        self._chip_h = int(chip_font.metrics("linespace") + 20)

        # Three file rows with pill-style Download buttons
        self._file_row(content, "Cut Jig", lambda: self._download_pdf("jig")).pack(pady=(10, 8))
        # self._file_row(content, "Single Pattern", lambda: self._download_pdf("pattern")).pack(pady=(8, 8))
        self._file_row(content, "Test File Frontside", lambda: self._download_pdf("front")).pack(pady=(8, 8))
        self._file_row(content, "Test File Backside", lambda: self._download_pdf("back")).pack(pady=(8, 8))

        # Report row: left strip for "Report:", then dynamic status label
        report_row = tk.Frame(content, bg=COLOR_BG_SCREEN)
        report_row.pack(fill="x", pady=(16, 10))
        report_strip = tk.Frame(report_row, bg=COLOR_BG_SCREEN_FOR_LABELS)
        report_strip.pack(side="left", fill="x")
        tk.Label(report_strip, text="Report:", bg=COLOR_BG_SCREEN_FOR_LABELS, fg="#000000",
                 font=("Myriad Pro", 24)).pack(side="left", padx=(0, 8))
        self._status_value = tk.Label(
            report_row,
            text=("Processing" if getattr(state, "is_processing", False) else "Successful"),
            bg=COLOR_BG_SCREEN,
            fg=("#bbbbbb" if getattr(state, "is_processing", False) else "#6fe28f"),
            font=("Myriad Pro", 24),
        )
        self._status_value.pack(side="left", padx=(12, 0))

        # Totals row: left strip with the label, then value on screen bg
        totals_row = tk.Frame(content, bg=COLOR_BG_SCREEN)
        totals_row.pack(fill="x", pady=(6, 2))
        totals_strip = tk.Frame(totals_row, bg=COLOR_BG_SCREEN_FOR_LABELS)
        totals_strip.pack(side="left")
        tk.Label(totals_strip, text="Total items in 1 batch:", bg=COLOR_BG_SCREEN_FOR_LABELS, fg="#000000",
                 font=("Myriad Pro", 18)).pack(side="left")
        # Show count of image objects (from canvas)
        tk.Label(totals_row, text=f"{state.nonsticker_image_count} pcs", bg=COLOR_BG_SCREEN, fg="#000000",
                 font=("Myriad Pro", 18)).pack(side="left", padx=(8, 0))

        # Bottom-right "Back to home" dark button (no Go Back)
        next_text = "Back to home"
        next_font_obj = tkfont.Font(font=("Myriad Pro", 22))
        next_width_px = int(next_font_obj.measure(next_text) + scale_px(16))
        next_height_px = int(next_font_obj.metrics("linespace") + scale_px(20))
        btn_next_canvas = tk.Canvas(self, width=next_width_px, height=next_height_px, bg=COLOR_BG_DARK,
                                    highlightthickness=0, bd=0, cursor="hand2")
        nx_left = 8
        ny_center = next_height_px // 2
        next_text_id = btn_next_canvas.create_text(nx_left, ny_center, text=next_text, font=("Myriad Pro", 22), fill=COLOR_TEXT, anchor="w")
        state.saved_product = ""

        def _next_press(_e, canvas=btn_next_canvas, tid=next_text_id):
            canvas.configure(bg="#3f3f3f"); canvas.move(tid, 1, 1); canvas._pressed = True
        def _next_release(e, canvas=btn_next_canvas, tid=next_text_id):
            canvas.configure(bg=COLOR_BG_DARK); canvas.move(tid, -1, -1)
            try:
                w = canvas.winfo_width(); h = canvas.winfo_height(); inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(canvas, "_pressed", False) and inside:
                state.is_cancelled = True
                canvas.after(10, self._back_home)
            canvas._pressed = False
            
        btn_next_canvas.bind("<ButtonPress-1>", _next_press)
        btn_next_canvas.bind("<ButtonRelease-1>", _next_release)
        btn_next_canvas.place(relx=1.0, rely=1.0, x=-scale_px(12), y=-scale_px(12), anchor="se")

        # Apply initial processing state and start polling for completion
        try:
            self._apply_processing_state()
        except Exception:
            logger.exception("Failed to apply initial processing state")
        threading.Thread(target=self._poll_processing).start()

    # ---------- helpers ----------
    def _pill_button(self, parent, text: str, command):
        f_obj = tkfont.Font(font=("Myriad Pro", 14))
        pad_x = 16
        pad_y = 10
        w_px = int(f_obj.measure(text) + pad_x * 2)
        h_px = int(f_obj.metrics("linespace") + pad_y * 2)
        btn = tk.Canvas(parent, width=w_px, height=h_px, bg=COLOR_BG_SCREEN,
                        highlightthickness=0, bd=0, cursor="hand2")
        r = max(6, int(round(h_px * 0.5)))
        x1, y1, x2, y2 = 0, 0, w_px, h_px
        shapes = []
        shapes.append(btn.create_rectangle(x1 + r, y1, x2 - r, y2, fill=COLOR_PILL, outline=""))
        shapes.append(btn.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=COLOR_PILL, outline=""))
        shapes.append(btn.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=COLOR_PILL, outline=""))
        txt_id = btn.create_text(pad_x, h_px // 2, text=text, font=("Myriad Pro", 14), fill=COLOR_TEXT, anchor="w")
        # keep references for later enable/disable styling
        btn._shapes = shapes
        btn._txt_id = txt_id
        btn._fill_enabled = COLOR_PILL
        btn._fill_disabled = "#bdbdbd"
        btn._text_enabled = COLOR_TEXT
        btn._text_disabled = "#666666"

        def _press(_e):
            if getattr(btn, "_disabled", False):
                return
            for sid in shapes:
                btn.itemconfigure(sid, fill="#dcdcdc")
            btn.move(txt_id, 1, 1)
            btn._pressed = True

        def _release(e):
            if getattr(btn, "_disabled", False):
                btn._pressed = False
                return
            for sid in shapes:
                btn.itemconfigure(sid, fill=COLOR_PILL)
            btn.move(txt_id, -1, -1)
            try:
                w = btn.winfo_width(); h = btn.winfo_height()
                inside = 0 <= e.x <= w and 0 <= e.y <= h
            except Exception:
                inside = True
            if getattr(btn, "_pressed", False) and inside:
                try:
                    command()
                except Exception:
                    pass
            btn._pressed = False

        btn.bind("<ButtonPress-1>", _press)
        btn.bind("<ButtonRelease-1>", _release)
        btn._disabled = False
        return btn

    def _pill_label(self, parent, text: str):
        f_obj = tkfont.Font(font=("Myriad Pro", 12))
        pad_x = 12
        pad_y = 6
        w_px = int(f_obj.measure(text) + pad_x * 2)
        h_px = int(f_obj.metrics("linespace") + pad_y * 2)
        cnv = tk.Canvas(parent, width=w_px, height=h_px, bg=COLOR_BG_SCREEN, highlightthickness=0, bd=0)
        r = max(6, int(round(h_px * 0.5)))
        x1, y1, x2, y2 = 0, 0, w_px, h_px
        cnv.create_rectangle(x1 + r, y1, x2 - r, y2, fill=COLOR_PILL, outline="")
        cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=COLOR_PILL, outline="")
        cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=COLOR_PILL, outline="")
        cnv.create_text(pad_x, h_px // 2, text=text, font=("Myriad Pro", 12), fill=COLOR_TEXT, anchor="w")
        return cnv

    def _file_row(self, parent, label_text: str, command, small_note: str | None = None):
        row = ttk.Frame(parent, style="Screen.TFrame")
        # Fixed-width wrapper to ensure same x start; give explicit height to avoid collapse
        chip_wrap = tk.Frame(row, bg=COLOR_BG_DARK,
                             width=getattr(self, "_chip_w", 450),
                             height=getattr(self, "_chip_h", 48))
        chip_wrap.pack(side="left")
        chip_wrap.pack_propagate(False)
        chip = tk.Frame(chip_wrap, bg=COLOR_BG_SCREEN_FOR_LABELS)
        chip.pack(expand=True, fill="both")
        tk.Label(chip, text=label_text, bg=COLOR_BG_SCREEN_FOR_LABELS, fg="#000000",
                 font=("Myriad Pro", 24)).pack(padx=10, pady=10)
        col = ttk.Frame(row, style="Screen.TFrame")
        col.pack(side="left", padx=14)
        b = self._pill_button(col, "Download", command)
        b.pack()
        try:
            # Track for enabling/disabling
            if not hasattr(self, "_download_buttons"):
                self._download_buttons = []
            self._download_buttons.append(b)
        except Exception:
            logger.exception("Failed to register download button for state management")
        if small_note:
            tk.Label(col, text=small_note, bg=COLOR_BG_SCREEN_FOR_LABELS, fg="#333333",
                     font=("Myriad Pro", 10)).pack(pady=(4, 0))
        return row

    # ---------- actions ----------
    def _download_pdf(self, type: str):
        filename = ""
        if type == "jig":
            filename = "Cut_jig.svg"
        elif type == "front":
            filename = "Test_file_frontside.pdf"
        elif type == "back":
            filename = "Test_file_backside.pdf"
        elif type == "pattern":
            filename = "Single_pattern.svg"

        # Choose appropriate dialog based on file extension
        _, ext = os.path.splitext(filename)
        if ext.lower() == ".svg":
            fname = filedialog.asksaveasfilename(
                title="Save SVG File",
                defaultextension=".svg",
                filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
                initialfile=filename
            )
        else:
            fname = filedialog.asksaveasfilename(
                title="Save PDF File",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=filename
            )
        if not fname:
            return
        try:
            shutil.copy(os.path.join(TEMP_FOLDER, filename), fname)
            messagebox.showinfo("Saved", f"File saved to:\n{fname}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")
        return

    # ----- processing state management -----
    def _set_buttons_enabled(self, enabled: bool) -> None:
        try:
            for b in getattr(self, "_download_buttons", []):
                try:
                    b._disabled = not enabled
                    b.configure(cursor=("hand2" if enabled else "arrow"))
                    # apply visual style for disabled/enabled
                    fill = getattr(b, "_fill_enabled", COLOR_PILL) if enabled else getattr(b, "_fill_disabled", "#bdbdbd")
                    txt_col = getattr(b, "_text_enabled", COLOR_TEXT) if enabled else getattr(b, "_text_disabled", "#666666")
                    for sid in getattr(b, "_shapes", []):
                        try:
                            b.itemconfigure(sid, fill=fill)
                        except Exception:
                            logger.exception("Failed to update download button shape fill")
                    try:
                        b.itemconfigure(getattr(b, "_txt_id", None), fill=txt_col)
                    except Exception:
                        logger.exception("Failed to update download button text color")
                except Exception:
                    continue
        except Exception:
            logger.exception("Failed to enable/disable download buttons")

    def _apply_processing_state(self) -> None:
        processing = bool(getattr(state, "is_processing", False))
        text = state.processing_message if processing else (
            f"Failed: {state.error_message if state.error_message else "Unknown error"}" if state.is_failed else "Successful"
        )
        color = "#bbbbbb" if processing else (
            "#e50000" if state.is_failed else "#6fe28f"
        )
        logger.debug(f"Processing state: Processing=%s, Failed: %s, Text: %s, Color: %s", processing, state.is_failed, text, color)
        try:
            self._status_value.configure(text=text, fg=color)
        except Exception:
            logger.exception("Failed to update processing state")
        self._set_buttons_enabled(not processing and not state.is_failed)

    def _poll_processing(self) -> None:
        while True:
            try:
                self._apply_processing_state()
            except Exception:
                logger.exception("Failed to apply processing state in poll")

            if not state.is_processing:
                self._apply_processing_state()
                break
            time.sleep(1.0)
            
    def _back_home(self):
        state.sku = ""
        state.sku_name = ""
        state.saved_product = ""
        try:
            from src.screens.common.select_product import SelectProductScreen
            self.app.show_screen(SelectProductScreen)
        except Exception:
            self.app.go_back()