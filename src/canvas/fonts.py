from __future__ import annotations

import os
import json
import logging
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

from src.core import COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL
from src.core.app import COLOR_BG_SCREEN
from src.core.state import FONTS_PATH
from src.utils import create_button, ButtonInfo, TextInfo, create_entry, EntryInfo


logger = logging.getLogger(__name__)


class FontsManager:
    """Encapsulates font mapping, text controls UI, and font import/remove.

    Attaches UI elements and variables on the owning screen for compatibility:
    - screen.row_text, screen.text_bar
    - screen.text_size, screen.text_color, screen.text_family
    - screen._family_combo
    - screen._suppress_text_traces
    """

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen
        # Ensure fonts directory exists
        try:
            FONTS_PATH.mkdir(exist_ok=True)
        except Exception:
            logger.exception("Failed to ensure fonts directory exists")

        self._fonts_map_path = FONTS_PATH / "fonts.json"
        self._fonts_map = self._load_fonts_map()
        self._font_families = self._list_font_families(self._fonts_map)

        # Build UI (hidden by default). Attach to left sidebar if available
        parent_for_text = getattr(self.s, "left_bar", self.s)
        self.s.row_text = tk.Frame(parent_for_text, bg="black")
        self.s.text_bar = tk.Frame(self.s.row_text, bg="black")

        tk.Label(self.s.text_bar, text="Text:", fg="white", bg="black", font=("Myriad Pro", 12, "bold")).pack(side="top", anchor="w", padx=(60, 9))

        # Text size (pt)
        self.s.text_size = tk.StringVar(value="12")
        _size_line = tk.Frame(self.s.text_bar, bg="black"); _size_line.pack(side="top", anchor="w")
        _sb = self.s._chip(_size_line, "Size:", self.s.text_size, label_padx=15, width=11, pady=(8,0))
        tk.Label(_sb, text="pt", bg="#6f6f6f", fg="white").pack(side="left", padx=0)

        # Text color (hex)
        self.s.text_color = tk.StringVar(value="#ffffff")
        _color_line = tk.Frame(self.s.text_bar, bg="black"); _color_line.pack(side="top", anchor="w")
        _cb = self.s._chip(_color_line, "Color:", self.s.text_color, label_padx=10, width=14, pady=(8,0))
        # Bind color picker to the entry inside the chip
        try:
            entry_widget = None
            for _w in _cb.winfo_children():
                if isinstance(_w, tk.Entry):
                    entry_widget = _w
                    break
            if entry_widget is not None:
                def _open_color_picker(_e=None):
                    try:
                        initial = (self.s.text_color.get() or "#ffffff").strip()
                    except Exception:
                        initial = "#ffffff"
                    try:
                        _rgb, hx = colorchooser.askcolor(color=initial, title="Select color")
                    except Exception:
                        hx = None
                    if hx:
                        try:
                            self.s.text_color.set(hx)
                        except Exception:
                            pass
                    return "break"
                entry_widget.bind("<Button-1>", _open_color_picker)
        except Exception:
            logger.exception("Failed to bind color picker to color entry")
        # Family combobox
        fam_line = tk.Frame(self.s.text_bar, bg="black"); fam_line.pack(side="top", anchor="w")
        fam_wrap = tk.Frame(fam_line, bg="#6f6f6f")
        fam_wrap.pack(side="left", padx=6, pady=8)
        tk.Label(fam_wrap, text="Family:", bg="#6f6f6f", fg="white").pack(side="left", padx=6)
        default_family = (self._font_families[0] if self._font_families else "Myriad Pro")
        self.s.text_family = tk.StringVar(value=default_family)
        self.s._family_combo = ttk.Combobox(
            fam_wrap,
            textvariable=self.s.text_family,
            state="readonly",
            values=self._font_families,
            justify="center",
            width=12,
        )
        self.s._family_combo.pack(side="left")

        # Buttons line (Import/Remove) stacked below family
        btn_line = tk.Frame(self.s.text_bar, bg="black"); btn_line.pack(side="top", anchor="w")
        # Import font
        imp_btn = create_button(
            ButtonInfo(
                parent=btn_line,
                text_info=TextInfo(text="Import", color=COLOR_TEXT, font_size=10),
                command=self._on_import_font,
                background_color="#000000",
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_DARK,
                active_color=COLOR_PILL,
                padding_x=15,
                padding_y=4,
            )
        )
        imp_btn.pack(side="left", padx=(6, 4))

        # Remove font
        rem_btn = create_button(
            ButtonInfo(
                parent=btn_line,
                text_info=TextInfo(text="Remove", color=COLOR_TEXT, font_size=10),
                command=self._on_remove_font,
                background_color="#000000",
                button_color=COLOR_PILL,
                hover_color=COLOR_BG_DARK,
                active_color=COLOR_PILL,
                padding_x=12,
                padding_y=4,
            )
        )
        rem_btn.pack(side="left", padx=8)
        tk.Frame(self.s.text_bar, bg="white", height=2).pack(side="top", fill="x", padx=8, pady=(10, 6))

        # Initial hidden state
        try:
            self.s.text_bar.pack_forget()
            self.s.row_text.place_forget()
        except Exception:
            logger.exception("Failed to initially hide text controls")

        # Wire up live updates
        self.s._suppress_text_traces = False
        self.s.text_size.trace_add("write", self._apply_text_changes)
        self.s.text_color.trace_add("write", self._apply_text_changes)
        self.s._family_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_text_changes())

    # ---- Public delegates ----
    def find_font_path(self, family: str) -> Optional[str]:
        try:
            file_stem = str(self._fonts_map.get(family, "MyriadPro-Regular"))
        except Exception:
            file_stem = "MyriadPro-Regular"
        try:
            ttf = (FONTS_PATH / f"{file_stem}.ttf")
            if ttf.exists():
                return str(ttf)
            otf = (FONTS_PATH / f"{file_stem}.otf")
            if otf.exists():
                return str(otf)
        except Exception:
            raise
        return None

    def refresh_text_controls(self):
        sel = getattr(self.s.selection, "_selected", None)
        if not sel or sel not in self.s._items:
            try:
                self.s.text_size.set("")
                self.s.text_color.set("")
                self.s.text_bar.pack_forget()
                self.s.row_text.pack_forget()
            except Exception:
                logger.exception("Failed to clear/hide text controls on deselect")
            return
        meta = self.s._items.get(sel, {})
        t = meta.get("type")
        try:
            is_text_block = (t == "text") or (t == "rect")
        except Exception:
            is_text_block = False
        if not is_text_block:
            try:
                self.s.text_bar.pack_forget()
                self.s.row_text.pack_forget()
            except Exception:
                logger.exception("Failed to hide text controls for non-text selection")
            return
        else:
            try:
                # Show font controls in the left sidebar under the object controls
                before_widget = getattr(self.s, "backside_wrap", None) or getattr(self.s, "tools_panel", None)
                if self.s.row_text.winfo_ismapped():
                    self.s.row_text.pack_forget()
                if before_widget is not None:
                    self.s.row_text.pack(side="top", fill="x", padx=0, pady=(0, 6), anchor="w", before=before_widget)
                else:
                    self.s.row_text.pack(side="top", fill="x", padx=0, pady=(0, 6), anchor="w")
                if not self.s.text_bar.winfo_ismapped():
                    self.s.text_bar.pack(side="left", padx=0)
            except Exception:
                logger.exception("Failed to show text controls for text selection")
        tid = meta.get("label_id") if t == "rect" else (meta.get("label_id") or sel)
        try:
            if t == "rect":
                sz = int(round(float(meta.get("label_font_size", 10))))
                fam = str(meta.get("label_font_family", "Myriad Pro"))
                col = str(meta.get("label_fill", "#17a24b"))
            elif t == "text":
                sz = int(round(float(meta.get("font_size_pt", 12))))
                fam = str(meta.get("font_family", "Myriad Pro"))
                col = str(meta.get("default_fill", self.s.canvas.itemcget(tid, "fill") or "#17a24b"))
            else:
                sz = 12; fam = "Myriad Pro"; col = "#17a24b"
            self.s.text_size.set(str(int(sz)))
            try:
                is_available = (fam in self._font_families) and (self.find_font_path(fam) is not None)
            except Exception:
                is_available = (fam in self._font_families)
            if not is_available:
                fallback = "Myriad Pro" if "Myriad Pro" in self._font_families else (self._font_families[0] if self._font_families else "Myriad Pro")
                fam = fallback
                try:
                    if t == "rect":
                        meta["label_font_family"] = fam
                    elif t == "text":
                        meta["font_family"] = fam
                except Exception:
                    pass
            self.s.text_family.set(fam)
            if col:
                self.s.text_color.set(col)
        except Exception:
            logger.exception("Failed to refresh text control values")
        finally:
            self.s._suppress_text_traces = False

    # ---- Internals ----
    def _load_fonts_map(self) -> dict:
        try:
            if self._fonts_map_path.exists():
                with open(self._fonts_map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            logger.exception("Failed to load fonts mapping")
        return {"Myriad Pro": "MyriadPro-Regular"}

    def _save_fonts_map(self, mp: dict) -> None:
        try:
            with open(self._fonts_map_path, "w", encoding="utf-8") as f:
                json.dump(mp, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Failed to save fonts map")

    def _list_font_families(self, mp: dict) -> list[str]:
        try:
            return sorted(list(mp.keys()))
        except Exception:
            return ["Myriad Pro"]

    def _valid_hex(self, s: str) -> bool:
        s = (s or "").strip()
        if len(s) != 7 or not s.startswith("#"):
            return False
        try:
            int(s[1:], 16)
            return True
        except Exception:
            logger.exception("Invalid color hex string")
            return False

    def _apply_text_changes(self, *_):
        if getattr(self.s, "_suppress_text_traces", False):
            return
        sel = getattr(self.s.selection, "_selected", None)
        if not sel or sel not in self.s._items:
            return
        meta = self.s._items.get(sel, {})
        t = meta.get("type")
        tid = meta.get("label_id") if t == "rect" else (meta.get("label_id") or sel)
        try:
            if tid:
                self.s.canvas.itemconfig(tid, state="normal")
        except Exception:
            logger.exception("Failed to ensure text item visible")
        # Color
        try:
            col = self.s.text_color.get().strip()
            if not col.startswith("#"):
                col = f"#{col}"
            if self._valid_hex(col) and tid:
                if t == "rect":
                    meta["label_fill"] = col
                    try:
                        self.s._update_rect_label_image(sel)
                    except Exception:
                        raise
                elif t == "text":
                    self.s.canvas.itemconfig(tid, fill=col)
                    meta["default_fill"] = col
        except Exception:
            logger.exception("Failed to set text color on canvas")
        # Size
        try:
            raw_sz = (self.s.text_size.get() or "").strip()
            if raw_sz != "":
                sz = int(float(raw_sz))
                sz = max(2, sz)
                if t == "rect":
                    meta["label_font_size"] = int(sz)
                    try:
                        self.s._update_rect_label_image(sel)
                    except Exception:
                        raise
                elif t == "text":
                    meta["font_size_pt"] = int(sz)
        except Exception:
            logger.exception("Failed to set text size metadata")
        # Family
        try:
            fam = (self.s.text_family.get() or "Myriad Pro").strip()
            if t == "rect":
                meta["label_font_family"] = fam
                try:
                    self.s._update_rect_label_image(sel)
                except Exception:
                    raise
            elif t == "text":
                meta["font_family"] = fam
        except Exception:
            logger.exception("Failed to set text family metadata")
        # Apply font metrics update and keep labels layered
        try:
            self.s._update_all_text_fonts()
        except Exception:
            logger.exception("Failed to update fonts after text changes")
        try:
            self.s._raise_all_labels()
        except Exception:
            logger.exception("Failed to raise labels after text changes")

    def _on_import_font(self):
        path = filedialog.askopenfilename(title="Import Font", filetypes=[("Font Files", "*.ttf *.otf")])
        if not path:
            return
        try:
            import shutil
            dst = FONTS_PATH / os.path.basename(path)
            shutil.copy(path, dst)
        except Exception as e:
            messagebox.showerror("Import failed", f"Could not import font:\n{e}")
            return
        try:
            base_family = os.path.splitext(os.path.basename(path))[0]
        except Exception:
            base_family = "ImportedFont"
        # Mini-window to enter display name (as before), but using safe background
        try:
            win = tk.Toplevel(self.s)
            win.title("Font name")
            win.configure(bg=COLOR_BG_SCREEN)
            win.transient(self.s)
            win.grab_set()
            frm = tk.Frame(win, bg=COLOR_BG_SCREEN); frm.pack(padx=12, pady=0)
            tk.Label(frm, text="Enter display name for this font:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=("Myriad Pro", 12)).pack(anchor="w", pady=(8, 0))
            tk.Label(frm, text="(as on Amazon)", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=("Myriad Pro", 8)).pack(anchor="center", pady=(0, 15))
            entry, _entry_canvas = create_entry(
                EntryInfo(
                    parent=frm,
                    width=200,
                    text_info=TextInfo(text=base_family, color=COLOR_TEXT, font_size=12),
                    fill=COLOR_PILL,
                    background_color=COLOR_BG_SCREEN,
                    radius=10,
                    padding_x=12,
                    padding_y=6,
                )
            )
            btn_row = tk.Frame(frm, bg=COLOR_BG_SCREEN); btn_row.pack(fill="x", pady=(15, 12))
            def _confirm():
                display = (entry.get() or base_family).strip() or base_family
                try:
                    self._fonts_map[display] = base_family
                    self._save_fonts_map(self._fonts_map)
                    self._font_families = self._list_font_families(self._fonts_map)
                    self.s._family_combo.configure(values=self._font_families)
                    # self.s.text_family.set(display)
                except Exception:
                    logger.exception("Failed to update fonts mapping after import")
                finally:
                    try:
                        win.grab_release()
                    except Exception:
                        raise
                    win.destroy()
            def _cancel():
                try:
                    win.grab_release()
                except Exception:
                    raise
                win.destroy()
            ok_btn = create_button(
                ButtonInfo(
                    parent=btn_row,
                    text_info=TextInfo(text="OK", color=COLOR_TEXT, font_size=12),
                    background_color=COLOR_BG_SCREEN,
                    button_color="#737373",
                    hover_color=COLOR_BG_DARK,
                    active_color="#737373",
                    padding_x=12,
                    padding_y=6,
                    radius=10,
                    command=_confirm,
                )
            )
            cancel_btn = create_button(
                ButtonInfo(
                    parent=btn_row,
                    text_info=TextInfo(text="Cancel", color=COLOR_TEXT, font_size=12),
                    background_color=COLOR_BG_SCREEN,
                    button_color="#737373",
                    hover_color=COLOR_BG_DARK,
                    active_color="#737373",
                    padding_x=12,
                    padding_y=6,
                    radius=10,
                    command=_cancel,
                )
            )
            ok_btn.pack(side="left", padx=(48, 8))
            cancel_btn.pack(side="left")
            try:
                entry.focus_set()
            except Exception:
                raise
            try:
                self.s.update_idletasks(); win.update_idletasks()
                px = self.s.winfo_rootx() + (self.s.winfo_width() - win.winfo_width()) // 2
                py = self.s.winfo_rooty() + (self.s.winfo_height() - win.winfo_height()) // 2
                win.geometry(f"+{max(0, px)}+{max(0, py)}")
            except Exception:
                raise
            self.s.wait_window(win)
        except Exception:
            logger.exception("Failed to open font name mini-window")

    def _on_remove_font(self):
        mp = self._fonts_map
        fam = (self.s.text_family.get() or "").strip()
        if not fam:
            try:
                messagebox.showinfo("Fonts", "Please select a font to remove")
            except Exception:
                pass
            return
        if fam == "Myriad Pro":
            try:
                messagebox.showinfo("Fonts", "Default font 'Myriad Pro' cannot be removed")
            except Exception:
                pass
            return
        try:
            ok = messagebox.askyesno("Confirm", "Are you sure?")
        except Exception:
            ok = True
        if not ok:
            return
        try:
            file_stem = str(mp.get(fam, ""))
            if file_stem:
                for ext in (".ttf", ".otf"):
                    fp = FONTS_PATH / f"{file_stem}{ext}"
                    try:
                        if fp.exists():
                            fp.unlink()
                    except Exception:
                        pass
            if fam in mp:
                del mp[fam]
            self._save_fonts_map(mp)
            try:
                self._font_families = self._list_font_families(mp)
            except Exception:
                self._font_families = []
            try:
                self.s._family_combo.configure(values=self._font_families)
            except Exception:
                pass
            try:
                if self.s.text_family.get() == fam:
                    fallback = "Myriad Pro" if "Myriad Pro" in self._font_families else (self._font_families[0] if self._font_families else "Myriad Pro")
                    self.s.text_family.set(fallback)
            except Exception:
                pass
            try:
                messagebox.showinfo("Removed", f"Font '{fam}' has been removed")
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Failed to remove font: {e}")
            except Exception:
                pass


