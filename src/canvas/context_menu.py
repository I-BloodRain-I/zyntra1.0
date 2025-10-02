import logging

import tkinter as tk
from typing import Optional, Callable, Sequence, Tuple, List

from src.utils import create_button, ButtonInfo, TextInfo, _rounded_rect

logger = logging.getLogger(__name__)


class CanvasContextPopup:
    """Rounded floating popup that supports any number of buttons.

    Usage examples:
        # New API (arbitrary buttons)
        popup = CanvasContextPopup(parent, buttons=[
            ("Duplicate", on_duplicate),
            ("Delete", on_delete),
            ("Bring to front", on_front),
        ])
        popup.show(x_root, y_root, close_bind_widget=some_widget)
    """

    def __init__(
        self,
        master: tk.Widget,
        panel_bg: str = "#2b2b2b",
        buttons: Optional[Sequence[Tuple[str, Callable[[], None]]]] = None,
        max_visible_buttons: int = 8,
    ) -> None:
        self.master = master
        self.panel_bg = panel_bg
        self._popup: Optional[tk.Toplevel] = None
        self._max_visible_buttons = max(1, int(max_visible_buttons))

        # Build internal button list with backward compatibility
        internal_buttons: List[Tuple[str, Callable[[], None]]] = []
        if buttons and len(buttons) > 0:
            for text, cmd in buttons:
                internal_buttons.append((str(text), cmd))
        # If still empty, provide a default Close button
        if not internal_buttons:
            internal_buttons.append(("Close", lambda: None))

        self._buttons = internal_buttons

    def destroy(self) -> None:
        try:
            if self._popup and self._popup.winfo_exists():
                self._popup.destroy()
        except Exception:
            logger.exception("Failed to destroy context popup")
        finally:
            self._popup = None

    def show(self, x_root: int, y_root: int, close_bind_widget: Optional[tk.Widget] = None) -> None:
        # Recreate popup fresh on each show
        self.destroy()
        popup = tk.Toplevel(self.master)
        self._popup = popup
        try:
            popup.overrideredirect(True)
        except Exception:
            logger.exception("Failed to set overrideredirect on popup")
        try:
            popup.attributes("-topmost", True)
        except Exception:
            logger.exception("Failed to set popup topmost attribute")

        # Transparent rounded corners using a color key
        magic = "#00ff01"
        try:
            popup.wm_attributes("-transparentcolor", magic)
        except Exception:
            logger.exception("Failed to set transparent color attribute")
        popup.configure(bg=magic)

        # Dimensions and layout
        btn_w = 160
        btn_h = 32
        pad = 8
        gap = 6
        num = len(self._buttons)
        total_w = btn_w + pad * 2
        content_h = pad * 2 + (btn_h * num) + (gap * max(0, num - 1))
        max_h = pad * 2 + (btn_h * min(num, self._max_visible_buttons)) + (gap * max(0, min(num, self._max_visible_buttons) - 1))

        cv = tk.Canvas(popup, width=total_w, height=max_h, bg=magic, highlightthickness=0, bd=0)
        cv.pack()

        # Rounded background sized to the viewport
        _rounded_rect(cv, 0, 0, total_w, max_h, 12, fill=self.panel_bg, outline="")

        def make_btn(text: str, cmd, y_center: int) -> tk.Canvas:
            info = ButtonInfo(
                parent=cv,
                width=btn_w,
                height=btn_h,
                radius=10,
                button_color="#3f3f3f",
                hover_color="#5a5a5a",
                active_color="#2a2a2a",
                text_info=TextInfo(text=text, color="#ffffff", font_size=12, font_weight="bold", justify="left"),
                padding_x=16,
                padding_y=10,
                command=cmd,
            )
            btn = create_button(info)
            try:
                btn.pack_forget()
            except Exception:
                logger.exception("Failed to pack_forget for context menu button")
            btn.configure(bg=self.panel_bg, highlightthickness=0, bd=0)
            cv.create_window(total_w // 2, y_center, window=btn, width=btn_w, height=btn_h)
            return btn

        # Create all buttons and wire to auto-destroy then call
        y = pad + btn_h // 2
        for idx, (label, callback) in enumerate(self._buttons):
            def _make_cmd(cb: Callable[[], None]) -> Callable[[], None]:
                def _wrapped() -> None:
                    self.destroy()
                    try:
                        cb()
                    except Exception:
                        logger.exception("Context menu button command failed")
                return _wrapped
            make_btn(str(label), _make_cmd(callback), y)
            y += btn_h + gap

        # Configure scroll region for long lists and support mouse wheel scrolling
        try:
            cv.configure(scrollregion=(0, 0, total_w, content_h))
        except Exception:
            logger.exception("Failed to configure scrollregion for context menu")

        if content_h > max_h:
            def _on_mousewheel(e):
                try:
                    delta = int(e.delta)
                except Exception:
                    delta = 0
                if delta != 0:
                    step = -1 if delta > 0 else 1
                    try:
                        cv.yview_scroll(step * 3, "units")
                    except Exception:
                        raise
                return "break"
            try:
                cv.bind("<MouseWheel>", _on_mousewheel)
            except Exception:
                logger.exception("Failed to bind mousewheel on context menu")

        # Auto-close conditions
        def on_focus_out(_):
            self.destroy()
        try:
            popup.bind("<FocusOut>", on_focus_out)
        except Exception:
            logger.exception("Failed to bind FocusOut on context menu")
        if close_bind_widget is not None:
            try:
                close_bind_widget.bind("<Button-1>", lambda _e: self.destroy(), add=True)
            except Exception:
                logger.exception("Failed to bind close on Button-1 for context menu")

        # Place and focus
        try:
            popup.update_idletasks()
            # Compute desired size and screen bounds, adjust if overflowing
            try:
                total_w = int(popup.winfo_width())
                total_h = int(popup.winfo_height())
            except Exception:
                total_w = 200
                total_h = 200
            try:
                screen_w = popup.winfo_screenwidth()
                screen_h = popup.winfo_screenheight()
            except Exception:
                screen_w = 1920
                screen_h = 1080
            place_x = int(x_root)
            place_y = int(y_root)
            # If bottom/right would overflow, move left/up to keep fully visible
            if place_x + total_w > screen_w:
                place_x = max(0, screen_w - total_w - 4)
            if place_y + total_h > screen_h:
                place_y = max(0, screen_h - total_h - 4)
            popup.geometry(f"+{place_x}+{place_y}")
            popup.deiconify()
            popup.focus_force()
        except Exception:
            logger.exception("Failed to place/focus context menu popup")


