import logging
import os
import threading
import time
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime
import json
from copy import deepcopy

import tkinter as tk
from tkinter import TclError, ttk, messagebox
from typing import Any, Dict, List
from PIL import ImageDraw, ImageChops, ImageFilter
from PIL import Image as _PILImage
from rembg import remove, new_session
import numpy as np
import math

from src.core.state import FONTS_PATH, INPUT_PATH, INTERNAL_PATH, MODEL_PATH, state
from src.core import (
    Screen,
    COLOR_BG_DARK,
    COLOR_BG_SCREEN,
    COLOR_TEXT,
    COLOR_BG_LIGHT,
    scale_px,
    font_from_pt,
    UI_SCALE,
    LOGS_PATH,
    OUTPUT_PATH,
    PRODUCTS_PATH,
)
from src.utils import *
from src.canvas import PdfExporter, ImageManager, PDFCombiner, PDFInfo
from src.screens.common.dropbox_handler import DEFAULT_COLOR, SUCCESS_COLOR, WARNING_COLOR, ERROR_COLOR, BASE_FOLDER, IMAGES_FOLDER, FILES_FOLDER, get_orders_info, Dropbox

logger = logging.getLogger(__name__)

DROPBOX_CLIENT = Dropbox()

model_session = new_session("u2net_custom", model_path=str(MODEL_PATH))

class OrderRangeScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        # Top line identical to LauncherSelectProduct
        # self.brand_bar(self)

        self.images = ImageManager(self)
        self._rotated_bounds_px = self.images.rotated_bounds_px
        self._rotated_bounds_mm = self.images.rotated_bounds_mm
        
        # Track processed files in current session to avoid overwriting
        self._processed_files = set()

        # Product tag (dark pill) below the top line
        tk.Label(self,
                 text=state.saved_product,
                 bg=COLOR_BG_DARK,
                 fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(24 * UI_SCALE))))\
            .pack(anchor="w", padx=scale_px(12), pady=(scale_px(8), 0))

        # Center area with header and inputs (no background panel)
        mid = ttk.Frame(self, style="Screen.TFrame"); mid.pack(expand=True, fill="both")
        try:
            mid.grid_columnconfigure(0, weight=1)
            mid.grid_columnconfigure(1, weight=0)
            mid.grid_columnconfigure(2, weight=1)
            mid.grid_rowconfigure(0, weight=1)
            mid.grid_rowconfigure(1, weight=0)
            mid.grid_rowconfigure(2, weight=2)
        except Exception:
            pass

        # Centered content container
        content = tk.Frame(mid, bg=COLOR_BG_SCREEN)
        content.grid(row=1, column=1)

        # Centered dark plaque title
        plaque = tk.Frame(content, bg=COLOR_BG_DARK)
        tk.Label(plaque,
                 text="Write order numbers to produce files:",
                 bg=COLOR_BG_DARK, fg=COLOR_TEXT,
                 font=("Myriad Pro", int(round(20 * UI_SCALE))))\
            .pack(padx=scale_px(12), pady=scale_px(6))
        plaque.pack(pady=(0, scale_px(12)))

        # Inputs row (compact, centered)
        lbl_font = ("Myriad Pro", int(round(24 * UI_SCALE)))
        ent_font = ("Myriad Pro", int(round(22 * UI_SCALE)))

        row_inputs = tk.Frame(content, bg=COLOR_BG_SCREEN)
        row_inputs.pack()

        # tk.Label(row_inputs, text="From:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=lbl_font).pack(side="left", padx=(0, 0))
        self.from_var = tk.StringVar(value=state.order_from)
        tk.Entry(row_inputs, textvariable=self.from_var, width=30, justify="center",
                 font=ent_font, bg="#ffffff", relief="flat").pack(side="left", pady=(4, 0))

        # Date range (Dropbox) inputs below order input
        date_font = ("Myriad Pro", int(round(19 * UI_SCALE)))
        date_row = tk.Frame(content, bg=COLOR_BG_SCREEN)
        date_row.pack(pady=(scale_px(8), 0))

        tk.Label(date_row, text="From:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=date_font).pack(side="left", padx=(0, scale_px(4)))
        self.drop_from_var = tk.StringVar(value=state.dropbox_from.strftime("%d-%m-%Y"))
        vcmd = (self.register(self._validate_date_mask), "%P")
        tk.Entry(
            date_row,
            textvariable=self.drop_from_var,
            width=12,
            justify="center",
            font=date_font,
            bg="#ffffff",
            relief="flat",
            validate="key",
            validatecommand=vcmd,
        ).pack(side="left")

        # Formats + DPI row (below date range)
        fmt_row = tk.Frame(content, bg=COLOR_BG_SCREEN)
        fmt_row.pack(pady=(scale_px(8), 0))

        tk.Label(fmt_row, text="Formats:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=date_font).pack(side="left", padx=(0, scale_px(4)))
        self.format_var = tk.StringVar(value="pdf")
        tk.Entry(
            fmt_row,
            textvariable=self.format_var,
            width=15,
            justify="center",
            font=date_font,
            bg="#ffffff",
            relief="flat",
        ).pack(side="left")

        tk.Label(fmt_row, text="DPI:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=date_font).pack(side="left", padx=(scale_px(20), scale_px(4)))
        self.dpi_var = tk.StringVar(value="1200")
        tk.Entry(
            fmt_row,
            textvariable=self.dpi_var,
            width=6,
            justify="center",
            font=date_font,
            bg="#ffffff",
            relief="flat",
        ).pack(side="left")

        tk.Label(date_row, text="To:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=date_font).pack(side="left", padx=(scale_px(20), scale_px(4)))
        self.drop_to_var = tk.StringVar(value=state.dropbox_to.strftime("%d-%m-%Y"))
        tk.Entry(
            date_row,
            textvariable=self.drop_to_var,
            width=12,
            justify="center",
            font=date_font,
            bg="#ffffff",
            relief="flat",
            validate="key",
            validatecommand=vcmd,
        ).pack(side="left")

        # tk.Label(row_inputs, text="To:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=lbl_font).pack(side="left", padx=(scale_px(50), 0))
        # self.to_var = tk.StringVar(value=state.order_to)
        # tk.Entry(row_inputs, textvariable=self.to_var, width=8, justify="center",
        #          font=ent_font, bg="#ffffff", relief="flat").pack(side="left")

        # ---------------------------------------------------------------------
        # Progress bar (between ID selection and logger)
        # ---------------------------------------------------------------------
        pb_wrap = tk.Frame(content, bg=COLOR_BG_SCREEN)
        pb_wrap.pack(pady=(scale_px(14), 0))
        self.progress = ttk.Progressbar(pb_wrap, orient="horizontal", length=486, mode="determinate", maximum=100)
        self.progress.pack(ipady=scale_px(12), pady=(5, 5))
        self.progress["value"] = 100
        # ---------------------------------------------------------------------

        # Scrollable logger area inside a rounded "pill" container
        pill_info = PillLabelInfo(
            width=900,
            height=300,
            parent=self,
            text_info=TextInfo(
                text="",
                color=COLOR_TEXT,
                font_size=22,
            ),
            fill=COLOR_BG_LIGHT,
            background_color=COLOR_BG_SCREEN,
            radius=15,
            padding_x=20,
            padding_y=12,
        )
        self.logger_canvas = create_pill_label(pill_info)
        # self.logger_canvas.place(relx=0.5, rely=0.8, anchor="center")
        self.logger_canvas.pack(after=self.progress, anchor="center", pady=scale_px(12))

        inner_w = pill_info.width - 2 * pill_info.padding_x
        inner_h = pill_info.height - 2 * pill_info.padding_y

        log_frame = tk.Frame(self.logger_canvas, bg=COLOR_BG_LIGHT)
        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            bg=COLOR_BG_LIGHT,
            fg=COLOR_TEXT,
            relief="flat",
            bd=0,
            font=("Myriad Pro", int(round(14 * UI_SCALE))),
        )
        yscroll = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=yscroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.log_text.configure(state="disabled")

        self.logger_canvas.create_window(
            pill_info.padding_x,
            pill_info.padding_y,
            anchor="nw",
            window=log_frame,
            width=inner_w,
            height=inner_h,
        )

        # Default logger color and tags cache for per-line colors
        self.log_default_color = DEFAULT_COLOR
        self._log_color_tags = {}

        # Keep a reference to Start button (to disable during progress)
        self.start_btn = create_button(
            ButtonInfo(
                parent=self,
                text_info=TextInfo(
                    text="Start",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                button_color=COLOR_BG_DARK,
                hover_color="#3f3f3f",
                active_color=COLOR_BG_DARK,
                padding_x=20,
                padding_y=12,
                command=self._start,
            )
        )
        self.start_btn.place(relx=0.995, rely=0.99, anchor="se")
        # Remember original cursor to restore after processing
        try:
            self._start_btn_default_cursor = self.start_btn.cget("cursor")
        except Exception:
            self._start_btn_default_cursor = ""

        # Bottom-left Go Back button (styled like font_info)
        back_btn = create_button(
            ButtonInfo(
                parent=self,
                text_info=TextInfo(
                    text="Cancel",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                button_color=COLOR_BG_DARK,
                hover_color="#3f3f3f",
                active_color=COLOR_BG_DARK,
                padding_x=20,
                padding_y=12,
                command=self._on_cancel,
            )
        )
        back_btn.place(relx=0.005, rely=0.99, anchor="sw")

        # Hotkeys: Enter → Start, Escape → Back (accept optional event)
        self.app.bind("<Return>", lambda _e=None: self._start())
        self.app.bind("<Escape>", lambda _e=None: self._on_cancel())

        # Processing state flag to prevent multiple concurrent starts
        self._is_processing = False
        # Cancellation flag
        self._cancel_requested = False

    # ------------------------------ Logging ------------------------------

    def log(self, message: str, color: str = None) -> None:
        if not hasattr(self, "log_text"):
            return
        current_time = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_text.configure(state="normal")
            # Insert timestamp without color tag
            self.log_text.insert("end", f"[{current_time}] ")

            # Insert message with color tag (if provided/defaulted)
            selected = color or getattr(self, "log_default_color", DEFAULT_COLOR)
            tag_name = f"fg_{selected}"
            if tag_name not in self._log_color_tags:
                self.log_text.tag_configure(tag_name, foreground=selected)
                self._log_color_tags[tag_name] = True
            self.log_text.insert("end", message, tag_name)

            # Newline untagged
            self.log_text.insert("end", "\n")
            self.log_text.see("end")

            current_day = datetime.now().strftime("%Y-%m-%d")
            if not (LOGS_PATH / (current_day + ".log")).exists():
                with open(LOGS_PATH / (current_day + ".log"), "w", encoding="utf-8") as f:
                    f.write(f"[{current_time}] {message}\n")
            else:
                with open(LOGS_PATH / (current_day + ".log"), "a", encoding="utf-8") as f:
                    f.write(f"[{current_time}] {message}\n")
        except TclError:
            pass
        finally:
            try:
                self.log_text.configure(state="disabled")
            except Exception:
                pass

    # ------------------------------- Start --------------------------------
    def _get_image_customization_objs(self, root_obj: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(root_obj, dict):
            root_obj_iter = [root_obj]
        else:
            root_obj_iter = root_obj

        founded_objs: List[Dict[str, Any]] = []
        for object in root_obj_iter:
            for key, value in object.items():
                if isinstance(value, (set, list, tuple, dict)):
                    founded_obj = self._get_image_customization_objs(value)
                    if isinstance(founded_obj, dict):
                        founded_objs.append(object)
                    elif isinstance(founded_obj, list) and founded_obj:
                        founded_objs.extend(founded_obj)
                if key == "type" and value == "ImageCustomization":
                    return object

        return founded_objs

    def _collect_customization_info(self, order_info: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        if "customizationInfo" not in order_info:
            return {"status": "error", "message": "Customization info not found"}
        if "version3.0" not in order_info["customizationInfo"]:
            return {"status": "error", "message": "Customization info version 3.0 not found"}
        if "surfaces" not in order_info["customizationInfo"]["version3.0"]:
            return {"status": "error", "message": "Surfaces not found"}

        objects = {"front": [], "back": []}
        for i, surface in enumerate(order_info["customizationInfo"]["version3.0"]["surfaces"]):
            side = "front" if i == 0 else "back"
            for area in surface['areas']:
                if area["customizationType"] == "Options":
                    if not area["optionImage"] or not area["optionValue"] or area["optionValue"].lower().startswith("NEIN"):
                        continue
                    if (area["optionValue"].lower() in ["nein", "ja"] or area["optionValue"].lower().startswith("nein ") or area["optionValue"].lower().startswith("ja ")) and str(order_info).count(area["optionImage"]) > 3:
                        continue
                    objects[side].append({
                        "type": "options",
                        "label": area["label"].strip(),
                        "value": area["optionValue"],
                        "image_url": area["optionImage"]
                    })
                elif area["customizationType"] == "TextPrinting":
                    if not area['text']:
                        continue

                    font_family = area["fontFamily"]
                    with open(FONTS_PATH / "fonts.json", "r", encoding="utf-8") as f:
                        all_fonts = json.load(f)
                    if font_family not in all_fonts:
                        return {"status": "error", "message": f"Font family {font_family} not found"}

                    objects[side].append({
                        "type": "text",
                        "color": area["fill"],
                        "font_family": area["fontFamily"],
                        "size": area["Dimensions"],
                        "position": area["Position"],
                        "label": area["label"].strip(),
                        "text": area["text"],
                    })
                elif area["customizationType"] == "ImagePrinting":
                    images = self._get_image_customization_objs(order_info["customizationData"])
                    for image in images:
                        image_transform_info = image["buyerPlacement"]
                        image_meta = image["children"][0]
                        if not image_meta["image"]["imageName"]:
                            continue
                        objects[side].append({
                            "type": "image",
                            "size": image_transform_info["dimension"],
                            "position": image_transform_info["position"],
                            "scale": image_transform_info["scale"],
                            "rotation": image_transform_info["angleOfRotation"],
                            "label": image_meta["label"].strip(),
                            "image_path": image_meta["image"]["imageName"],
                            "mask_size": image["dimension"],
                            "mask_position": image["position"],
                        })
                else:
                    raise RuntimeError(f"Unexpected type: {area["customizationType"]}")

        return {"status": "success", "data": objects}

    def _download_image_from_amazon(self, image_url: str) -> Dict[str, Union[str, Image.Image]]:
        retries = 3
        image_name = image_url.split("/")[-1]
        while retries > 0:
            if getattr(self, "_cancel_requested", False):
                return {"status": "error", "message": "Cancelled"}
            try:
                self.log(f"Downloading image {image_name} from Amazon")
                response = requests.get(image_url)
                if response.status_code != 200:
                    self.log(f"Failed to download image {image_name} from Amazon: {response.status_code}. Retrying...")
                    retries -= 1
                    time.sleep(5)
                    continue
                return {"status": "success", "image": Image.open(BytesIO(response.content))}
            except Exception as e:
                self.log(f"Failed to download image {image_name} from Amazon: {e}. Retrying...")
                retries -= 1
                time.sleep(5)
                continue
        return {"status": "error", "message": f"Failed to download image {image_name} from Amazon"}

    def _crop_image(self, image: Image.Image) -> Image.Image:
        return image.crop(image.getbbox())

    def _remove_background(self, image: Image.Image) -> Image.Image:
        return remove(image, session=model_session)

    def _download_image_from_dropbox(self, parent_folder: str, child_folder: str, image_path: str) -> Dict[str, Union[str, Image.Image]]:
        try:
            self.log(f"Downloading image {image_path} from Dropbox")
            info = DROPBOX_CLIENT.download_big_file(f"{BASE_FOLDER}/{parent_folder}/{FILES_FOLDER}/{child_folder}/{IMAGES_FOLDER}/{image_path}", str(INTERNAL_PATH) + "/", raw_data=True)
            if info is None:
                return {"status": "error", "message": f"Image {child_folder}/{image_path} not found in Dropbox"}
            img_ = Image.open(info[1])
            return {"status": "success", "image": img_}
        except Exception as e:
            logger.exception("Failed download image from dropbox")
            return {"status": "error", "message": f"Failed download image from dropbox: {e}"}

    def _transform_amazon_image(
        self,
        im: Image.Image,
        scale: float,
        angle_deg: float,
        place_xy: Tuple[float, float],
        mask_rect: Tuple[int, int, int, int],
        canvas_size: Tuple[int, int] = (2000, 2000),
        rotate_resample: str = "bicubic",
        apply_unsharp: bool = True,
        unsharp_radius: float = 0.6,
        unsharp_percent: int = 80,
        unsharp_threshold: int = 2,
    ) -> Image.Image:
        """
        1) If scale<1, resize with Lanczos (best for downscale) to improve crispness.
        2) Premultiply alpha to minimize dark/bright fringes at transparency edges.
        3) Apply affine transform (rotation + translation only) so that ORIGINAL TL maps to place_xy.
        4) Unpremultiply alpha back to straight RGBA.
        5) Mask the canvas (outside mask -> transparent).
        6) Optional UnsharpMask for extra crispness.
        """
        assert 0 < scale <= 1, "scale must be in (0,1]."
        if im.mode != "RGBA":
            im = im.convert("RGBA")

        # 1) Downscale with Lanczos (only if needed)
        W, H = im.size
        new_w = max(1, int(round(W * scale)))
        new_h = max(1, int(round(H * scale)))

        lanczos = _PILImage.Resampling.LANCZOS
        bicubic = _PILImage.Resampling.BICUBIC
        bilinear = _PILImage.Resampling.BILINEAR
        nearest = _PILImage.Resampling.NEAREST
        affine_method = _PILImage.Transform.AFFINE

        im_scaled = im.resize((new_w, new_h), lanczos) if (new_w != W or new_h != H) else im

        # 2) Premultiply alpha
        arr = np.asarray(im_scaled).astype(np.float32)  # HxWx4
        rgb = arr[..., :3]
        a = arr[..., 3:4] / 255.0
        rgb_premult = rgb * a
        arr_pm = np.concatenate([rgb_premult, a * 255.0], axis=-1).astype(np.uint8)
        im_pm = Image.fromarray(arr_pm, mode="RGBA")

        # 3) Affine rotation+translation with exact anchoring for ORIGINAL TL -> place_xy
        k = 1.0  # scale already applied
        theta = math.radians(angle_deg)
        c, s = math.cos(theta), math.sin(theta)
        px, py = place_xy

        # inverse matrix for transform (canvas->source)
        inv_a =  c / k
        inv_b =  s / k
        inv_d = -s / k
        inv_e =  c / k
        inv_c = -(inv_a * px + inv_b * py)
        inv_f = -(inv_d * px + inv_e * py)

        if rotate_resample == "bicubic":
            resamp = bicubic
        elif rotate_resample == "bilinear":
            resamp = bilinear
        elif rotate_resample == "nearest":
            resamp = nearest
        else:
            resamp = bicubic

        canvas_w, canvas_h = canvas_size
        warped_pm = im_pm.transform(
            size=(canvas_w, canvas_h),
            method=affine_method,
            data=(inv_a, inv_b, inv_c, inv_d, inv_e, inv_f),
            resample=resamp,
            fillcolor=(0, 0, 0, 0),
        )

        # 4) Unpremultiply alpha
        arr_w = np.asarray(warped_pm).astype(np.float32)
        rgb_w = arr_w[..., :3]
        a_w = arr_w[..., 3:4] / 255.0
        eps = 1e-6
        rgb_unpm = np.where(a_w > eps, rgb_w / np.maximum(a_w, eps), 0.0)
        arr_unpm = np.concatenate([np.clip(rgb_unpm, 0, 255), np.clip(a_w * 255.0, 0, 255)], axis=-1).astype(np.uint8)
        warped = Image.fromarray(arr_unpm, mode="RGBA")

        # 5) Apply rectangular mask
        mx, my, mw, mh = mask_rect
        mask = Image.new("L", (canvas_w, canvas_h), 0)
        ImageDraw.Draw(mask).rectangle([mx, my, mx + mw, my + mh], fill=255)
        r, g, b, a = warped.split()
        a_masked = ImageChops.multiply(a, mask)
        out = Image.merge("RGBA", (r, g, b, a_masked))

        # 6) Optional sharpening
        if apply_unsharp:
            out = out.filter(ImageFilter.UnsharpMask(radius=unsharp_radius, percent=unsharp_percent, threshold=unsharp_threshold))

        return out.crop((mx, my, mx + mw, my + mh))

    def _apply_mask(
        self, 
        im: Image.Image, 
        template_path: Path, 
        mask_path: Path
    ) -> Dict[str, Any]:

        def largest_component_bool(bool_mask):
            """Return the largest 4-connected component from a boolean mask.

            Args:
                bool_mask: 2D boolean array with candidate pixels set to True.

            Returns:
                2D boolean array that keeps only the largest component, or None if empty.
            """
            h, w = bool_mask.shape
            if not bool_mask.any():
                return None
            visited = np.zeros((h, w), dtype=bool)
            best = None
            best_len = 0
            for i in range(h):
                for j in range(w):
                    if bool_mask[i, j] and not visited[i, j]:
                        stack = [(i, j)]
                        visited[i, j] = True
                        coords = []
                        while stack:
                            y, x = stack.pop()
                            coords.append((y, x))
                            if y>0   and bool_mask[y-1,x] and not visited[y-1,x]: visited[y-1,x]=True; stack.append((y-1,x))
                            if y+1<h and bool_mask[y+1,x] and not visited[y+1,x]: visited[y+1,x]=True; stack.append((y+1,x))
                            if x>0   and bool_mask[y,x-1] and not visited[y,x-1]: visited[y,x-1]=True; stack.append((y,x-1))
                            if x+1<w and bool_mask[y,x+1] and not visited[y,x+1]: visited[y,x+1]=True; stack.append((y,x+1))
                        if len(coords) > best_len:
                            best_len = len(coords)
                            m = np.zeros((h, w), dtype=bool)
                            ys, xs = zip(*coords)
                            m[ys, xs] = True
                            best = m
            return best

        def content_active_bbox(img_rgba, thr=1):
            """Compute the bounding box of non-transparent pixels in an RGBA image.

            Args:
                img_rgba: RGBA PIL image.
                thr: Alpha threshold; pixels with alpha > thr are considered active.

            Returns:
                (left, top, right, bottom) bbox of active content, or None if empty.
            """
            a = np.array(img_rgba.split()[-1], dtype=np.uint8)
            ys, xs = np.where(a > thr)
            if ys.size == 0:
                return None
            top, left = int(ys.min()), int(xs.min())
            bottom, right = int(ys.max()) + 1, int(xs.max()) + 1
            return (left, top, right, bottom)

        def scale_min_cover_active(img_rgba, target_w, target_h, thr=1):
            """Cover-fit using only the active (non-transparent) content region.

            Args:
                img_rgba: RGBA PIL image that may contain transparent padding.
                target_w: Target width to cover.
                target_h: Target height to cover.
                thr: Alpha threshold for active region detection.

            Returns:
                RGBA image of exactly (target_w, target_h) with content scaled
                by minimal cover based on its active bbox.
            """
            bbox = content_active_bbox(img_rgba, thr=thr)
            if bbox is None:
                return Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            l, t, r, b = bbox
            core = img_rgba.crop((l, t, r, b))
            w, h = core.size
            s = max(target_w / w, target_h / h)
            nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
            scaled = core.resize((nw, nh), Image.LANCZOS)
            x0 = (nw - target_w) // 2
            y0 = (nh - target_h) // 2
            return scaled.crop((x0, y0, x0 + target_w, y0 + target_h))

        def paste_with_alpha(template_rgba, content_rgba, alpha_u8, top_left):
            """Composite content onto template using an 8-bit alpha matte.

            Args:
                template_rgba: Background RGBA image.
                content_rgba: Foreground RGBA image sized to the matte.
                alpha_u8: 2D uint8 alpha (0..255) in template coordinates.
                top_left: (left, top) paste position.

            Returns:
                New RGBA image after compositing.
            """
            result = template_rgba.copy()
            result.paste(content_rgba, top_left, Image.fromarray(alpha_u8, mode="L"))
            return result

        if not template_path.exists():
            logger.error(f"Template path {template_path} does not exist")
            return {"status": "error", "message": f"Template path {template_path} does not exist"}
        template = Image.open(template_path).convert("RGBA")

        if not mask_path.exists():
            logger.error(f"Mask path {mask_path} does not exist")
            return {"status": "error", "message": f"Mask path {mask_path} does not exist"}
        mask_img = Image.open(mask_path).convert("RGBA")

        if mask_img.size != template.size:
            mask_img = mask_img.resize(template.size, Image.NEAREST)

        if im.mode != "RGBA":
            im = im.convert("RGBA")

        cw = max(template.size[0], mask_img.size[0])
        ch = max(template.size[1], mask_img.size[1])
        if template.size != (cw, ch):
            t = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); t.paste(template, (0, 0), template); template = t
        if mask_img.size != (cw, ch):
            m = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); m.paste(mask_img, (0, 0), mask_img); mask_img = m

        alpha = np.array(mask_img.split()[-1], dtype=np.uint8)
        inv_alpha = 255 - alpha
        window = largest_component_bool(inv_alpha > 0)
        if window is None:
            return {"status": "error", "message": "No window found"}

        ys, xs = np.where(window)
        top, left = int(ys.min()), int(xs.min())
        bottom, right = int(ys.max()) + 1, int(xs.max()) + 1
        bw, bh = right - left, bottom - top

        fitted = scale_min_cover_active(im, bw, bh, thr=1)
        matte = (window[top:bottom, left:right].astype(np.uint8) * 255)

        result = paste_with_alpha(template, fitted, matte, (left, top))
        return {"status": "success", "image": result}

    def _prepare_order_data(self, parent_folder: str, child_folder: str, order_info: Dict[str, Any], order_i: int, total_orders: int) -> Dict[str, Any]:
        if "quantity" not in order_info:
            return {"status": "error", "message": "Quantity not found"}

        result = self._collect_customization_info(order_info)
        if result["status"] == "error":
            return {"status": "error", "message": result["message"]}
        customization_info = result["data"]

        total_download_image_count = 0
        total_loaded_image_count = 0
        for side in customization_info:
            for object in customization_info[side]:
                if object["type"] == "options":
                    total_download_image_count += 1
                if object["type"] == "image":
                    total_loaded_image_count += 1
        self.log(f"[{order_i}/{total_orders}] Total images to download from Amazon: {total_download_image_count}; from Dropbox: {total_loaded_image_count}")

        downloaded_image_count = 0
        loaded_image_count = 0
        for side in customization_info:
            for object in customization_info[side]:
                if getattr(self, "_cancel_requested", False):
                    return {"status": "error", "message": "Cancelled"}
                
                if object["type"] == "image":
                    image_info = self._download_image_from_dropbox(parent_folder, child_folder, object["image_path"])
                    if image_info["status"] == "error":
                        return {"status": "error", "message": image_info["message"]}
                    else:
                        loaded_image_count += 1
                        self.log(f"[{order_i}/{total_orders}] Image {loaded_image_count}/{total_loaded_image_count} downloaded from Dropbox")
                        image = self._transform_amazon_image(
                            im=image_info["image"], 
                            scale=object["scale"]["scaleX"], 
                            angle_deg=object["rotation"], 
                            place_xy=[object["position"]["x"], object["position"]["y"]], 
                            mask_rect=[object["mask_position"]["x"], object["mask_position"]["y"], object["mask_size"]["width"], object["mask_size"]["height"]]
                        )
                        object["loaded_image"] = image

                elif object["type"] == "options":
                    image_info = self._download_image_from_amazon(object["image_url"])
                    if image_info["status"] == "error":
                        return {"status": "error", "message": image_info["message"]}
                    else:
                        downloaded_image_count += 1
                        self.log(f"[{order_i}/{total_orders}] Image {downloaded_image_count}/{total_download_image_count} downloaded from Amazon")
                        if not object["image_url"].lower().endswith(".png"):
                            image_info["image"] = self._remove_background(image_info["image"])
                        image = self._crop_image(image_info["image"])
                        object["loaded_image"] = image

        return {"status": "success", "data": customization_info, "asin": order_info["asin"], "quantity": order_info["quantity"]}

    def _make_pdf(
        self, 
        data: List[Tuple[Dict[str, Any], Dict[str, Any]]], 
        jig_size: Tuple[float, float], 
        pdf_start_oder_i: int, 
        pdf_end_oder_i: int,
        pdf_order: int = 1,
        dpi: int = 1200,
        formats: List[str] = None,
        front_barcode = None,
        back_barcode = None,
        barcode_text: str = None,
        reference_text: str = None,
        jig_cmyk: str = None
    ) -> Dict[str, str]:
        try:
            # Parse CMYK to RGBA for border color
            def _parse_cmyk_to_rgba(cmyk_str: str, default=(0, 0, 0, 255)) -> tuple[int, int, int, int]:
                try:
                    parts = [p.strip() for p in str(cmyk_str or "").split(",")]
                    # pad/truncate to 4
                    if len(parts) < 4:
                        parts += ["0"] * (4 - len(parts))
                    elif len(parts) > 4:
                        parts = parts[:4]
                    c, m, y, k = [float(p or 0) for p in parts]
                    # auto-detect scale: 0..1, 0..100, or 0..255
                    vals = [c, m, y, k]
                    maxv = max(vals)
                    if maxv <= 1.0:
                        scale = 1.0
                    elif maxv <= 100.0:
                        scale = 100.0
                    else:
                        scale = 255.0
                    c = max(0.0, min(1.0, c / scale))
                    m = max(0.0, min(1.0, m / scale))
                    y = max(0.0, min(1.0, y / scale))
                    k = max(0.0, min(1.0, k / scale))
                    r = int(round(255 * (1 - c) * (1 - k)))
                    g = int(round(255 * (1 - m) * (1 - k)))
                    b = int(round(255 * (1 - y) * (1 - k)))
                    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), 255)
                except Exception:
                    return default
            
            # Convert jig CMYK to RGBA for border
            border_color_rgba = _parse_cmyk_to_rgba(jig_cmyk or "0,0,0,0", default=(0, 0, 0, 255))
            
            def _remove_unprocessed_objs(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                return [item for item in items if item.get("processed", False)]

            exporter = PdfExporter(self)
            from pathlib import Path as _Path
            if formats is None:
                formats = ["pdf"]
            # Normalize formats
            fmts_norm: List[str] = []
            seen = set()
            for f in formats:
                ff = (f or "").strip().lower()
                if ff == "jpeg":
                    ff = "jpg"
                if ff in ("pdf", "png", "jpg") and ff not in seen:
                    seen.add(ff)
                    fmts_norm.append(ff)
            if not fmts_norm:
                fmts_norm = ["pdf"]

            # Helper function to generate unique filename with index if file was already processed in this session
            def _get_unique_base_path(base_name: str) -> _Path:
                """Generate a unique base path by checking if file already exists in current session."""
                base = OUTPUT_PATH / base_name
                base_path = base.resolve()
                
                # Check if any file with this base name was processed in current session
                base_str = str(base_path)
                matching_files = [f for f in self._processed_files if f.startswith(base_str)]
                
                if not matching_files:
                    # No files processed yet with this base name
                    return base_path
                
                # Find the next available index
                index = 2
                while True:
                    # Try base_name_2, base_name_3, etc.
                    new_base = OUTPUT_PATH / f"{base_name}_{index}"
                    new_base_path = new_base.resolve()
                    new_base_str = str(new_base_path)
                    
                    # Check if this indexed version was already processed
                    if not any(f.startswith(new_base_str) for f in self._processed_files):
                        return new_base_path
                    index += 1

            base_front = _get_unique_base_path(f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_front{f'_{pdf_order}' if pdf_order > 1 else ''}")
            base_back  = _get_unique_base_path(f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_back")

            front_items = []
            back_items = []
            for front, back in data:
                front_items.extend(front["objects"] if front else [])
                if back:
                    back_items.extend(back["objects"] if back else [])
            
            if front_barcode:
                front_barcode["processed"] = True
                front_items.append(front_barcode)
            if back_barcode:
                back_barcode["processed"] = True
                back_items.append(back_barcode)

            # Group items by export_file field
            def _group_by_export_file(items_list):
                """Group items by their export_file assignment, excluding slots"""
                grouped = {}
                for item in items_list:
                    if item.get("type") == "slot":
                        # Skip slots - they should not be exported
                        continue
                    else:
                        # Regular objects go to their assigned file
                        ef = item.get("export_file", "File 1")
                        if ef not in grouped:
                            grouped[ef] = []
                        grouped[ef].append(item)
                return grouped
            
            front_grouped = _group_by_export_file(front_items)
            back_grouped = _group_by_export_file(back_items)
            
            # Collect all export file names from both sides
            export_files_to_render = set(front_grouped.keys()) | set(back_grouped.keys())
            if not export_files_to_render:
                export_files_to_render = {"File 1"}  # Default fallback
            export_files_to_render = sorted(export_files_to_render)  # Sort for consistent ordering

            def _render_and_save(side_items: List[Dict[str, Any]], base: _Path) -> None:
                if not side_items:
                    return
                items = _remove_unprocessed_objs(side_items)
                if not items:
                    return
                did_pdf = False
                if "pdf" in fmts_norm:
                    p_pdf = str(base.with_suffix(".pdf"))
                    logger.debug("Rendering PDF: %s", p_pdf)
                    exporter.render_scene_to_pdf(p_pdf, items, jig_size[0], jig_size[1], dpi=dpi, barcode_text=barcode_text, reference_text=reference_text)
                    did_pdf = True
                    # Track this file as processed
                    self._processed_files.add(str(base))
                    # Always create PNG for PDF combiner (even if not in formats)
                    p_png = str(base.with_suffix(".png"))
                    exporter.save_last_render_as_png(p_png)
                    logger.debug(f"Saved PNG for combiner: {p_png}")
                # Ensure last render image exists even if PDF not requested
                if not did_pdf and ("png" in fmts_norm or "jpg" in fmts_norm):
                    import time as _time
                    tmp_pdf = str((OUTPUT_PATH / f"__tmp_{int(_time.time()*1000)}.pdf").resolve())
                    try:
                        exporter.render_scene_to_pdf(tmp_pdf, items, jig_size[0], jig_size[1], dpi=dpi, barcode_text=barcode_text, reference_text=reference_text)
                    finally:
                        try:
                            os.remove(tmp_pdf)
                        except Exception:
                            pass
                if "png" in fmts_norm and not did_pdf:
                    # Only save PNG if not already saved above
                    p_png = str(base.with_suffix(".png"))
                    exporter.save_last_render_as_png(p_png)
                    # Track this file as processed
                    self._processed_files.add(str(base))
                if "jpg" in fmts_norm:
                    p_jpg = str(base.with_suffix(".jpg"))
                    exporter.save_last_render_as_jpg(p_jpg)
                    # Track this file as processed
                    self._processed_files.add(str(base))

            # Render each export file separately
            for export_file_name in export_files_to_render:
                # Get items for this export file
                front_items_for_file = front_grouped.get(export_file_name, [])
                back_items_for_file = back_grouped.get(export_file_name, [])
                
                # Count non-slot items to determine if file has content
                front_objects = [it for it in front_items_for_file if it.get("type") != "slot"]
                back_objects = [it for it in back_items_for_file if it.get("type") != "slot"]
                
                # Skip if no objects in this file
                if not front_objects and not back_objects:
                    logger.debug(f"Skipping {export_file_name} - no objects assigned")
                    continue
                
                # Generate file names for this export file
                # Replace spaces and special chars in export file name for filename
                file_suffix = export_file_name.replace(' ', '_')
                
                # Create base paths with export file name
                base_front_file = _get_unique_base_path(
                    f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_front_{file_suffix}{f'_{pdf_order}' if pdf_order > 1 else ''}"
                )
                base_back_file = _get_unique_base_path(
                    f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_back_{file_suffix}"
                )
                
                # Render frontside for this export file
                if front_objects:
                    logger.debug(f"Rendering frontside for {export_file_name}...")
                    _render_and_save(front_items_for_file, base_front_file)
                
                # Render backside for this export file
                if back_objects:
                    logger.debug(f"Rendering backside for {export_file_name}...")
                    _render_and_save(back_items_for_file, base_back_file)

            # Return PDF info for combining (collect from all export files)
            pdf_infos = []
            if "pdf" in fmts_norm:
                for export_file_name in export_files_to_render:
                    front_objects = [it for it in front_grouped.get(export_file_name, []) if it.get("type") != "slot"]
                    back_objects = [it for it in back_grouped.get(export_file_name, []) if it.get("type") != "slot"]
                    
                    if not front_objects and not back_objects:
                        continue
                    
                    file_suffix = export_file_name.replace(' ', '_')
                    
                    if front_objects:
                        base_front_file = OUTPUT_PATH / f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_front_{file_suffix}{f'_{pdf_order}' if pdf_order > 1 else ''}"
                        pdf_path = str(base_front_file.with_suffix(".pdf"))
                        if os.path.exists(pdf_path):
                            pdf_infos.append(PDFInfo(
                                path=pdf_path,
                                width_mm=jig_size[0],
                                height_mm=jig_size[1],
                                order_range=f"{pdf_start_oder_i}-{pdf_end_oder_i}",
                                side="front",
                                pdf_order=pdf_order,
                                dpi=dpi,
                                cmyk=jig_cmyk or "0,0,0,100"
                            ))
                    
                    if back_objects:
                        base_back_file = OUTPUT_PATH / f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_back_{file_suffix}"
                        pdf_path = str(base_back_file.with_suffix(".pdf"))
                        if os.path.exists(pdf_path):
                            pdf_infos.append(PDFInfo(
                                path=pdf_path,
                                width_mm=jig_size[0],
                                height_mm=jig_size[1],
                                order_range=f"{pdf_start_oder_i}-{pdf_end_oder_i}",
                                side="back",
                                pdf_order=pdf_order,
                                dpi=dpi,
                                cmyk=jig_cmyk or "0,0,0,100"
                            ))

            return {"status": "success", "pdf_infos": pdf_infos}

        except MemoryError:
            logger.exception("Not enough memory to render PDF")
            return {"status": "error", "message": "Not enough memory to render PDF"}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "message": str(e)}

    def _process_order(
        self, 
        parent_folder: str, 
        child_folder: str,
        saved_slots: List[Tuple[Dict[str, Any], Dict[str, Any]]],
        order_info: Dict[str, Any],
        original_pattern_info: Dict[str, Any],
        pattern_info: Dict[str, Any], 
        pdf_start_oder_id: int,
        order_id: int, 
        last_order_id: int,
        pdf_combiner: PDFCombiner = None,
        front_barcode: Optional[dict] = None,
        back_barcode: Optional[dict] = None
    ) -> Dict[str, Any]:

        def _is_pattern_filled(pattern_info: Dict[str, Any], original_pattern_info: Dict[str, Any]) -> bool:
                is_need_front = False
                is_need_back = False
                for major in original_pattern_info["Frontside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_need_front = True
                for major in original_pattern_info["Backside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_need_back = True

                is_filled_front = True if is_need_front else False
                is_filled_back = True if is_need_back else False
                for major in pattern_info["Frontside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_filled_front = False
                for major in pattern_info["Backside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_filled_back = False

                return is_filled_front or is_filled_back

        def _select_slot(order_side_data: Dict[str, Any], pattern_info: Dict[str, Any], side: str) -> Dict[str, Any]:
            for major_index, major in enumerate(pattern_info[side]):
                for slot_index, slot in enumerate(major["slots"]):
                    if not slot["objects"]:
                        continue

                    slot_labels_and_types = {(object["amazon_label"], object["type"]) for object in slot["objects"]}
                    for object in order_side_data:
                        if (object["label"], object["type"] if object["type"] != "options" else "image") in slot_labels_and_types:
                            return pattern_info[side][major_index]["slots"].pop(slot_index)

            return None

        def _process_object(order_side_data: Dict[str, Any], slot_info: Dict[str, Any]) -> Dict[str, Any]:
            for object in slot_info["objects"]:
                # Check if object is static - static objects don't need Amazon data match
                is_static = bool(object.get("is_static", False))
                
                if is_static:
                    # Static objects are processed as-is without Amazon data
                    object["processed"] = True
                    object["slot_x_mm"] = slot_info["x_mm"]
                    object["slot_y_mm"] = slot_info["y_mm"]
                    object["slot_w_mm"] = slot_info["w_mm"]
                    object["slot_h_mm"] = slot_info["h_mm"]
                    continue
                
                # Non-static objects require matching with Amazon data
                order_object = [obj for obj in order_side_data if obj["label"] == object["amazon_label"]]
                if len(order_object) == 0:
                    continue
                order_object = order_object[0]

                if object["type"] == "image":
                    if object["mask_path"] and object["mask_path"] != "None":
                        mask_path = PRODUCTS_PATH / object["mask_path"]
                        template_path = PRODUCTS_PATH / object["path"]
                        result = self._apply_mask(order_object["loaded_image"], template_path, mask_path)
                        if result["status"] == "error":
                            return {"status": "error", "message": f"Failed to apply mask for order: {result['message']}"}
                        object["loaded_image"] = result["image"]
                    else:
                        object["loaded_image"] = order_object["loaded_image"]

                    filename = order_object["image_path"].split(".")[0] + ".png" if "image_path" in order_object else order_object["image_url"].split("/")[-1].split(".")[0] + ".png"
                    object["path"] = str(filename)
                    object["processed"] = True

                elif object["type"] == "text":
                    object["type"] = "rect"
                    object["label"] = order_object["text"]
                    object["label_fill"] = order_object["color"]
                    object["label_font_family"] = order_object["font_family"]
                    object["processed"] = True
                object["slot_x_mm"] = slot_info["x_mm"]
                object["slot_y_mm"] = slot_info["y_mm"]
                object["slot_w_mm"] = slot_info["w_mm"]
                object["slot_h_mm"] = slot_info["h_mm"]
                   
        result = self._prepare_order_data(parent_folder, child_folder, order_info, order_id, last_order_id)
        if result["status"] == "error":
            return {"status": "error", "message": result["message"]}
        order_data = result["data"]
        order_asin = result["asin"]

        link_to_pattern_info = pattern_info
        started_pattern_info = deepcopy(pattern_info)
        is_saved_slots_processed = False

        selected_slots = []
        asins_info = pattern_info.get("ASINs", None)
        DEBUG_MULTIPLIER = 1
        try:
            if asins_info is None:
                total_count = result["quantity"]
            else:
                order_count = [asin_pair[1] for asin_pair in asins_info if asin_pair[0] == order_asin][0]
                total_count = int(result["quantity"] * order_count)
        except Exception:
            logger.exception("Failed to get order count")
            return {"status": "error", "message": "Failed to get order count"}
        total_count *= DEBUG_MULTIPLIER
            
        pdf_count = 1
        self.log(f"[{order_id}/{last_order_id}] To process: {total_count} {'pcs' if total_count > 1 else 'pc'}")
        for i in range(total_count):
            selected_slot_front = None
            selected_slot_back = None
            if order_data.get("front", {}):
                selected_slot_front = _select_slot(order_data["front"], pattern_info, "Frontside")
                if not selected_slot_front:
                    return {"status": "error", "message": f"Not found front pattern slot for order {order_id}"}
            if order_data.get("back", {}):
                selected_slot_back = _select_slot(order_data["back"], pattern_info, "Backside")
                if not selected_slot_back:
                    return {"status": "error", "message": f"Not found back pattern slot for order {order_id}"}
            
            if selected_slot_front:
                _process_object(order_data["front"], selected_slot_front)
            if selected_slot_back:
                _process_object(order_data["back"], selected_slot_back)
            selected_slots.append((selected_slot_front, selected_slot_back))

            if _is_pattern_filled(pattern_info, original_pattern_info):
                self.log(f"[{order_id}] [{i+1}/{total_count}] The export data is filled, making files...")
                pattern_info = deepcopy(original_pattern_info)
                jig_info = pattern_info["Scene"]["jig"]
                jig_cmyk = jig_info.get("cmyk", "75,0,75,0")
                result = self._make_pdf(
                    saved_slots + selected_slots,
                    (jig_info["width_mm"], jig_info["height_mm"]),
                    pdf_start_oder_id,
                    order_id,
                    pdf_order=pdf_count,
                    dpi=getattr(self, "_export_dpi", 1200),
                    formats=getattr(self, "_export_formats", ["pdf"]),
                    barcode_text=str(order_id),
                    reference_text=order_info["orderId"],
                    jig_cmyk=jig_cmyk,
                    front_barcode=front_barcode,
                    back_barcode=back_barcode
                )
                if result["status"] == "error":
                    link_to_pattern_info.clear()
                    link_to_pattern_info.update(started_pattern_info)
                    return {"status": "error", "message": "Failed to make pdf: " + result["message"]}
                self.log(f"[{order_id}] [{i+1}/{total_count}] Files made successfully", SUCCESS_COLOR)
                
                # Add PDFs to combiner
                if pdf_combiner and "pdf_infos" in result and (front_barcode or back_barcode):
                    for pdf_info in result["pdf_infos"]:
                        pdf_combiner.add_pdf(pdf_info)
                        
                selected_slots.clear()
                saved_slots.clear()
                is_saved_slots_processed = True
                pdf_count += 1
                pdf_start_oder_id = order_id
            
        if link_to_pattern_info != pattern_info:
            link_to_pattern_info.clear()
            link_to_pattern_info.update(pattern_info)
        return {"status": "success", "selected_slots": selected_slots, "pdf_start_order_id": pdf_start_oder_id, "is_saved_slots_processed": is_saved_slots_processed}

    def _process_orders(self):
        try:
            def _is_pattern_filled(pattern_info: Dict[str, Any], original_pattern_info: Dict[str, Any]) -> bool:
                is_need_front = False
                is_need_back = False
                for major in original_pattern_info["Frontside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_need_front = True
                for major in original_pattern_info["Backside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_need_back = True

                is_filled_front = True if is_need_front else False
                is_filled_back = True if is_need_back else False
                for major in pattern_info["Frontside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_filled_front = False
                for major in pattern_info["Backside"]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            is_filled_back = False

                return is_filled_front or is_filled_back

            if getattr(self, "_cancel_requested", False):
                self.log("Processing cancelled by user.", WARNING_COLOR)
                return

            # Clear processed files set at the start of each processing run
            # This allows files to be recreated if they were deleted from disk
            self._processed_files.clear()

            self.log(f"Trying to open the {state.saved_product} pattern file...")
            try:
                with open(PRODUCTS_PATH / f"{state.saved_product}.json", "r", encoding="utf-8") as f:
                    pattern_info = json.load(f)
                    for side in ["Frontside", "Backside"]:
                        for major in pattern_info[side]:
                            for slot in major["slots"]:
                                for obj_ in slot["objects"]:
                                    if obj_["type"] == "image":
                                        if obj_["mask_path"] in [None, ".", "None", "none"]:
                                            obj_["mask_path"] = ""
                                        else:
                                            try:
                                                Path(obj_["mask_path"])
                                            except Exception: 
                                                obj_["mask_path"] = ""

                                    elif obj_["type"] == "text":
                                        obj_["label"] = ""

            except Exception as e:
                self.log(f"Failed to open the {state.saved_product} pattern file: {e}", ERROR_COLOR)
                self.start_btn.configure(state="normal")
                self.progress["value"] = 100
                return
            self.log(f"{state.saved_product} pattern file opened successfully", SUCCESS_COLOR)

            # Initialize PDF combiner
            pdf_combiner = PDFCombiner(OUTPUT_PATH)
            self.log("PDF combiner initialized for combining rendered PDFs")

            total_orders_items: Dict[str, Tuple[Dict[str, Any], str, str]] = {}
            if state.order_from.find("-") != -1 and state.order_from.count("-") == 1:
                self.log(f"Starting processing for range [{state.order_from}]")
                orders_info = get_orders_info([str(i) for i in range(int(state.order_from.split("-")[0].strip()), int(state.order_from.split("-")[1].strip()) + 1)], self.log)
                total_orders_items = orders_info["orders"]
            elif state.order_from.find(",") != -1 or state.order_from.strip().isdigit():
                orders_ = [order_.strip() for order_ in state.order_from.split(",")]
                self.log(f"Starting processing for orders {orders_}")
                orders_info = get_orders_info(orders_, self.log)
                total_orders_items = orders_info["orders"]
            else:
                messagebox.showerror("Incorrect format", "Order input should be like 0-10 or 3,7,9 or just 3")
                 
            orders_to_process: Dict[str, Tuple[Dict[str, Any], str, str]] = {}
            asins = [asin_ for asin_, _ in state.asins]
            for order_file, order_info in total_orders_items.items():
                if "asin" not in order_info[0]:
                    self.log(f"Order {order_file} has no asin", ERROR_COLOR)
                    continue
                
                if order_info[0]["asin"] in asins:
                    orders_to_process[order_file] = order_info

            if not orders_to_process:
                self.log(f"No orders found for ASINs: {asins}", ERROR_COLOR)
                return
            else:
                self.log(f"Found {len(orders_to_process)} orders for ASINs {asins}", SUCCESS_COLOR)

            total_orders = len(orders_to_process) 
            progress_step = 100 / len(orders_to_process)
            orders_to_process = dict(sorted(orders_to_process.items(), key=lambda x: int(x[0].split("_")[0])))
            last_order_i = max(int(order_path.split("_")[0]) for order_path in orders_to_process)

            front_barcode = None
            back_barcode = None
            if "FrontsideBarcode" in pattern_info:
                front_barcode = pattern_info["FrontsideBarcode"]
            if "BacksideBarcode" in pattern_info:
                back_barcode = pattern_info["BacksideBarcode"]

            failed_orders = []
            current_processing_orders = []
            pattern_data = deepcopy(pattern_info)
            pdf_data: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
            pdf_start_oder_i = None
            is_sucess = False
            for i, (order_file, order_info_) in enumerate(orders_to_process.items()):
                order_id = int(order_file.split("_")[0])
                order_info, parent_folder, child_folder = order_info_
                if pdf_start_oder_i is None:
                    pdf_start_oder_i = order_id

                if getattr(self, "_cancel_requested", False):
                    self.log("Processing cancelled by user.", WARNING_COLOR)
                    logger.debug("Processing cancelled by user.")
                    break

                self.log(f"Processing of Order {order_id}/{last_order_i} has been initiated")
                logger.debug(f"Processing of Order {order_id}/{last_order_i} has been initiated")
                order_result = self._process_order(
                    parent_folder,
                    child_folder,
                    pdf_data,
                    order_info,
                    deepcopy(pattern_info),
                    pattern_data,
                    pdf_start_oder_i,
                    order_id,
                    last_order_i,
                    pdf_combiner,
                    front_barcode=front_barcode,
                    back_barcode=back_barcode
                )
                if order_result["status"] == "error":
                    if order_result.get("message") == "Cancelled":
                        self.log("Processing cancelled by user.", WARNING_COLOR)
                        break
                    failed_orders.append(order_file)
                    self.log(f"[{order_id}/{last_order_i}] Order processing failed: " + order_result["message"], ERROR_COLOR)
                else:
                    self.log(f"[{order_id}/{last_order_i}] Order processed successfully", SUCCESS_COLOR)
                    if order_result["is_saved_slots_processed"]:
                        pdf_data.clear()
                    if order_result["selected_slots"] == (None, None):
                        self.log(f"[{order_id}/{last_order_i}] Order doesn't require customization", WARNING_COLOR)
                    else:
                        if len(order_result["selected_slots"]) > 0:
                            pdf_data.extend(order_result["selected_slots"])
                        current_processing_orders.append(order_file)
                    pdf_start_oder_i = order_result["pdf_start_order_id"]

                if getattr(self, "_cancel_requested", False):
                    self.log("Processing cancelled by user.", WARNING_COLOR)
                    break

                if _is_pattern_filled(pattern_data, pattern_info) or (i == total_orders - 1 and pdf_data):
                    self.log(f"[{pdf_start_oder_i}-{order_id}] The export data is filled, making files...")
                    pattern_data = deepcopy(pattern_info)
                    jig_info = pattern_info["Scene"]["jig"]
                    jig_cmyk = jig_info.get("cmyk", "75,0,75,0")
                    result = self._make_pdf(
                        pdf_data,
                        (jig_info["width_mm"], jig_info["height_mm"]),
                        pdf_start_oder_i,
                        order_id,
                        dpi=getattr(self, "_export_dpi", 1200),
                        formats=getattr(self, "_export_formats", ["pdf"]),
                        barcode_text=str(order_id),
                        reference_text=order_info["orderId"],
                        jig_cmyk=jig_cmyk,
                        front_barcode=front_barcode,
                        back_barcode=back_barcode
                    )
                    if result["status"] == "error":
                        self.log(f"[{pdf_start_oder_i}-{order_id}] Failed to export files: " + result["message"], ERROR_COLOR)
                        failed_orders.extend([order_path for order_path in current_processing_orders])
                    else:
                        self.log(f"[{pdf_start_oder_i}-{order_id}] Files made successfully", SUCCESS_COLOR)
                        is_sucess = True
                        
                        # Add PDFs to combiner
                        if "pdf_infos" in result and (front_barcode or back_barcode):
                            for pdf_info in result["pdf_infos"]:
                                pdf_combiner.add_pdf(pdf_info)
                                
                    pdf_data.clear()
                    pdf_start_oder_i = None

                self.progress["value"] += progress_step

            # Finalize and combine all pending PDFs
            # True True False 2
            if is_sucess:
                if (front_barcode or back_barcode) and pdf_combiner.pending_pdfs:
                    self.log("Combining rendered PDFs into larger sheets...")
                    try:
                        combined_paths = pdf_combiner.finalize()
                        if combined_paths:
                            self.log(f"Created {len(combined_paths)} combined PDF(s):", SUCCESS_COLOR)
                            for path in combined_paths:
                                self.log(f"  - {os.path.basename(path)}", SUCCESS_COLOR)
                        else:
                            self.log("No PDFs were combined (possibly all fit in single sheets already)")
                    except Exception as e:
                        self.log(f"Failed to combine PDFs: {e}", ERROR_COLOR)
                        logger.exception("PDF combining failed")
                    
                self.log(f"Processing completed! You can find files in outputs/ folder", SUCCESS_COLOR)
            # if failed_orders:
            #     self.log(f"Failed orders: {failed_orders}", ERROR_COLOR)

        finally:
            # Re-enable Start button and reset processing flag when done
            try:
                self.start_btn.configure(state="normal")
                self.progress["value"] = 100
                # Restore visuals and interactions
                self._clear_start_button_color_override()
                self._restore_start_button_interactions()
                # Restore original cursor exactly as before processing
                self.start_btn.configure(cursor=getattr(self, "_start_btn_default_cursor", ""))
            except Exception:
                pass
            self._is_processing = False
            self._cancel_requested = False

    # ------------------------- Helpers: Button UI -------------------------
    def _set_start_button_color(self, color: str) -> None:
        try:
            c = self.start_btn
            c.update_idletasks()
            w = int(c.winfo_width())
            h = int(c.winfo_height())
            # Remove previous override if any
            try:
                c.delete("btn_disabled_overlay")
            except Exception:
                pass
            c.create_rectangle(0, 0, w, h, fill=color, outline="", tags=("btn_disabled_overlay",))
            # Keep text above
            try:
                c.tag_raise("btntxt")
            except Exception:
                pass
        except Exception:
            pass

    def _clear_start_button_color_override(self) -> None:
        try:
            self.start_btn.delete("btn_disabled_overlay")
            self.start_btn.update_idletasks()
        except Exception:
            pass

    def _disable_start_button_interactions(self) -> None:
        """Intercept common hover/press events to suppress animations during processing."""
        try:
            self._start_btn_blocked_events = (
                "<Enter>", "<Leave>", "<ButtonPress-1>", "<ButtonRelease-1>", "<Motion>"
            )
            # Save previous bindings to restore later
            self._start_btn_saved_bindings = {}
            for seq in self._start_btn_blocked_events:
                prev_script = self.start_btn.bind(seq)
                self._start_btn_saved_bindings[seq] = prev_script
                # Returning "break" prevents further processing of the event
                self.start_btn.bind(seq, lambda _e=None: "break")
        except Exception:
            pass

    def _restore_start_button_interactions(self) -> None:
        try:
            for seq in getattr(self, "_start_btn_blocked_events", ()):  # type: ignore[attr-defined]
                prev = getattr(self, "_start_btn_saved_bindings", {}).get(seq)
                if prev:
                    self.start_btn.bind(seq, prev)
                else:
                    self.start_btn.unbind(seq)
            # Clear saved bindings
            self._start_btn_saved_bindings = {}
        except Exception:
            pass

    def _validate_date_mask(self, proposed: str) -> bool:
        """Allow only masks like dd-mm-YYYY while typing (digits and hyphens).
        This validation is permissive during typing, enforcing segment lengths.
        """
        if proposed == "":
            return True
        if len(proposed) > 10:
            return False
        for ch in proposed:
            if not (ch.isdigit() or ch == "-"):
                return False
        parts = proposed.split("-")
        if len(parts) > 3:
            return False
        if len(parts) >= 1 and len(parts[0]) > 2:
            return False
        if len(parts) >= 2 and len(parts[1]) > 2:
            return False
        if len(parts) == 3 and len(parts[2]) > 4:
            return False
        return True

    def _start(self):
        # Prevent multiple concurrent starts via button or hotkey
        if getattr(self, "_is_processing", False):
            return
        # Clear any previous cancellation
        self._cancel_requested = False
        from_s = self.from_var.get().strip()

        # 1) Order number does not exist / invalid
        if not from_s:
            messagebox.showerror("Error", "Order number does not exist.")
            return

        state.order_from = from_s

        # 2) Dropbox date range validation and save
        df_s = self.drop_from_var.get().strip()
        dt_s = self.drop_to_var.get().strip()
        if not df_s or not dt_s:
            messagebox.showerror("Error", "Please enter date range (From and To) in format dd-mm-YYYY.")
            return
        try:
            df = datetime.strptime("-".join([f"0{el}" if len(el) == 1 else el for el in df_s.split('-')]), "%d-%m-%Y")
            dt = datetime.strptime("-".join([f"0{el}" if len(el) == 1 else el for el in dt_s.split('-')]), "%d-%m-%Y")
        except Exception:
            messagebox.showerror("Error", "Date format must be dd-mm-YYYY.")
            return
        if df > dt:
            messagebox.showerror("Error", "'From' date must be before or equal to 'To' date.")
            return
        state.dropbox_from = df
        state.dropbox_to = dt

        # 3) Formats + DPI
        fmt_s = (self.format_var.get() if hasattr(self, "format_var") else "pdf").strip()
        fmts = [f.strip().lower() for f in fmt_s.split(",") if f.strip()]
        formats_norm: List[str] = []
        seen = set()
        for f in fmts:
            if f == "jpeg":
                f = "jpg"
            if f in ("pdf", "png", "jpg") and f not in seen:
                seen.add(f)
                formats_norm.append(f)
        if not formats_norm:
            messagebox.showerror("Error", "Please enter at least one valid format: pdf, png, jpg.")
            return
        dpi_s = (self.dpi_var.get() if hasattr(self, "dpi_var") else "1200").strip()
        try:
            dpi_v = int(dpi_s or "1200")
            if dpi_v <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "DPI must be a positive integer (e.g. 1200).")
            return
        self._export_formats = formats_norm
        self._export_dpi = dpi_v

        self.progress["value"] = 0
        # Visually disable start button and block hover/press animations
        try:
            self._set_start_button_color("#555555")
            self._disable_start_button_interactions()
            self.start_btn.configure(cursor="arrow")
        except Exception:
            pass
        self.start_btn.configure(state="disabled")
        self._is_processing = True

        threading.Thread(target=self._process_orders, daemon=True).start()
   
    def _on_cancel(self):
        """If processing, request cancellation; otherwise go back."""
        state.is_cancelled = True
        if getattr(self, "_is_processing", False):
            if not getattr(self, "_cancel_requested", False):
                self._cancel_requested = True
                try:
                    self.log("Cancellation requested...", WARNING_COLOR)
                except Exception:
                    pass
        # Not processing: behave as a normal back button
        try:
            self.app.go_back()
        except Exception:
            pass
