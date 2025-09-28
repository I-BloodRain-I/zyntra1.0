import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.core import Screen, vcmd_int, vcmd_float, warn, COLOR_BG_DARK, COLOR_TEXT
from src.core.state import state


class FontInfoScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.header(self, "Upload all fonts")

        self.rows = ttk.Frame(self, style="Screen.TFrame")
        self.rows.pack(pady=8)

        self.name_vars: list[tk.StringVar] = []
        self.upload_labels: list[ttk.Label] = []

        self._build_rows()
        self.bottom_nav(self, on_back=self.app.go_back, on_next=self.next)

    def _upload(self, idx):
        state.font_uploaded[idx] = True
        self.upload_labels[idx].configure(text="✔ Uploaded")
        state.font_names[idx] = self.name_vars[idx].get().strip()

    def _build_rows(self):
        for w in self.rows.winfo_children():
            w.destroy()
        self.name_vars.clear()
        self.upload_labels.clear()

        total = state.font_variations_total
        for i in range(total):
            card = ttk.Frame(self.rows, style="Card.TFrame", padding=10)
            card.pack(fill="x", padx=10, pady=6)
            ttk.Label(card, text=f"Font {i+1}", width=10).grid(row=0, column=0, sticky="w", padx=(4, 8))
            ttk.Label(card, text="Name (Same as Amazon)").grid(row=0, column=1, sticky="w")
            var = tk.StringVar(value=state.font_names[i] if i < len(state.font_names) else "")
            ttk.Entry(card, textvariable=var, width=28).grid(row=0, column=2, padx=8)
            self.name_vars.append(var)

            ttk.Button(card, text="Upload", command=lambda k=i: self._upload(k)).grid(row=0, column=3, padx=8)
            status = ttk.Label(card, text="• Pending", style="Muted.TLabel")
            status.grid(row=0, column=4, padx=8)
            self.upload_labels.append(status)

            if i < len(state.font_uploaded) and state.font_uploaded[i]:
                status.configure(text="✔ Uploaded")

    def next(self):
        if not all(state.font_uploaded):
            missing = [str(i + 1) for i, ok in enumerate(state.font_uploaded) if not ok]
            messagebox.showwarning("Upload required", f"Please upload all fonts: {', '.join(missing)}")
            return
        self.app.show_screen(Screen4)