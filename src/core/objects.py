from typing import Optional, Callable
from dataclasses import dataclass

import tkinter as tk


@dataclass
class TextInfo:
    """
    Represents configuration for displaying styled text.

    Attributes:
        text: The content of the text.
        color: The color of the text.
        font_size: The size of the font.
        font_family: The font family to use (default: "Myriad Pro").
        font_weight: The weight of the font, such as "normal" or "bold".
        justify: Text alignment (e.g., "left", "center", "right").
    """
    text: str
    color: str
    font_size: int
    font_family: str = "Myriad Pro"
    font_weight: str = "normal"
    justify: str = "center"


@dataclass
class BaseWidgetInfo:
    """
    Defines a general set of properties for graphical components.

    Attributes:
        parent: The parent component to which this element belongs.
        width: The width of the component (default: 0, auto-size).
        height: The height of the component (default: 0, auto-size).
        radius: Corner radius for rounded shapes (default: 0).
        background_color: Background color of the component.
        foreground_color: Foreground color of the component.
        text_info: Styling configuration for text, if applicable.
        border: The width of the border (default: 0, no border).
        border_color: The color of the border, if defined.
        padding_x: Horizontal padding inside the component (default: 0).
        padding_y: Vertical padding inside the component (default: 0).
        tag: A string identifier used for tagging or referencing the component.
    """
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
    """
    Extends BaseWidgetInfo with additional properties tailored for buttons.

    Attributes:
        button_color: The default color of the button.
        hover_color: The color of the button when hovered by the pointer.
        active_color: The color of the button when actively pressed.
        command: The function executed when the button is clicked.
    """
    button_color: str = "#808080"
    hover_color: str = "#3f3f3f"
    active_color: str = "#dcdcdc"
    command: Optional[Callable[[], None]] = None


@dataclass
class EntryInfo(BaseWidgetInfo):
    """
    Extends BaseWidgetInfo with additional properties specific to entry fields.

    Attributes:
        fill: The background fill color of the entry field.
    """
    fill: str = "white"
    

@dataclass
class PillLabelInfo(BaseWidgetInfo):
    """
    Extends BaseWidgetInfo with additional properties specific to pill-shaped labels.

    Attributes:
        fill: The background fill color of the label.
    """
    fill: str = "#e5e5e5"
