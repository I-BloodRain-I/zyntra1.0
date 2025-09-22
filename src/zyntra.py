import logging
import tkinter as tk
from tkinter import ttk, messagebox
from state import state, ALL_PRODUCTS, APP_TITLE
from core import App, Screen
from screens_sticker import Screen1


class LauncherSelectProduct(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        # Fall back to previous UI layout/styles for main screen
        title = tk.Frame(self, bg="gray20", height=44); title.pack(fill="x")
        tk.Label(title, text=APP_TITLE, bg="gray20", fg="black",
                 font=("Arial", 18, "bold")).pack(side="left", padx=10, pady=6)

        mid = tk.Frame(self, bg="gray30"); mid.pack(expand=True, fill="both")
        tk.Label(mid, text="Select product:", bg="gray30", fg="black",
                 font=("Arial", 16)).pack(pady=(24, 8))

        search_row = tk.Frame(mid, bg="gray30"); search_row.pack(pady=(0, 6))
        tk.Label(search_row, text="Search:", bg="gray30", fg="black",
                 font=("Arial", 12)).pack(side="left", padx=(0, 8))

        self.search_var = tk.StringVar(value=state.saved_search)
        search_entry = tk.Entry(search_row, textvariable=self.search_var, font=("Arial", 12), width=30)
        search_entry.pack(side="left")
        tk.Button(search_row, text="Clear", bg="gray25", fg="black",
                  command=lambda: (self.search_var.set(""), self._filter_products())).pack(side="left", padx=6)

        self.product_var = tk.StringVar(value=state.saved_product)
        self.product_dropdown = ttk.Combobox(mid, textvariable=self.product_var, values=ALL_PRODUCTS, state="readonly", width=32)
        self.product_dropdown.pack(pady=(0, 18))

        bottom_left = tk.Frame(self, bg="gray30"); bottom_left.pack(side="left", anchor="sw", padx=12, pady=18)
        tk.Button(bottom_left, text="UPDATE EXISTING PRODUCT", bg="gray25", fg="black", width=28, height=2).pack(pady=6)
        tk.Button(bottom_left, text="Add a new product", bg="gray25", fg="black", width=28, height=2, command=self._add_new).pack(pady=6)

        tk.Button(self, text="Proceed", bg="gray25", fg="black", width=12, height=2, command=self._proceed).place(relx=0.93, rely=0.92, anchor="center")

        search_entry.bind("<KeyRelease>", lambda *_: self._filter_products())
        self._filter_products()
        search_entry.focus_set()

    def _filter_products(self):
        q_raw = self.search_var.get().strip()
        state.saved_search = q_raw
        q = q_raw.lower()
        values = ALL_PRODUCTS if not q else [p for p in ALL_PRODUCTS if q in p.lower()]
        self.product_dropdown["values"] = values
        if self.product_var.get() not in values:
            self.product_var.set(values[0] if values else "")

    def _proceed(self):
        state.saved_product = self.product_var.get()
        self.app.show_screen(LauncherOrderRange)

    def _add_new(self):
        logging.info("Starting new product flow (sticker/non-sticker chooser)")
        self.app.show_screen(Screen1)


class LauncherOrderRange(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        bar = ttk.Frame(self, style="Title.TFrame"); bar.pack(fill="x")
        ttk.Label(bar, text=APP_TITLE, style="Brand.TLabel").pack(side="left", padx=10, pady=6)

        ttk.Label(self, text=state.saved_product, style="H2.TLabel").pack(anchor="w", padx=10, pady=(8, 0))

        mid = ttk.Frame(self, style="Screen.TFrame"); mid.pack(expand=True)
        card = ttk.Frame(mid, style="Card.TFrame", padding=16); card.pack(pady=(32, 18))
        ttk.Label(card, text="Write order numbers to produce files:", style="H2.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        ttk.Label(card, text="From:", style="Label.TLabel").grid(row=1, column=0, padx=(0, 8))
        self.from_var = tk.StringVar(value=state.order_from)
        ttk.Entry(card, textvariable=self.from_var, width=12, justify="center").grid(row=1, column=1, padx=(0, 28))

        ttk.Label(card, text="To:", style="Label.TLabel").grid(row=1, column=2, padx=(0, 8))
        self.to_var = tk.StringVar(value=state.order_to)
        ttk.Entry(card, textvariable=self.to_var, width=12, justify="center").grid(row=1, column=3)

        self.bottom_nav(self, on_back=self.app.go_back, on_next=self._start, next_text="Start")

    def _start(self):
        from_s = self.from_var.get().strip()
        to_s = self.to_var.get().strip()

        # 1) Order number does not exist / invalid
        if not from_s or not to_s:
            messagebox.showerror("Error", "Order number does not exist.")
            return

        # Both must be integers
        try:
            from_n = int(from_s)
            to_n = int(to_s)
        except ValueError:
            messagebox.showerror("Error", "Order number does not exist.")
            return

        # Range sanity
        if from_n > to_n:
            messagebox.showwarning("Warning", "'From' must be less than or equal to 'To'.")
            return

        state.order_from = from_s
        state.order_to = to_s
        self.app.show_screen(Screen1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = App(title=APP_TITLE)
    app.show_screen(LauncherSelectProduct)
    app.mainloop()