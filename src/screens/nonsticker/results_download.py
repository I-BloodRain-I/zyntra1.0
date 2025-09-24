import os
import re
import struct
from pathlib import Path
from typing import Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.core import Screen, vcmd_float, COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL
from src.state import state, MM_TO_PX, IMAGES_PATH

# ---- tiny helper: write a minimal PDF so Download has content ----
def _write_minimal_pdf(path: str):
    pdf = b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 24 Tf 72 720 Td (Zyntra Test File) Tj ET
endstream
endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000015 00000 n 
0000000062 00000 n 
0000000119 00000 n 
0000000263 00000 n 
0000000404 00000 n 
trailer<</Root 1 0 R /Size 6>>
startxref
517
%%EOF
"""
    with open(path, "wb") as f:
        f.write(pdf)


class NStickerResultsDownloadScreen(Screen):
    """Non-sticker success + download."""
    def __init__(self, master, app):
        super().__init__(master, app)

        # App title + screen title
        self.header(self, "Product Added Successfully")

        wrap = ttk.Frame(self, style="Screen.TFrame")
        wrap.pack(expand=True, fill="both", padx=20, pady=20)

        # keep main success header within wrap for spacing consistency
        ttk.Label(wrap, text="Product Added Successfully", style="H1.TLabel").pack(pady=(10, 16))

        chk = tk.Canvas(wrap, width=180, height=180, bg="#4d4d4d", highlightthickness=0)
        chk.pack(pady=(0, 12))
        r = 80
        cx, cy = 90, 90
        chk.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#17a24b", width=10)
        chk.create_line(55, 95, 85, 120, fill="#17a24b", width=12, capstyle="round")
        chk.create_line(85, 120, 140, 60, fill="#17a24b", width=12, capstyle="round")

        product_name = state.saved_product if state.saved_product else "Product"
        ttk.Label(wrap, text=f"Sku {product_name}", style="H1.TLabel").pack(pady=(6, 0))
        ttk.Label(wrap, text=(state.sku or "—"), style="H1.TLabel").pack(pady=(0, 16))

        row = ttk.Frame(wrap, style="Screen.TFrame")
        row.pack(pady=(8, 0))
        chip = ttk.Frame(row, style="Card.TFrame", padding=10)
        chip.pack(side="left")
        ttk.Label(chip, text="Test File .pdf", style="H2.TLabel").pack()
        ttk.Button(row, text="Download", command=self._download).pack(side="left", padx=14)

        self.bottom_nav(self, on_back=self.app.go_back, on_next=self.app.quit_app, next_text="Done")

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