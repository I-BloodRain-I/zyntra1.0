import tkinter as tk
import tkinter.font as tkfont
from typing import Tuple
from src.utils import *


# import tkinter as tk
# import tkinter.font as tkfont
# from typing import Tuple

def create_pill_with_embedded_entry(
    parent: tk.Widget,
    *,
    label: tk.Canvas,
    text: str = "Variation 1 Designs total:",
    value: str = "4",
    font_size: int = 20,
    # внешняя пилюля
    pill_bg: str = "#b3b3b3",   # фон внешней пилюли
    r: int = 22,
    pad_x: int = 20,
    pad_y: int = 12,
    gap: int = 12,
    shadow: bool = False,
    shadow_offset: int = 2,
    shadow_color: str = "#cfcfcf",
    text_color: str = "black",
    # правая капсула/entry (используем вашу create_entry)
    capsule_width: int = 56,
    capsule_height: int | None = None,  # если None — подгон по высоте пилюли
    capsule_r: int = 12,
    capsule_bg: str = "#e5e5e5",        # цвет заполнения капсулы
    entry_fg: str = "black",
    entry_justify: str = "center",
    entry_padding: int = 6,             # прокинем как padding в create_entry
    pack_: bool = True,
) -> Tuple[tk.Canvas, tk.Entry]:
    """
    Слева — текст, справа — ваша же капсула с Entry, встроенная внутрь пилюли.
    Требует доступной функции _rounded_rect и ваших create_pill_label/create_entry.
    """

    # font_obj = tkfont.Font(size=font_size)
    # text_w = int(font_obj.measure(text))
    # line_h = int(font_obj.metrics("linespace"))
    # h = int(line_h + pad_y*2)
    # w = int(pad_x + text_w + gap + capsule_width + pad_x)

    # # внешний canvas и пилюля
    # canvas = tk.Canvas(parent, width=w, height=h, highlightthickness=0, bd=0)
    # if pack_:
    #     canvas.pack()

    # if shadow and shadow_offset > 0:
    #     _rounded_rect(canvas, 0, shadow_offset, w, h, r, fill=shadow_color, outline="")

    # _rounded_rect(canvas, 0, 0, w, h, r, fill=pill_bg, outline="")

    # # текст слева
    # canvas.create_text(pad_x, h//2, text=text, fill=text_color, font=font_obj, anchor="w")
    canvas = label
    # print(canvas.winfo_width(), canvas.winfo_height())
    # h = 40
    # w = 120
    h = canvas.winfo_height()
    w = canvas.winfo_width()
    
    # размеры правой капсулы (чуть ниже полной высоты — визуально мягче)
    cap_h = h if capsule_height is None else capsule_height
    if capsule_height is None:
        cap_h = h - max(2, pad_y // 2)

    # создаём КАПСУЛУ через вашу create_entry (она вернёт entry и ЕЁ canvas)
    # ВАЖНО: bg внутреннего canvas == цвет внешней пилюли (pill_bg), чтобы углы
    # вокруг капсулы «растворялись» в пилюле и не было второго прямоугольника.
    text_info = TextInfo(text=value, color=entry_fg, font_size=font_size, justify=entry_justify)
    info = EntryInfo(
        parent=canvas,
        radius=capsule_r,
        width=capsule_width,
        height=cap_h,
        text_info=text_info,
        padding_x=entry_padding,
        padding_y=entry_padding,
        border=0,
        border_color="#C0C0C0",
        fill=capsule_bg,
        background_color=pill_bg,
        foreground_color=entry_fg,
    )
    entry, entry_canvas = create_entry(info=info)
    #     parent=canvas,             # родитель временно не важен — встроим create_window
    #     r=capsule_r,
    #     width=capsule_width,
    #     height=cap_h,
    #     font_size=font_size,
    #     text=value,
    #     bg=pill_bg,                # фон canvas под капсулой = фон pilly
    #     entry_bg=capsule_bg,       # фон самого поля = фон капсулы
    #     fg=entry_fg,
    #     justify=entry_justify,
    #     border=0,
    #     border_color="#C0C0C0",
    #     padding=entry_padding
    # )

    # не даём ему самовольно pack'нуться (если в вашей версии pack стоит внутри —
    # добавьте в create_entry флаг, либо сразу после вызова сделайте:)
    try:
        entry_canvas.pack_forget()
    except Exception:
        pass

    # позиционируем правую капсулу в большой пилюле
    cx1 = w - pad_x
    cx0 = cx1 - capsule_width
    cy0 = (h - cap_h) // 2
    cy1 = cy0 + cap_h

    canvas.create_window((cx0 + cx1)//2, (cy0 + cy1)//2,
                         window=entry_canvas, width=capsule_width, height=cap_h)

    return canvas, entry


from src.utils import create_pill_label
if __name__ == "__main__":
    root = tk.Tk()
    # label = create_pill_label(root, text="Variation 1 Designs total:")
    # entry, canvas = create_entry(label)
    # canvas.pack_forget()

    # cx1 = canvas.winfo_width() - 20
    # cx0 = cx1 - 56
    # cy0 = (canvas.winfo_height() - 34) // 2
    # cy1 = cy0 + 34

    # canvas.create_window((cx0 + cx1)//2, (cy0 + cy1)//2,
    #                      window=canvas, width=56, height=34)

    # Basic layer
    text_info = TextInfo(text="Variation 1 Designs total:", color="black", font_size=36)
    pill_info = PillLabelInfo(
        width=900,
        parent=root, 
        text_info=text_info, 
        fill="#e5e5e5", 
        radius=22,
        padding_x=24,
        padding_y=12
    )
    entry_info = EntryInfo(
        parent=root,
        radius=12,
        width=56,
        height=60,
        text_info=TextInfo(text="4", color="black", font_size=12),
        padding_x=6,
        padding_y=12,
        fill="#008000",
    )
    button_info = PillLabelInfo(
        parent=root,
        radius=12,
        width=56,
        height=60,
        padding_x=6,
        padding_y=12,
        fill="#008000",
    )
    canvas, entry_canvas, entry = append_object_to_pill_label(
        pill_info, 
        entry_info,
        object_padding_x=-80
    )
    canvas, button_canvas, _ = append_object_to_pill_label(
        pill_info,
        button_info,
        pill_canvas=canvas,
        object_padding_x=-150
    )
    root.mainloop()
    

# if __name__ == "__main__":
#     root = tk.Tk()
#     text_info = TextInfo(text="4", color="black", font_size=12)
#     pill_label_widget = EntryInfo(
#         width=400,
#         parent=root,
#         text_info=text_info, 
#         padding_x=24, 
#         padding_y=16, 
#         radius=20, 
#         tag="label",
#         fill="#e5e5e5",
#         border=0,
#         border_color="#C0C0C0",
#     )
#     label = create_entry(info=pill_label_widget)
#     # entry, canvas = create_entry(root, text="4")
#     root.mainloop()
