import tkinter as tk
from tkinter import ttk
from state import state, ALL_PRODUCTS, APP_TITLE
from core import App
from screens_sticker import Screen1 


def start_first_screen():
    def filter_products(*_):
        q_raw = search_var.get().strip()
        state.saved_search = q_raw
        q = q_raw.lower()
        values = ALL_PRODUCTS if not q else [p for p in ALL_PRODUCTS if q in p.lower()]
        product_dropdown["values"] = values
        if product_var.get() not in values:
            product_var.set(values[0] if values else "")

    def proceed():
        state.saved_product = product_var.get()
        root.destroy()
        open_second_screen()

    def add_new():
        root.destroy()
        app = App(title=APP_TITLE)
        app.show_screen(Screen1)
        app.mainloop()

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("800x520")
    root.configure(bg="gray30")

    title = tk.Frame(root, bg="gray20", height=44); title.pack(fill="x")
    tk.Label(title, text=APP_TITLE, bg="gray20", fg="black",
             font=("Arial", 18, "bold")).pack(side="left", padx=10, pady=6)

    mid = tk.Frame(root, bg="gray30"); mid.pack(expand=True, fill="both")
    tk.Label(mid, text="Select product:", bg="gray30", fg="black",
             font=("Arial", 16)).pack(pady=(24, 8))

    search_row = tk.Frame(mid, bg="gray30"); search_row.pack(pady=(0, 6))
    tk.Label(search_row, text="Search:", bg="gray30", fg="black",
             font=("Arial", 12)).pack(side="left", padx=(0, 8))

    search_var = tk.StringVar(value=state.saved_search)
    search_entry = tk.Entry(search_row, textvariable=search_var, font=("Arial", 12), width=30)
    search_entry.pack(side="left")
    tk.Button(search_row, text="Clear", bg="gray25", fg="black",
              command=lambda: (search_var.set(""), filter_products())).pack(side="left", padx=6)

    product_var = tk.StringVar(value=state.saved_product)
    product_dropdown = ttk.Combobox(mid, textvariable=product_var, values=ALL_PRODUCTS, state="readonly", width=32)
    product_dropdown.pack(pady=(0, 18))

    bottom_left = tk.Frame(root, bg="gray30"); bottom_left.pack(side="left", anchor="sw", padx=12, pady=18)
    tk.Button(bottom_left, text="UPDATE EXISTING PRODUCT", bg="gray25", fg="black", width=28, height=2).pack(pady=6)
    tk.Button(bottom_left, text="Add a new product", bg="gray25", fg="black", width=28, height=2, command=add_new).pack(pady=6)

    tk.Button(root, text="Proceed", bg="gray25", fg="black", width=12, height=2, command=proceed).place(relx=0.93, rely=0.92, anchor="center")

    search_entry.bind("<KeyRelease>", filter_products)
    filter_products()
    root.mainloop()


def open_second_screen():
    def go_back():
        win.destroy()
        start_first_screen()

    def start_action():
        state.order_from = from_entry.get()
        state.order_to   = to_entry.get()
        win.destroy()
        app = App(title=APP_TITLE)
        app.show_screen(Screen1)  # дальше визард сам решит ветку
        app.mainloop()

    win = tk.Tk()
    win.title(APP_TITLE)
    win.geometry("800x520")
    win.configure(bg="gray30")

    title = tk.Frame(win, bg="gray20", height=44); title.pack(fill="x")
    tk.Label(title, text=APP_TITLE, bg="gray20", fg="black",
             font=("Arial", 18, "bold")).pack(side="left", padx=10, pady=6)

    tk.Label(win, text=state.saved_product, bg="gray25", fg="black",
             font=("Arial", 16), padx=18, pady=6).place(x=10, y=56)

    mid = tk.Frame(win, bg="gray30"); mid.pack(expand=True)
    tk.Label(mid, text="Write order numbers to produce files:", bg="gray25", fg="black",
             font=("Arial", 14), padx=16, pady=6).pack(pady=(32, 18))

    row = tk.Frame(mid, bg="gray30"); row.pack(pady=8)
    tk.Label(row, text="From:", bg="gray30", fg="black", font=("Arial", 22)).grid(row=0, column=0, padx=(0, 8))
    from_entry = tk.Entry(row, font=("Arial", 20), width=10, justify="center"); from_entry.insert(0, state.order_from); from_entry.grid(row=0, column=1, padx=(0, 28))
    tk.Label(row, text="To:", bg="gray30", fg="black", font=("Arial", 22)).grid(row=0, column=2, padx=(0, 8))
    to_entry = tk.Entry(row, font=("Arial", 20), width=10, justify="center"); to_entry.insert(0, state.order_to); to_entry.grid(row=0, column=3)

    tk.Button(win, text="Go Back", bg="gray25", fg="black", width=12, height=2, command=go_back).place(relx=0.08, rely=0.92, anchor="center")
    tk.Button(win, text="Start",   bg="gray25", fg="black", width=12, height=2, command=start_action).place(relx=0.93, rely=0.92, anchor="center")
    win.mainloop()


if __name__ == "__main__":
    start_first_screen()