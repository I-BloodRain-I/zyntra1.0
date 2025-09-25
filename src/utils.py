from typing import Tuple, Optional, Callable, Union

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass


@dataclass
class TextInfo:
    text: str
    color: str
    font_size: int
    font_family: str = "Myriad Pro"
    font_weight: str = "normal"
    justify: str = "center"


@dataclass
class BaseWidgetInfo:
    parent: tk.Widget
    width: int = 0
    height: int = 0
    radius: int = 0
    background_color: Optional[str] = None
    foreground_color: Optional[str] = None
    text_info: Optional[TextInfo] = None
    border: int = 0
    border_color: Optional[str] = None
    padding_x: int = 0
    padding_y: int = 0
    tag: str = ""
    

@dataclass
class ButtonInfo(BaseWidgetInfo):
    button_color: str = "#808080"
    hover_color: str = "#3f3f3f"
    active_color: str = "#dcdcdc"
    command: Optional[Callable[[], None]] = None


@dataclass
class EntryInfo(BaseWidgetInfo):
    fill: str = "white"
    

@dataclass
class PillLabelInfo(BaseWidgetInfo):
    fill: str = "#e5e5e5"


def _rounded_rect(
    canvas: tk.Canvas,
    x0: int, y0: int,
    x1: int, y1: int,
    r: int,
    fill: str,
    outline: str = "",
    width: int = 1,
    tag: str = ""
) -> Tuple[int, ...]:
    """Draws a rounded rectangle using arcs and rectangles.

    Args:
        canvas: The Tkinter canvas on which to draw.
        x0: Left coordinate of the rectangle.
        y0: Top coordinate of the rectangle.
        x1: Right coordinate of the rectangle.
        y1: Bottom coordinate of the rectangle.
        r: Corner radius for rounded edges.
        fill: Fill color of the rectangle.
        outline: Outline color of the rectangle. Defaults to "".
        width: Outline width. Defaults to 1.
        tag: Canvas tag to assign to all items.

    Returns:
        Tuple of created item ids.
    """
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    ids = []

    # central/side rectangles
    ids.append(canvas.create_rectangle(x0+r, y0,   x1-r, y1, fill=fill, outline=outline, width=width, tags=(tag,)))
    ids.append(canvas.create_rectangle(x0,   y0+r, x1,   y1-r, fill=fill, outline=outline, width=width, tags=(tag,)))

    # 4 angles
    ids.append(canvas.create_arc(x0,     y0,     x0+2*r, y0+2*r, start=90,  extent=90, style="pieslice",
                      fill=fill, outline=outline, width=width, tags=(tag,)))
    ids.append(canvas.create_arc(x1-2*r, y0,     x1,     y0+2*r, start=0,   extent=90, style="pieslice",
                      fill=fill, outline=outline, width=width, tags=(tag,)))
    ids.append(canvas.create_arc(x0,     y1-2*r, x0+2*r, y1,     start=180, extent=90, style="pieslice",
                      fill=fill, outline=outline, width=width, tags=(tag,)))
    ids.append(canvas.create_arc(x1-2*r, y1-2*r, x1,     y1,     start=270, extent=90, style="pieslice",
                      fill=fill, outline=outline, width=width, tags=(tag,)))

    return tuple(ids)


def create_entry(info: EntryInfo) -> Tuple[tk.Entry, tk.Canvas]:
    """
    Draws a rounded input field.

    The entry automatically sizes itself based on the text width and padding.
    It supports rounded corners, custom background colors, and an optional
    border.

    Returns:
        A tuple containing the Entry widget and the Canvas used
        to draw the rounded background.
    """
    if info.text_info is None:
        info.text_info = TextInfo(text="", color="", font_size=0)
    font_obj = tkfont.Font(size=int(round(info.text_info.font_size)))
    w = max(info.width, int(font_obj.measure(info.text_info.text) + info.padding_x*2))
    h = max(info.height, int(font_obj.metrics("linespace") + info.padding_y*2))

    canvas = tk.Canvas(info.parent, width=w, height=h, highlightthickness=0, bd=0, bg=info.background_color)
    canvas.pack()

    if info.border > 0:
        _rounded_rect(canvas, 0, 0, w, h, info.radius, fill=info.border_color, outline="")

    inset = info.border
    _rounded_rect(canvas, inset, inset, w-inset, h-inset, max(0, info.radius-info.border),
                  fill=info.fill, outline="")

    entry = tk.Entry(canvas, font=("Arial", info.text_info.font_size), bd=0, relief="flat",
                     bg=info.fill, fg=info.text_info.color, highlightthickness=0, justify=info.text_info.justify)
    entry.insert(0, info.text_info.text)

    usable_w = w - 2*(info.padding_x + info.border)
    usable_h = h - 2*(info.padding_y + info.border)
    canvas.create_window(w//2, h//2, window=entry,
                         width=max(10, usable_w), height=max(10, usable_h))

    return entry, canvas


def _shade(hex_color: str, delta: int) -> str:
    """Return a shade of hex_color by adding delta to each RGB channel."""
    s = hex_color.lstrip("#")
    r = max(0, min(255, int(s[0:2], 16) + delta))
    g = max(0, min(255, int(s[2:4], 16) + delta))
    b = max(0, min(255, int(s[4:6], 16) + delta))
    return f"#{r:02x}{g:02x}{b:02x}"


