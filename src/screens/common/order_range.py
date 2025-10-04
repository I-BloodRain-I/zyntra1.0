import logging
import os
from tempfile import gettempdir
import threading
import time
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime
import json
from copy import deepcopy

from pprint import pformat
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
from typing import Any, Dict, List, Literal
from PIL import ImageDraw, ImageChops, ImageFilter, ImageOps
from PIL import Image as _PILImage
import numpy as np
import math

from src.core.state import state
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
from src.canvas import PdfExporter, ImageManager


DEFAULT_COLOR = "#000000"
SUCCESS_COLOR = "#228B22"
WARNING_COLOR = "#ffff00"
ERROR_COLOR = "#CE0000"

logger = logging.getLogger(__name__)


class OrderRangeScreen(Screen):
    def __init__(self, master, app):
        super().__init__(master, app)

        # Top line identical to LauncherSelectProduct
        self.brand_bar(self)

        self.images = ImageManager(self)
        self._rotated_bounds_px = self.images.rotated_bounds_px
        self._rotated_bounds_mm = self.images.rotated_bounds_mm

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

        tk.Label(row_inputs, text="From:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=lbl_font).pack(side="left", padx=(0, 0))
        self.from_var = tk.StringVar(value=state.order_from)
        tk.Entry(row_inputs, textvariable=self.from_var, width=8, justify="center",
                 font=ent_font, bg="#ffffff", relief="flat").pack(side="left")

        tk.Label(row_inputs, text="To:", bg=COLOR_BG_SCREEN, fg=COLOR_TEXT, font=lbl_font).pack(side="left", padx=(scale_px(50), 0))
        self.to_var = tk.StringVar(value=state.order_to)
        tk.Entry(row_inputs, textvariable=self.to_var, width=8, justify="center",
                 font=ent_font, bg="#ffffff", relief="flat").pack(side="left")

        # ---------------------------------------------------------------------
        # Progress bar (between ID selection and logger)
        # ---------------------------------------------------------------------
        pb_wrap = tk.Frame(content, bg=COLOR_BG_SCREEN)
        pb_wrap.pack(pady=(scale_px(14), 0))
        self.progress = ttk.Progressbar(pb_wrap, orient="horizontal", length=500, mode="determinate", maximum=100)
        self.progress.pack(ipady=scale_px(12), pady=(5, 36))
        self.progress["value"] = 100
        # ---------------------------------------------------------------------

        # Scrollable logger area inside a rounded "pill" container
        pill_info = PillLabelInfo(
            width=900,
            height=600,
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

        # Bottom-left Go Back button (styled like font_info)
        back_btn = create_button(
            ButtonInfo(
                parent=self,
                text_info=TextInfo(
                    text="Go Back",
                    color=COLOR_TEXT,
                    font_size=22,
                ),
                button_color=COLOR_BG_DARK,
                hover_color="#3f3f3f",
                active_color=COLOR_BG_DARK,
                padding_x=20,
                padding_y=12,
                command=self.app.go_back,
            )
        )
        back_btn.place(relx=0.005, rely=0.99, anchor="sw")

        # Hotkeys: Enter → Start, Escape → Back (accept optional event)
        self.app.bind("<Return>", lambda _e=None: self._start())
        self.app.bind("<Escape>", lambda _e=None: self.app.go_back())

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

        finally:
            self.log_text.configure(state="disabled")

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
                    if not area["optionImage"] or area["optionValue"].startswith("NEIN"):
                        continue
                    if str(order_info).count(area["optionValue"]) > 3:
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

        return objects

    def _download_image(self, image_url: str) -> Dict[str, Union[str, Image.Image]]:
        retries = 3
        image_name = image_url.split("/")[-1]
        while retries > 0:
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

    def _load_image(self, image_path: str) -> Dict[str, Union[str, Image.Image]]:
        path = Path(image_path)
        if not path.exists():
            return {"status": "error", "message": f"Image {image_path} does not exist"}
        if not path.is_file():
            return {"status": "error", "message": f"Path {image_path} is not a file"}
        return {"status": "success", "image": Image.open(path)}

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
        try:
            lanczos = _PILImage.Resampling.LANCZOS
            bicubic = _PILImage.Resampling.BICUBIC
            bilinear = _PILImage.Resampling.BILINEAR
            nearest = _PILImage.Resampling.NEAREST
            affine_method = _PILImage.Transform.AFFINE
        except AttributeError:
            lanczos = _PILImage.LANCZOS
            bicubic = _PILImage.BICUBIC
            bilinear = _PILImage.BILINEAR
            nearest = _PILImage.NEAREST
            affine_method = _PILImage.AFFINE

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
        mask_path: Path,
        alpha_threshold: int = 10,
        fit_mode: Literal["cover", "contain", "fill"] = "fill"
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

    def _prepare_order_data(self, path_to_json: str, order_i: int, total_orders: int) -> Dict[str, Any]:
        path = Path(path_to_json)
        
        if not path.exists():
            return {"status": "error", "message": f"Path {path_to_json} does not exist"}
        
        if not path.is_file():
            return {"status": "error", "message": f"Path {path_to_json} is not a file"}
        
        with open(path, "r", encoding="utf-8") as f:
            order_info = json.load(f)
        
        customization_info = self._collect_customization_info(order_info)
        total_download_image_count = 0
        total_loaded_image_count = 0
        for side in customization_info:
            for object in customization_info[side]:
                if object["type"] == "options":
                    total_download_image_count += 1
                if object["type"] == "image":
                    total_loaded_image_count += 1
        self.log(f"[{order_i+1}/{total_orders}] Total images to download from Amazon: {total_download_image_count}; from Dropbox: {total_loaded_image_count}")

        downloaded_image_count = 0
        loaded_image_count = 0
        for side in customization_info:
            for object in customization_info[side]:
                
                if object["type"] == "image":
                    image_info = self._load_image(object["image_path"])
                    if image_info["status"] == "error":
                        return {"status": "error", "message": image_info["message"]}
                    else:
                        loaded_image_count += 1
                        self.log(f"[{order_i+1}/{total_orders}] Image {loaded_image_count}/{total_loaded_image_count} downloaded from Dropbox")
                        image_info["image"].save("order_object_loaded_image_before.png")
                        image = self._transform_amazon_image(
                            im=image_info["image"], 
                            scale=object["scale"]["scaleX"], 
                            angle_deg=object["rotation"], 
                            place_xy=[object["position"]["x"], object["position"]["y"]], 
                            mask_rect=[object["mask_position"]["x"], object["mask_position"]["y"], object["mask_size"]["width"], object["mask_size"]["height"]]
                        )
                        object["loaded_image"] = image

                elif object["type"] == "options":
                    image_info = self._download_image(object["image_url"])
                    if image_info["status"] == "error":
                        return {"status": "error", "message": image_info["message"]}
                    else:
                        downloaded_image_count += 1
                        self.log(f"[{order_i+1}/{total_orders}] Image {downloaded_image_count}/{total_download_image_count} downloaded from Amazon")
                        image = self._transform_amazon_image(
                            im=image_info["image"], 
                            scale=object["scale"]["scaleX"], 
                            angle_deg=object["rotation"], 
                            place_xy=[object["position"]["x"], object["position"]["y"]], 
                            mask_rect=[object["mask_position"]["x"], object["mask_position"]["y"], object["mask_size"]["width"], object["mask_size"]["height"]]
                        )
                        object["loaded_image"] = image

        return {"status": "success", "data": customization_info}

    def _make_pdf(
        self, 
        data: List[Tuple[Dict[str, Any], Dict[str, Any]]], 
        jig_size: Tuple[float, float], 
        pdf_start_oder_i: int, 
        pdf_end_oder_i: int
    ) -> Dict[str, str]:
        try:       
            exporter = PdfExporter(self)
            p_front = str((OUTPUT_PATH / f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_front.pdf").resolve())
            p_back  = str((OUTPUT_PATH / f"{state.saved_product}_{pdf_start_oder_i}-{pdf_end_oder_i}_back.pdf").resolve())

            front_items = []
            back_items = []
            for front, back in data:
                front_items.extend(front["objects"])
                if back:
                    back_items.extend(back["objects"])

            logger.debug("Rendering front PDF...")
            exporter.render_scene_to_pdf(p_front, front_items, jig_size[0], jig_size[1], dpi=1200)
            if back_items and any(item is not None for item in back_items):
                logger.debug("Rendering back PDF...")
                exporter.render_scene_to_pdf(p_back, back_items, jig_size[0], jig_size[1], dpi=1200)

            return {"status": "success"}

        except MemoryError:
            logger.exception("Not enough memory to render PDF")
            return {"status": "error", "message": "Not enough memory to render PDF"}
        except Exception as e:
            logger.exception(e)
            return {"status": "error", "message": str(e)}

    def _process_order(self, path_to_json: str, pattern_info: Dict[str, Any], order_i: int, total_orders: int) -> Tuple[Dict[str, str], bool]:

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
                order_object = [obj for obj in order_side_data if obj["label"] == object["amazon_label"]]
                if len(order_object) == 0:
                    continue
                order_object = order_object[0]

                if object["type"] == "image":
                    if object["mask_path"] and object["mask_path"] != "None":
                        mask_path = PRODUCTS_PATH / object["mask_path"]
                        template_path = PRODUCTS_PATH / object["path"]
                        order_object["loaded_image"].save("order_object_loaded_image.png")
                        result = self._apply_mask(order_object["loaded_image"], template_path, mask_path)
                        if result["status"] == "error":
                            return {"status": "error", "message": f"Failed to apply mask for order: {result['message']}"}
                        result["image"].show()
                        object["loaded_image"] = result["image"]
                    else:
                        object["loaded_image"] = order_object["loaded_image"]

                    # order_object["loaded_image"].save(path)
                    filename = order_object["image_path"].split(".")[0] + ".png" if "image_path" in order_object else order_object["image_url"].split("/")[-1].split(".")[0] + ".png"
                    object["path"] = str(filename)
                    object["processed"] = True

                elif object["type"] == "text":
                    object["type"] = "rect"
                    object["label"] = order_object["text"]
                    object["label_fill"] = order_object["color"]
                    object["label_font_family"] = order_object["font_family"]
                    object["processed"] = True
                   
        result = self._prepare_order_data(path_to_json, order_i, total_orders)
        if result["status"] == "error":
            return {"status": "error", "message": result["message"]}
        order_data = result["data"]

        selected_slot_front = None
        selected_slot_back = None
        if order_data.get("front", {}):
            selected_slot_front = _select_slot(order_data["front"], pattern_info, "Frontside")
            if not selected_slot_front:
                return {"status": "error", "message": f"Not found front pattern slot for order {path_to_json}"}
        if order_data.get("back", {}):
            selected_slot_back = _select_slot(order_data["back"], pattern_info, "Backside")
            if not selected_slot_back:
                return {"status": "error", "message": f"Not found back pattern slot for order {path_to_json}"}
        
        if selected_slot_front:
            _process_object(order_data["front"], selected_slot_front)
        if selected_slot_back:
            _process_object(order_data["back"], selected_slot_back)
            
        return {"status": "success", "front": selected_slot_front, "back": selected_slot_back}

    def _process_orders(self):
        
        def _is_pattern_filled(pattern_info: Dict[str, Any]) -> bool:
            for side in ["Frontside", "Backside"]:
                for major in pattern_info[side]:
                    for slot in major["slots"]:
                        if slot["objects"]:
                            return False
            return True

        self.log(f"Trying to open the {state.saved_product} pattern file...")
        try:
            with open(PRODUCTS_PATH / f"{state.saved_product}.json", "r", encoding="utf-8") as f:
                pattern_info = json.load(f)
        except Exception as e:
            self.log(f"Failed to open the {state.saved_product} pattern file: {e}", ERROR_COLOR)
            self.start_btn.configure(state="normal")
            self.progress["value"] = 100
            return
        self.log(f"{state.saved_product} pattern file opened successfully", SUCCESS_COLOR)

        self.log(f"Starting processing for range [{state.order_from}..{state.order_to}]")
        # order_paths = [f"data/15-09-2025 LIGHTER BULK/JSON/161804_Image1.json" for _ in range(6)]
        order_paths = [f"data/15-09-2025 LIGHTER BULK/JSON/161823_Image1.json" for _ in range(1)]
        total_orders = len(order_paths)
        progress_step = 100 / len(order_paths)

        failed_orders = []
        pattern_data = deepcopy(pattern_info)
        pdf_data: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        pdf_start_oder_i = 1
        for i, order_path in enumerate(order_paths):
            self.log(f"Processing of Order {i+1}/{total_orders} has been initiated")
            order_result = self._process_order(order_path, pattern_data, i, total_orders)
            if order_result["status"] == "error":
                failed_orders.append(order_path)
                self.log(f"[{i+1}/{total_orders}] Order processing failed: " + order_result["message"], ERROR_COLOR)
            else:
                self.log(f"[{i+1}/{total_orders}] Order processed successfully", SUCCESS_COLOR)
                pdf_data.append((order_result["front"], order_result["back"]))

            if _is_pattern_filled(pattern_data) or (i == total_orders - 1 and pdf_data):
                self.log(f"[{pdf_start_oder_i}-{i+1}] The pdf data is filled, making pdf...")
                pattern_data = deepcopy(pattern_info)
                jig_info = pattern_info["Scene"]["jig"]
                result = self._make_pdf(pdf_data, (jig_info["width_mm"], jig_info["height_mm"]), pdf_start_oder_i, i+1)
                if result["status"] == "error":
                    self.log(f"[{pdf_start_oder_i}-{i+1}] Failed to make pdf: " + result["message"], ERROR_COLOR)
                    failed_orders.extend(order_paths[pdf_start_oder_i-1:i+1])
                else:
                    self.log(f"[{pdf_start_oder_i}-{i+1}] PDFs made successfully", SUCCESS_COLOR)
                pdf_data.clear()
                pdf_start_oder_i = i + 2

            self.progress["value"] += progress_step

        # make pdf

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

        # Подготовка прогресса и запуск анимации
        self.progress["value"] = 0
        self.start_btn.configure(state="disabled")

        threading.Thread(target=self._process_orders).start()
        # result = self._process_order("data/15-09-2025 LIGHTER BULK/JSON/161804_Image1.json")
        # if result["status"] == "error":
        #     self.log(result["message"], ERROR_COLOR)
        # else:
        #     self.log("Order processed successfully", SUCCESS_COLOR)

