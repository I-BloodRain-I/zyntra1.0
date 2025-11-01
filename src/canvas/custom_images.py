from __future__ import annotations

import os
import logging

import tkinter as tk
from tkinter import filedialog, messagebox

from src.core import COLOR_TEXT, COLOR_BG_DARK, COLOR_PILL
from src.core.app import COLOR_BG_SCREEN
from src.utils import create_button, ButtonInfo, TextInfo, create_entry, EntryInfo


logger = logging.getLogger(__name__)


class CustomImagesManager:
    """Manages custom images for individual image objects.
    
    Each image object stores its own list of custom image paths (name -> path dict).
    The combobox shows custom images for the currently selected object only.
    Import/Remove buttons manage the list for that specific object.
    """

    def __init__(self, screen: tk.Widget) -> None:
        self.s = screen

    def get_custom_images_for_object(self, obj_meta: dict) -> dict:
        """Get the custom images dict for a specific object."""
        try:
            # Use .get() method which works for both dict and CanvasObject
            custom_imgs = obj_meta.get("custom_images", None)
            if custom_imgs is None:
                obj_meta["custom_images"] = {}
                return obj_meta["custom_images"]
            return custom_imgs
        except Exception:
            logger.exception("Failed to get custom_images for object")
            return {}

    def import_custom_image_for_object(self, obj_meta: dict) -> None:
        """Import a new custom image for the given object."""
        path = filedialog.askopenfilename(
            title="Select Custom Image", 
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.svg"),
            ]
        )
        if not path:
            return
        
        if not os.path.exists(path):
            messagebox.showerror("Import failed", "Selected file does not exist")
            return
        
        try:
            base_name = os.path.splitext(os.path.basename(path))[0]
        except Exception:
            base_name = "CustomImage"
        
        # Prompt for display name
        try:
            win = tk.Toplevel(self.s)
            win.title("Image name")
            win.configure(bg=COLOR_BG_SCREEN)
            win.transient(self.s)
            win.grab_set()
            frm = tk.Frame(win, bg=COLOR_BG_SCREEN)
            frm.pack(padx=12, pady=0)
            tk.Label(frm, text="Enter display name for this image:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=("Myriad Pro", 12)).pack(anchor="w", pady=(8, 0))
            tk.Label(frm, text="(as on Amazon)", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=("Myriad Pro", 8)).pack(anchor="center", pady=(0, 15))
            entry, _entry_canvas = create_entry(
                EntryInfo(
                    parent=frm,
                    width=200,
                    text_info=TextInfo(text=base_name, color=COLOR_TEXT, font_size=12),
                    fill=COLOR_PILL,
                    background_color=COLOR_BG_SCREEN,
                    radius=10,
                    padding_x=12,
                    padding_y=6,
                )
            )
            btn_row = tk.Frame(frm, bg=COLOR_BG_SCREEN)
            btn_row.pack(fill="x", pady=(15, 12))
            
            def _confirm():
                display = (entry.get() or base_name).strip() or base_name
                if not display:
                    messagebox.showwarning("Invalid Name", "Image name cannot be empty")
                    return
                
                try:
                    # Add to this object's custom images
                    custom_imgs = self.get_custom_images_for_object(obj_meta)
                    custom_imgs[display] = path
                    # Explicitly assign back to ensure persistence
                    obj_meta["custom_images"] = custom_imgs
                    logger.info(f"Added custom image '{display}' to object. Object now has {len(custom_imgs)} custom images: {list(custom_imgs.keys())}")
                    
                    # Set this as the selected custom image for the object
                    obj_meta["custom_image"] = display
                except Exception:
                    logger.exception("Failed to add custom image to object")
                finally:
                    try:
                        win.grab_release()
                    except Exception:
                        pass
                    win.destroy()
                    
                # Refresh the combobox AFTER closing the dialog
                try:
                    if hasattr(self.s, "selection") and hasattr(self.s.selection, "select"):
                        sel = getattr(self.s.selection, "_selected", None)
                        if sel:
                            logger.info(f"Refreshing selection for cid={sel}")
                            self.s.selection.select(sel)
                except Exception:
                    logger.exception("Failed to refresh selection after import")
            
            def _cancel():
                try:
                    win.grab_release()
                except Exception:
                    pass
                win.destroy()
            
            ok_btn = create_button(
                ButtonInfo(
                    parent=btn_row,
                    text_info=TextInfo(text="OK", color=COLOR_TEXT, font_size=12),
                    background_color=COLOR_BG_SCREEN,
                    button_color="#737373",
                    hover_color=COLOR_BG_DARK,
                    active_color="#737373",
                    padding_x=12,
                    padding_y=6,
                    radius=10,
                    command=_confirm,
                )
            )
            cancel_btn = create_button(
                ButtonInfo(
                    parent=btn_row,
                    text_info=TextInfo(text="Cancel", color=COLOR_TEXT, font_size=12),
                    background_color=COLOR_BG_SCREEN,
                    button_color="#737373",
                    hover_color=COLOR_BG_DARK,
                    active_color="#737373",
                    padding_x=12,
                    padding_y=6,
                    radius=10,
                    command=_cancel,
                )
            )
            ok_btn.pack(side="left", padx=(48, 8))
            cancel_btn.pack(side="left")
            try:
                entry.focus_set()
            except Exception:
                pass
            try:
                self.s.update_idletasks()
                win.update_idletasks()
                px = self.s.winfo_rootx() + (self.s.winfo_width() - win.winfo_width()) // 2
                py = self.s.winfo_rooty() + (self.s.winfo_height() - win.winfo_height()) // 2
                win.geometry(f"+{max(0, px)}+{max(0, py)}")
            except Exception:
                pass
            self.s.wait_window(win)
        except Exception:
            logger.exception("Failed to open image name dialog")

    def remove_custom_image_from_object(self, obj_meta: dict) -> None:
        """Remove a custom image from the given object's list."""
        custom_imgs = self.get_custom_images_for_object(obj_meta)
        
        if not custom_imgs:
            messagebox.showinfo("Custom Images", "No custom images for this object")
            return
        
        # Get currently selected name from combobox
        current = ""
        if hasattr(self.s, "sel_custom_image"):
            current = str(self.s.sel_custom_image.get() or "").strip()
        
        if not current or current not in custom_imgs:
            messagebox.showinfo("Custom Images", "Please select an image to remove")
            return
        
        try:
            ok = messagebox.askyesno("Confirm", f"Remove '{current}' from this object?")
        except Exception:
            ok = True
        
        if not ok:
            return
        
        try:
            del custom_imgs[current]
            # Explicitly assign back to ensure persistence
            obj_meta["custom_images"] = custom_imgs
            
            # If this was the selected custom_image, clear it or set to first available
            if obj_meta.get("custom_image") == current:
                remaining = list(custom_imgs.keys())
                obj_meta["custom_image"] = remaining[0] if remaining else ""
            
            # Refresh the combobox
            if hasattr(self.s, "selection") and hasattr(self.s.selection, "select"):
                sel = getattr(self.s.selection, "_selected", None)
                if sel:
                    self.s.selection.select(sel)
            
            messagebox.showinfo("Removed", f"'{current}' removed from this object")
        except Exception:
            logger.exception("Failed to remove custom image")