def create_button(info: ButtonInfo) -> tk.Canvas:
    """
    Create a rounded button on a Canvas sized from its label.

    The button automatically sizes itself based on the text width and padding.
    It supports rounded corners, custom background colors, and an optional
    hover and active states.

    Returns:
        The Canvas containing the button.
    """
    if info.text_info is None:
        info.text_info = TextInfo(text="", color="", font_size=0)
    font_obj = tkfont.Font(size=int(round(info.text_info.font_size)))
    w = max(info.width, int(font_obj.measure(info.text_info.text) + info.padding_x))
    h = max(info.height, int(font_obj.metrics("linespace") + info.padding_y))

    canvas = tk.Canvas(info.parent, width=w, height=h, highlightthickness=0, bd=0, cursor="hand2")
    canvas.pack()

    hover = info.hover_color if info.hover_color else _shade(info.button_color, +12)
    active = info.active_color if info.active_color else _shade(info.button_color, -18)

    _rounded_rect(canvas, 0, 0, w, h, info.radius, fill=info.button_color, outline="", tag=info.tag)

    px_left = 8
    py_center = h // 2
    text_id = canvas.create_text(px_left, py_center, text=info.text_info.text, font=font_obj, fill=info.text_info.color, anchor="w", tags=("btntxt",))

    state = {"pressed": False, "inside": False}

    def set_bg(color: str) -> None:
        canvas.delete("btnbg")
        _rounded_rect(canvas, 0, 0, w, h, info.radius, fill=color, outline="", tag="btnbg")
        canvas.tag_raise("btntxt")

    def inside(ev: tk.Event) -> bool:
        return 0 <= ev.x <= w and 0 <= ev.y <= h

    def on_enter(_):
        state["inside"] = True
        if not state["pressed"]:
            set_bg(hover)

    def on_leave(_):
        state["inside"] = False
        if not state["pressed"]:
            set_bg(info.button_color)

    def on_press(_):
        state["pressed"] = True
        set_bg(active)
        canvas.move(text_id, 1, 1)

    def on_release(ev):
        was_pressed = state["pressed"]
        state["pressed"] = False
        canvas.move(text_id, -1, -1)
        set_bg(hover if inside(ev) else info.button_color)
        if was_pressed and inside(ev) and info.command:
            canvas.after(10, info.command)

    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<ButtonRelease-1>", on_release)

    return canvas


def create_pill_label(info: PillLabelInfo) -> tk.Canvas:
    """
    Create a rounded "pill-style" label inside a Canvas.

    The label automatically sizes itself based on the text width and padding.
    It supports rounded corners, custom background colors, and an optional
    drop shadow effect for a speech-bubble look.

    Returns:
        A Tkinter Canvas object containing the rounded pill label.
    """
    if info.text_info is None:
        info.text_info = TextInfo(text="", color="", font_size=0)
    font_obj = tkfont.Font(size=info.text_info.font_size)
    w = max(info.width, int(font_obj.measure(info.text_info.text) + info.padding_x * 2))
    h = max(info.height, int(font_obj.metrics("linespace") + info.padding_y * 2))

    canvas = tk.Canvas(info.parent, width=w, height=h, bg=info.background_color, highlightthickness=0, bd=0)
    canvas.pack()

    _rounded_rect(canvas, 0, 0, w, h, info.radius, fill=info.fill, outline="", tag=info.tag)
    y = h // 2
    if info.text_info.justify == "top":
        y = info.padding_y
    elif info.text_info.justify == "bottom":
        y = h - info.padding_y - font_obj.metrics("linespace")
    canvas.create_text(info.padding_x, y, text=info.text_info.text, fill=info.text_info.color, font=font_obj, anchor="w", tags=(info.tag,))

    return canvas


def append_object_to_pill_label(
    pill_label: PillLabelInfo, 
    object_info: Union[EntryInfo, ButtonInfo, PillLabelInfo],
    pill_canvas: Optional[tk.Canvas] = None,
    object_padding_x: int = 0,
    object_padding_y: int = 0
) -> Tuple[tk.Canvas, tk.Canvas, Optional[tk.Entry]]:
    """
    Append an object to a pill label.

    Returns:
        A tuple containing the pill label canvas, the object canvas, and the object.
        If the object is an entry, the object is returned.
    """
    canvas = pill_canvas if pill_canvas else create_pill_label(pill_label)
    pill_label.parent.update()
    object_info.parent = canvas
    object_info.background_color = pill_label.fill

    obj = None
    if isinstance(object_info, EntryInfo):
        obj, obj_canvas = create_entry(object_info)
    elif isinstance(object_info, ButtonInfo):
        obj_canvas = create_button(object_info)
    elif isinstance(object_info, PillLabelInfo):
        obj_canvas = create_pill_label(object_info)
    obj_canvas.pack_forget()

    cx1 = canvas.winfo_width() - object_info.padding_x + object_padding_x
    cx0 = cx1 - object_info.width
    cy0 = (canvas.winfo_height() - object_info.height) // 2 + object_padding_y
    cy1 = cy0 + object_info.height
    canvas.create_window((cx0 + cx1)//2, (cy0 + cy1)//2,
                         window=obj_canvas, width=object_info.width, height=object_info.height)

    return canvas, obj_canvas, obj