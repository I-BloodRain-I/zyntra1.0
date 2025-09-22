# App (Tk), стили ttk, базовый Screen
import tkinter as tk
from tkinter import ttk, messagebox
from state import MM_TO_PX, APP_TITLE

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
    style.configure("Screen.TFrame", background="#4d4d4d")
    style.configure("Title.TFrame",  background="#3b3b3b")
    style.configure("Card.TFrame",   background="#a6a6a6")
    style.configure("Brand.TLabel",  background="#3b3b3b", foreground="black", font=("Arial", 18, "bold"))
    style.configure("H1.TLabel",     background="#4d4d4d", foreground="black", font=("Arial", 22, "bold"))
    style.configure("H2.TLabel",     background="#a6a6a6", foreground="black", font=("Arial", 16))
    style.configure("H3.TLabel",     background="#a6a6a6", foreground="black", font=("Arial", 12, "bold"))
    style.configure("Label.TLabel",  background="#a6a6a6", foreground="black", font=("Arial", 12))
    style.configure("Muted.TLabel",  background="#a6a6a6", foreground="#333")
    style.configure("Choice.TRadiobutton", background="#a6a6a6")


class App(tk.Tk):
    def __init__(self, title: str = APP_TITLE, size: str = "980x640"):
        super().__init__()
        self.title(title)
        self.geometry(size)
        self.configure(bg="#4d4d4d")
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

    def header(self, parent, title_text="Add a new product"):
        bar = ttk.Frame(parent, style="Title.TFrame")
        bar.pack(fill="x")
        ttk.Label(bar, text=APP_TITLE, style="Brand.TLabel").pack(side="left", padx=10, pady=6)
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