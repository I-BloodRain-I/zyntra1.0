from typing import Tuple, Optional, Union

import tkinter as tk
import tkinter.font as tkfont

from src.core import EntryInfo, ButtonInfo, PillLabelInfo, TextInfo


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
    """
    Draw a rounded rectangle on a canvas by combining two rectangles with four quarter-circle arcs.

    The corner radius is clamped so it cannot exceed half of the rectangle’s width or height.

    Args:
        canvas: The drawing surface on which to create items.
        x0: Left coordinate of the rectangle.
        y0: Top coordinate of the rectangle.
        x1: Right coordinate of the rectangle.
        y1: Bottom coordinate of the rectangle.
        r: Corner radius for rounded corners; values larger than half the edge lengths are reduced.
        fill: Fill color for all created items.
        outline: Outline color for all created items. Defaults to an empty string (no outline).
        width: Outline width for all created items. Defaults to 1.
        tag: A canvas tag assigned to all created items (in addition to any internal tags).

    Returns:
        A tuple of item identifiers, in drawing order: the two central/side rectangles
        followed by the four corner arcs (top-left, top-right, bottom-left, bottom-right).
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
    Create a rounded input field consisting of a canvas background and an embedded text entry.

    Behavior:
      • The canvas size is computed from the requested width/height in `info`, the measured text,
        and `padding_x`/`padding_y`. The larger of the computed size and the requested size is used.
      • If `border` is positive, a border layer is drawn beneath the field using `border_color`
        and the inner field radius is reduced by the border width.
      • An entry widget is embedded at the center of the canvas using a canvas window.
      • The entry’s font size, foreground color, initial text, and justification are derived from `info.text_info`.
      • The canvas is packed into `info.parent`; the embedded entry becomes a child of that canvas.

    Args:
        info: Configuration describing parent container, geometry (width, height, radius, padding),
              colors (`background_color`, `fill`, optional `border_color`), border thickness, and text styling.

    Returns:
        A tuple `(entry, canvas)` where `entry` is the created text entry widget and `canvas`
        is the background canvas that contains it.
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
    """
    Produce a lighter or darker shade of a hexadecimal color.

    Each RGB channel is adjusted by `delta` and clamped to the range [0, 255].

    Args:
        hex_color: A color string in the form "#rrggbb".
        delta: The signed amount to add to each RGB channel.

    Returns:
        A color string in the form "#rrggbb" representing the adjusted shade.
    """
    s = hex_color.lstrip("#")
    r = max(0, min(255, int(s[0:2], 16) + delta))
    g = max(0, min(255, int(s[2:4], 16) + delta))
    b = max(0, min(255, int(s[4:6], 16) + delta))
    return f"#{r:02x}{g:02x}{b:02x}"


def create_button(info: ButtonInfo) -> tk.Canvas:
    """
    Create a rounded, text-labeled button on a canvas with hover and active visual states.

    Behavior:
      • The canvas size is computed from the requested width/height in `info`, measured label text,
        and `padding_x`/`padding_y`. The larger of the computed size and the requested size is used.
      • The button face is drawn as a rounded rectangle; text is left-anchored with a small left inset.
      • Hover and active background colors are taken from `info.hover_color` and `info.active_color`.
        If not provided, fallback shades are derived from `info.button_color`.
      • Pointer events (<Enter>, <Leave>, <ButtonPress-1>, <ButtonRelease-1>) update the background
        and invoke `info.command` on click if provided.
      • The canvas is packed into `info.parent`.

    Args:
        info: Configuration describing parent container, geometry (width, height, radius, padding),
              label styling via `text_info`, base color (`button_color`), optional hover/active colors,
              an optional command callback, and an optional tag.

    Returns:
        The canvas that contains the button background and label.
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
    Create a rounded “pill” label on a canvas with text content.

    Behavior:
      • The canvas size is computed from the requested width/height in `info`, measured text,
        and `padding_x`/`padding_y`. The larger of the computed size and the requested size is used.
      • A rounded rectangle is drawn as the label’s background using `info.fill`.
      • Text is drawn left-anchored at `padding_x`. Vertical placement is:
          – top if `text_info.justify == "top"`,
          – bottom if `text_info.justify == "bottom"`,
          – vertically centered otherwise.
      • The canvas is packed into `info.parent`.

    Args:
        info: Configuration describing parent container, geometry (width, height, radius, padding),
              background (`background_color`), fill color (`fill`), optional tag, and text styling.

    Returns:
        The canvas that contains the pill label background and text.
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
    Attach a secondary component (entry, button, or pill label) to the right side of a pill label.

    Behavior:
      • If `pill_canvas` is not provided, a pill label canvas is created (and packed) using `pill_label`.
      • The target component’s parent is set to the pill canvas; its background is aligned to the pill fill.
      • The component is created:
          – entries via `create_entry` (returns `(entry, canvas)`),
          – buttons via `create_button` (returns `canvas`),
          – pill labels via `create_pill_label` (returns `canvas`).
      • The created component’s canvas is placed inside the pill canvas using a canvas window near the right edge.
      • Geometry is computed from `object_info.width`/`height`, `object_info.padding_x`/`padding_y`,
        and the optional `object_padding_x`/`object_padding_y`.

    Args:
        pill_label: Configuration for the host pill label.
        object_info: Configuration for the component to append (entry, button, or pill label).
        pill_canvas: An existing pill canvas to use. If omitted, a new one is created.
        object_padding_x: Additional horizontal offset applied during placement.
        object_padding_y: Additional vertical offset applied during placement.

    Returns:
        A tuple `(pill_canvas_out, object_canvas, entry_or_none)` where:
          • `pill_canvas_out` is the pill label canvas,
          • `object_canvas` is the canvas of the appended component,
          • `entry_or_none` is the entry widget if an entry was appended, otherwise `None`.
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