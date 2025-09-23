# App (Tk), стили ttk, базовый Screen
import os

import tkinter as tk
from tkinter import ttk, messagebox

from src.state import MM_TO_PX, APP_TITLE

# Shared UI colors
COLOR_BG_SCREEN = "#878787"
COLOR_BG_DARK = "#474747"
COLOR_CARD = "#a6a6a6"
COLOR_TEXT = "#000000"
COLOR_PILL = "#e6e6e6"

# Helpers: dialogs
def info(message: str, title: str = "Info"):
    messagebox.showinfo(title, message)

def warn(message: str, title: str = "Warning"):
    messagebox.showwarning(title, message)

def error(message: str, title: str = "Error"):
    messagebox.showerror(title, message)

# Helpers: numeric validation and units
def vcmd_int(root):
    def _is_int(new_value: str) -> bool:
        return new_value.isdigit() or new_value == ""
    return root.register(_is_int)

def vcmd_float(root):
    def _is_float(new_value: str) -> bool:
        if new_value == "":
            return True
        try:
            float(new_value)
            return True
        except ValueError:
            return False
    return root.register(_is_float)

# Helpers: conversions
def to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default

def to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default

def mm_to_px(mm_value) -> int:
    try:
        return int(float(mm_value) * MM_TO_PX)
    except Exception:
        return 0


def apply_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    # Global backgrounds per latest spec
    style.configure("Screen.TFrame", background=COLOR_BG_SCREEN)
    style.configure("Title.TFrame",  background=COLOR_BG_DARK)
    style.configure("Card.TFrame",   background=COLOR_CARD)
    style.configure("Brand.TLabel",  background=COLOR_BG_DARK, foreground=COLOR_TEXT, font=("Myriad Pro", 24))
    style.configure("H1.TLabel",     background="#4d4d4d", foreground="black", font=("Myriad Pro", 22))
    style.configure("H2.TLabel",     background=COLOR_CARD, foreground="black", font=("Myriad Pro", 16))
    style.configure("H3.TLabel",     background=COLOR_CARD, foreground="black", font=("Myriad Pro", 12))
    style.configure("Label.TLabel",  background=COLOR_CARD, foreground="black", font=("Myriad Pro", 12))
    style.configure("Muted.TLabel",  background=COLOR_CARD, foreground="#333")
    style.configure("Choice.TRadiobutton", background="#a6a6a6")
    # Combobox style for launcher
    style.configure(
        "Prod.TCombobox",
        fieldbackground="#3d3d3d",
        background="#3d3d3d",
        foreground="#000000",
        arrowsize=0,
        arrowcolor="#000000",
        selectforeground="#000000",
        selectbackground="#3d3d3d"
    )
    style.configure("Prod.TCombobox", font=("Myriad Pro", 31))


class App(tk.Tk):
    def __init__(self, title: str = APP_TITLE, size: str = "960x720"):
        super().__init__()
        self.title(title)
        self.geometry(size)
        self.minsize(960, 720)
        self.maxsize(960, 720)  # static layout, fixed 4:3 ratio
        self.configure(bg=COLOR_BG_SCREEN)
        apply_styles(self)
        self.current = None
        self._history: list[type] = []

    def show_screen(self, screen_cls, push_history: bool = True):
        if self.current is not None:
            if push_history:
                try:
                    self._history.append(self.current.__class__)
                except Exception:
                    pass
            self.current.destroy()
        # clear global hotkeys between screens
        try:
            self.unbind("<Return>")
            self.unbind("<Escape>")
        except Exception:
            pass
        self.current = screen_cls(self, self)
        self.current.pack(expand=True, fill="both")

    def quit_app(self):
        self.destroy()

    def go_back(self):
        if self._history:
            prev = self._history.pop()
            self.show_screen(prev, push_history=False)
        else:
            self.quit_app()


class Screen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(style="Screen.TFrame")

    # UI scale (duplicated here for independence from zyntra module)
    UI_SCALE = float(os.environ.get("ZYNTRA_UI_SCALE", "1.0"))

    def scale_px(self, value: float) -> int:
        try:
            return int(round(value * self.UI_SCALE))
        except Exception:
            return int(round(value))

    def brand_bar(self, parent):
        bar = tk.Frame(parent, bg=COLOR_BG_DARK, height="31p")
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(
            bar,
            text=APP_TITLE,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT,
            font=("Myriad Pro", int(round(24 * self.UI_SCALE))),
        ).pack(side="left", padx=self.scale_px(8), pady=0)
        return bar

    def header(self, parent, title_text="Add a new product"):
        self.brand_bar(parent)
        ttk.Label(parent, text=title_text, style="H1.TLabel").pack(pady=(18, 8))

    def bottom_nav(self, parent, on_back=None, on_next=None, next_text="Proceed"):
        row = ttk.Frame(parent, style="Screen.TFrame")
        row.pack(fill="x", side="bottom", pady=12)
        if on_back is None:
            on_back = self.app.go_back
        ttk.Button(row, text="Go Back", command=on_back).pack(side="left", padx=12)
        ttk.Button(row, text=next_text, command=on_next).pack(side="right", padx=12)
        # Default hotkeys: Enter → next, Escape → back/quit
        if on_next:
            self.app.bind("<Return>", lambda _e: on_next())
        if on_back:
            self.app.bind("<Escape>", lambda _e: on_back())