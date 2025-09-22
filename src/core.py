# App (Tk), стили ttk, базовый Screen
import tkinter as tk
from tkinter import ttk


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
    def __init__(self, title: str = "Zyntra 1.0", size: str = "980x640"):
        super().__init__()
        self.title(title)
        self.geometry(size)
        self.configure(bg="#4d4d4d")
        apply_styles(self)
        self.current = None

    def show_screen(self, screen_cls):
        if self.current is not None:
            self.current.destroy()
        self.current = screen_cls(self, self)
        self.current.pack(expand=True, fill="both")

    def quit_app(self):
        self.destroy()


class Screen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.configure(style="Screen.TFrame")

    def header(self, parent, title_text="Add a new product"):
        bar = ttk.Frame(parent, style="Title.TFrame")
        bar.pack(fill="x")
        ttk.Label(bar, text="Zyntra 1.0", style="Brand.TLabel").pack(side="left", padx=10, pady=6)
        ttk.Label(parent, text=title_text, style="H1.TLabel").pack(pady=(18, 8))

    def bottom_nav(self, parent, on_back=None, on_next=None, next_text="Proceed"):
        row = ttk.Frame(parent, style="Screen.TFrame")
        row.pack(fill="x", side="bottom", pady=12)
        ttk.Button(row, text="Go Back", command=on_back).pack(side="left", padx=12)
        ttk.Button(row, text=next_text, command=on_next).pack(side="right", padx=12)