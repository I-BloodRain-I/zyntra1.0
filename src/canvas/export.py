from __future__ import annotations

import io
import os
import logging
import numpy as np
from typing import List, Tuple, Optional
from io import BytesIO
import functools
import urllib.request

import math
import arabic_reshaper
from bidi.algorithm import get_display
import cairo
import emoji
from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji

from src.core import MM_TO_PX
from src.core.state import FONTS_PATH, PRODUCTS_PATH, state
from src.utils import svg_to_png

TWEMOJI_PNG_DIR: Optional[str] = None
TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"

logger = logging.getLogger(__name__)


class PdfExporter:
    """Export a scene into a single-page PDF at requested DPI."""

    def __init__(self, screen) -> None:
        self.s = screen

    def render_scene_to_pdf(
        self, 
        path: str, 
        items: list[dict], 
        jig_w_mm: float, 
        jig_h_mm: float, 
        only_jig: bool = False, 
        dpi: int = 300,
        barcode_text = "text1",
        reference_text = "text2"

    ) -> None:
        """Render a scene (slots + items) into a single-page PDF (jig == page)."""
        try:
            from PIL import Image as _PIL_Image  # type: ignore
            from PIL import ImageDraw as _PIL_Draw  # type: ignore
            from PIL import ImageFont as _PIL_Font  # type: ignore
        except Exception as e:
            raise RuntimeError("Pillow (PIL) is required to export PDF.") from e

        if not hasattr(_PIL_Font.FreeTypeFont, "getsize"):
            def _getsize(self, text, *args, **kwargs):
                # getbbox возвращает (left, top, right, bottom)
                bbox = self.getbbox(text, *args, **kwargs)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                return (w, h)
            _PIL_Font.FreeTypeFont.getsize = _getsize

        # базовые единицы
        px_per_mm = float(dpi) / 25.4
        page_w_px = max(1, int(round(jig_w_mm * px_per_mm)))
        page_h_px = max(1, int(round(jig_h_mm * px_per_mm)))

        # Рабочий холст в RGBA (прозрачный фон)
        img = _PIL_Image.new("RGBA", (page_w_px, page_h_px), (255, 255, 255, 0))
        draw = _PIL_Draw.Draw(img, "RGBA")
        font_small = _PIL_Font.load_default()

        # --- Font helpers: map family -> file and build font at pixel size ---
        def _load_fonts_map() -> dict:
            """Load the fonts mapping from FONTS_PATH/fonts.json.

            Returns a dict mapping display family names to file stems. If the
            mapping file is missing or invalid, a default mapping is returned.
            """
            try:
                mp_path = FONTS_PATH / "fonts.json"
                if mp_path.exists():
                    import json as _json
                    with open(mp_path, "r", encoding="utf-8") as f:
                        data = _json.load(f)
                        if isinstance(data, dict):
                            return data
            except Exception:
                raise
            return {"Myriad Pro": "MyriadPro-Regular"}

        _fonts_map = _load_fonts_map()

        def _font_path_for_family(family: str) -> str | None:
            """Resolve a filesystem path for a font family.

            Checks the loaded fonts map for a file stem and attempts to find
            a .ttf or .otf file under FONTS_PATH. Returns the path or None if
            not found.
            """
            try:
                file_stem = str(_fonts_map.get(family, "MyriadPro-Regular"))
            except Exception:
                file_stem = "MyriadPro-Regular"
            try:
                ttf = FONTS_PATH / f"{file_stem}.ttf"
                if ttf.exists():
                    return str(ttf)
                otf = FONTS_PATH / f"{file_stem}.otf"
                if otf.exists():
                    return str(otf)
            except Exception:
                raise
            # final fallback to bundled name if present
            try:
                fp = FONTS_PATH / "MyriadPro-Regular.ttf"
                if fp.exists():
                    return str(fp)
            except Exception:
                raise
            return None

        def _truetype_for_family(family: str, size_px: int):
            """Return a Pillow FreeType font instance for the family at size_px.

            If the requested family cannot be resolved or loaded, attempts a
            series of fallbacks and finally returns PIL's default font.
            """
            try:
                path = _font_path_for_family(family)
                if path:
                    return _PIL_Font.truetype(path, max(1, int(size_px)))
            except Exception:
                raise
            # fallback
            try:
                fp = FONTS_PATH / "MyriadPro-Regular.ttf"
                if fp.exists():
                    return _PIL_Font.truetype(str(fp), max(1, int(size_px)))
            except Exception:
                raise
            return _PIL_Font.load_default()

        def _parse_hex_rgba(hex_str: str, default=(255, 255, 255, 255)):
            """Parse a CSS-style hex color (#RRGGBB) into an RGBA tuple.

            Returns `default` if parsing fails.
            """
            try:
                s = str(hex_str or "").strip()
                if s.startswith("#") and len(s) == 7:
                    r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
                    return (r, g, b, 255)
            except Exception:
                raise
            return default

        def _darken_white_color(image: Image.Image, reduce_pct: int = 2, cap_white: bool = True, cap_value: int = 250) -> Image.Image:
            """Reduce brightness of pure-white pixels on opaque areas.

            This helps avoid fully blown-out whites when compositing artwork on
            printable substrates. Returns a new Image in RGBA mode.
            """
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            arr = np.array(image, dtype=np.uint8)
            rgb = arr[:, :, :3]
            alpha = arr[:, :, 3]

            opaque_mask = alpha > 0
            rgb[opaque_mask] = (rgb[opaque_mask].astype(np.float32) * (1 - reduce_pct / 100.0)).astype(np.uint8)

            if cap_white:

                mask_white = (
                    (rgb[:, :, 0] >= 255) &
                    (rgb[:, :, 1] >= 255) &
                    (rgb[:, :, 2] >= 255) &
                    opaque_mask
                )
                rgb[mask_white] = cap_value

            result = np.dstack((rgb, alpha))
            return Image.fromarray(result, mode="RGBA")

        def _draw_rotated_text_center(
            text: str,
            center_x: int,
            center_y: int,
            font,
            fill: tuple[int, int, int, int],
            angle_deg: float,
            mirror: bool = False,
        ) -> None:
            """Render (with Pilmoji) centered text at (center_x, center_y).

            The function applies Arabic shaping and BiDi display rules, renders
            text (including emojis) to a temporary RGBA image, rotates that
            image by angle_deg, then composites it centered onto the main
            export canvas (`img`). This preserves high-quality rotated text
            with transparent background.
            """
            # bidi/arabic shaping — как и было
            reshaped_text = arabic_reshaper.reshape(text)
            text = get_display(reshaped_text)

            # Базовый bbox только для оценки масштаба
            bb = draw.textbbox((0, 0), text, font=font)
            tw = max(1, bb[2] - bb[0])
            th = max(1, bb[3] - bb[1])

            pad = max(8, int(getattr(font, "size", 16)) * 2)

            temp_img = _PIL_Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
            draw_text_with_emojis(temp_img, (pad - bb[0], pad - bb[1]), text, font, fill=fill, emoji_scale=1.0)

            # Apply mirror (flip horizontally) if mirror flag is set BEFORE rotation
            if mirror:
                try:
                    temp_img = temp_img.transpose(_PIL_Image.FLIP_LEFT_RIGHT)
                except Exception:
                    logger.exception("Failed to apply mirror flip for text render")

            # Поворот
            if abs(float(angle_deg)) > 1e-6:
                try:
                    temp_img = temp_img.rotate(float(angle_deg), expand=True, resample=_PIL_Image.BICUBIC, fillcolor=(0, 0, 0, 0))
                except Exception:
                    temp_img = temp_img.rotate(float(angle_deg), expand=True)

            a = temp_img.split()[-1]
            bbox = a.getbbox()
            if bbox:
                temp_img = temp_img.crop(bbox)

            left = int(round(center_x - temp_img.width / 2.0))
            top  = int(round(center_y - temp_img.height / 2.0))

            try:
                img.alpha_composite(temp_img, (left, top))
            except Exception:
                img.paste(temp_img, (left, top), temp_img.split()[-1])


        def _split_text_emoji(s: str) -> List[Tuple[str, str]]:
            """Split text into ('text', chunk) / ('emoji', chunk) pairs using emoji>=2.0 API."""
            result, last = [], 0
            for e in emoji.emoji_list(s):
                st, en = e["match_start"], e["match_end"]
                if st > last:
                    result.append(("text", s[last:st]))
                result.append(("emoji", s[st:en]))
                last = en
            if last < len(s):
                result.append(("text", s[last:]))
            return result


        def _codepoints(s: str) -> str:
            """Return lower-hex Unicode codepoints joined by dashes (Twemoji format)."""
            return "-".join(f"{ord(ch):x}" for ch in s)


        def _estimate_x_height(font: ImageFont.FreeTypeFont) -> int:
            """Estimate x-height of the given font."""
            try:
                l, t, r, b = font.getbbox("x")
                return max(1, b - t)
            except Exception:
                return max(1, int(font.size * 0.5))


        def compute_emoji_y_shift(font: ImageFont.FreeTypeFont, scale: float) -> int:
            """Estimate vertical offset to visually align emoji center with text body."""
            ascent, _ = font.getmetrics()
            xh = _estimate_x_height(font)
            em = int(round(font.size * scale))
            baseline_y = ascent
            target_center_y = baseline_y - xh * 0.55
            emoji_top_y = target_center_y - em / 2.0
            default_top_y = baseline_y - em
            return int(round(emoji_top_y - default_top_y))


        @functools.lru_cache(maxsize=4096)
        def _load_twemoji_png(codepoint: str) -> Image.Image:
            """Return RGBA Twemoji PNG for the given codepoint, local or CDN-based."""
            filename = f"{codepoint}.png"
            if TWEMOJI_PNG_DIR:
                local_path = os.path.join(TWEMOJI_PNG_DIR, filename)
                if os.path.isfile(local_path):
                    im = Image.open(local_path)
                    return im.convert("RGBA") if im.mode != "RGBA" else im
            url = f"{TWEMOJI_CDN}/{filename}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = resp.read()
            im = Image.open(BytesIO(data))
            return im.convert("RGBA") if im.mode != "RGBA" else im


        def draw_text_with_emojis(
            img: Image.Image,
            xy: Tuple[int, int],
            text: str,
            font: ImageFont.FreeTypeFont,
            *,
            fill=(0, 0, 0, 255),
            emoji_scale: float = 1.0,
            emoji_shift_px: Optional[int] = None,
        ) -> None:
            """Draw single-line text with emojis aligned to text baseline."""
            x, y = xy
            draw = ImageDraw.Draw(img, "RGBA")
            if emoji_shift_px is None:
                emoji_shift_px = compute_emoji_y_shift(font, emoji_scale)
            for kind, chunk in _split_text_emoji(text):
                if kind == "text" and chunk:
                    draw.text((x, y), chunk, font=font, fill=fill)
                    x += draw.textlength(chunk, font=font)
                elif kind == "emoji":
                    cp = _codepoints(chunk)
                    try:
                        im = _load_twemoji_png(cp)
                    except Exception:
                        em = max(1, int(round(font.size * emoji_scale)))
                        im = Image.new("RGBA", (em, em), (0, 0, 0, 0))
                        g = ImageDraw.Draw(im)
                        g.rectangle([0, 0, em - 1, em - 1], outline=(0, 0, 0, 255))
                        g.line([0, 0, em - 1, em - 1], fill=(0, 0, 0, 255))
                        g.line([0, em - 1, em - 1, 0], fill=(0, 0, 0, 255))
                    target = max(1, int(round(font.size * emoji_scale)))
                    if im.height != target:
                        im = im.resize((target, target), Image.LANCZOS)
                    ascent, _ = font.getmetrics()
                    top = y + ascent - target + (emoji_shift_px or 0)
                    img.alpha_composite(im, (int(x), int(top)))
                    x += target


        def measure_text_with_emojis(
            text: str,
            font: ImageFont.FreeTypeFont,
            *,
            emoji_scale: float = 1.0,
            emoji_shift_px: Optional[int] = None,
            padding: int = 4,
        ) -> Tuple[int, int]:
            """Measure width and height of rendered text with emojis."""
            if emoji_shift_px is None:
                emoji_shift_px = compute_emoji_y_shift(font, emoji_scale)
            rough_w = 2 * padding
            for kind, chunk in _split_text_emoji(text):
                if kind == "text" and chunk:
                    rough_w += int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(chunk, font=font))
                else:
                    rough_w += int(round(font.size * emoji_scale))
            ascent, descent = font.getmetrics()
            rough_h = ascent + descent + 2 * padding
            tmp = Image.new("RGBA", (max(1, rough_w), max(1, rough_h)), (0, 0, 0, 0))
            draw_text_with_emojis(tmp, (padding, padding), text, font,
                                fill=(0, 0, 0, 255),
                                emoji_scale=emoji_scale,
                                emoji_shift_px=emoji_shift_px)
            bbox = tmp.getbbox()
            if not bbox:
                return (1, 1)
            l, t, r, b = bbox
            return (max(1, r - l), max(1, b - t))


        def measure_rotated_text_with_emojis(
            text: str,
            font: ImageFont.FreeTypeFont,
            angle_deg: float,
            *,
            emoji_scale: float = 1.0,
            emoji_shift_px: Optional[int] = None,
            padding: int = 4,
        ) -> Tuple[int, int]:
            """Measure rotated text with emojis by rendering, rotating, and cropping."""
            if emoji_shift_px is None:
                emoji_shift_px = compute_emoji_y_shift(font, emoji_scale)
            w, h = measure_text_with_emojis(text, font,
                                            emoji_scale=emoji_scale,
                                            emoji_shift_px=emoji_shift_px,
                                            padding=padding)
            tmp = Image.new("RGBA", (w + 2 * padding, h + 2 * padding), (0, 0, 0, 0))
            draw_text_with_emojis(tmp, (padding, padding), text, font,
                                emoji_scale=emoji_scale,
                                emoji_shift_px=emoji_shift_px)
            try:
                tmp = tmp.rotate(float(angle_deg), expand=True,
                                resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
            except Exception:
                tmp = tmp.rotate(float(angle_deg), expand=True)
            bbox = tmp.getbbox()
            if not bbox:
                return (1, 1)
            l, t, r, b = bbox
            return (max(1, r - l), max(1, b - t))

        def _measure_rotated_text_size_px(text: str, font, angle_deg: float) -> tuple[int, int]:
            """Измеряет реальный размер (после Pilmoji-рендера и поворота)."""
            # bidi/arabic shaping
            reshaped_text = arabic_reshaper.reshape(text)
            text_disp = get_display(reshaped_text)

            # Оценочный bbox
            bb0 = draw.textbbox((0, 0), text_disp, font=font)
            tw0 = max(1, bb0[2] - bb0[0])
            th0 = max(1, bb0[3] - bb0[1])

            pad = max(8, int(getattr(font, "size", 16)) * 2)

            tmp = _PIL_Image.new("RGBA", (tw0 + pad * 2, th0 + pad * 2), (0, 0, 0, 0))
            try:
                with Pilmoji(tmp) as p:
                    p.text((pad - bb0[0], pad - bb0[1]), text_disp, font=font, fill=(0, 0, 0, 255))
            except Exception:
                # На всякий случай fallback (хотя Pilmoji установлен)
                td = _PIL_Draw.Draw(tmp, "RGBA")
                td.text((pad - bb0[0], pad - bb0[1]), text_disp, font=font, fill=(0, 0, 0, 255))

            if abs(float(angle_deg)) > 1e-6:
                try:
                    tmp = tmp.rotate(float(angle_deg), expand=True, resample=_PIL_Image.BICUBIC, fillcolor=(0, 0, 0, 0))
                except Exception:
                    tmp = tmp.rotate(float(angle_deg), expand=True)

            a = tmp.split()[-1]
            bbox = a.getbbox()
            if bbox:
                rw = bbox[2] - bbox[0]
                rh = bbox[3] - bbox[1]
            else:
                rw, rh = tmp.width, tmp.height

            return int(rw), int(rh)


        def _fit_font_to_block(text: str, family: str, initial_size_px: int, max_w_px: int, max_h_px: int, angle_deg: float):
            """Return a truetype font scaled down so rotated text fits within max_w_px x max_h_px."""
            import math
            size_px = max(1, int(initial_size_px))
            font = _truetype_for_family(family, size_px)
            rw, rh = _measure_rotated_text_size_px(text, font, angle_deg)
            # Fast path already fits
            if rw <= max_w_px and rh <= max_h_px:
                return font, size_px
            # Compute first estimate by proportional scaling
            # Guard against zero to avoid division by zero
            scale_w = max_w_px / float(max(1, rw))
            scale_h = max_h_px / float(max(1, rh))
            scale = min(scale_w, scale_h, 1.0)
            new_size = max(1, int(math.floor(size_px * scale)))
            if new_size == size_px and scale < 1.0:
                new_size = max(1, size_px - 1)
            # Refine with a small loop due to raster rounding
            attempts = 0
            while attempts < 10:
                attempts += 1
                size_px = new_size
                font = _truetype_for_family(family, size_px)
                rw, rh = _measure_rotated_text_size_px(text, font, angle_deg)
                if rw <= max_w_px and rh <= max_h_px:
                    return font, size_px
                # reduce size and retry
                new_size = max(1, size_px - 1)
                if new_size == size_px:
                    break
            return font, size_px

        # Empirical scale so exported text matches on-canvas perceived size
        # TEXT_PT_TO_PX_SCALE = 1.33
        TEXT_PT_TO_PX_SCALE = 1.0

        # Рамка «джига» — не рисуем в растре, чтобы PNG/JPG были без рамки.
        # Рамку добавим в PDF на этапе Cairo (см. ниже).
        jw = max(1, int(round(jig_w_mm * px_per_mm)))
        jh = max(1, int(round(jig_h_mm * px_per_mm)))
        jx0 = 0
        jy0 = 0
        jx1 = page_w_px - 1
        jy1 = page_h_px - 1

        def mm_to_px(m: float) -> int:
            return int(round(float(m) * px_per_mm))

        def rect_from_mm(x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> tuple[int, int, int, int]:
            l = int(round(float(x_mm) * px_per_mm))
            t = int(round(float(y_mm) * px_per_mm))
            r = int(round(float(x_mm + w_mm) * px_per_mm))
            b = int(round(float(y_mm + h_mm) * px_per_mm))
            if r <= l:
                r = l + 1
            if b <= t:
                b = t + 1
            return l, t, r, b

        # стабильная сортировка по z как по float, с привязкой к исходному порядку
        def _z_of(val) -> float:
            try:
                z = val.get("z", 0)
                return float(z)
            except Exception:
                return 0.0

        items_sorted = sorted(
            enumerate(items),
            key=lambda p: (_z_of(p[1]), p[0])  # (z, исходный индекс)
        )
        items = [it for _, it in items_sorted]

        if not only_jig:
            # Determine if we should draw borders around images based on pattern JSON
            def _parse_cmyk_to_rgba(cmyk_str: str, default=(0, 0, 0, 255)) -> tuple[int, int, int, int]:
                try:
                    parts = [p.strip() for p in str(cmyk_str or "").split(",")]
                    # pad/truncate to 4
                    if len(parts) < 4:
                        parts += ["0"] * (4 - len(parts))
                    elif len(parts) > 4:
                        parts = parts[:4]
                    c, m, y, k = [float(p or 0) for p in parts]
                    if c == 0 and m == 100 and y == 0 and k == 0:
                        return (236, 0, 140, 255) 
                    elif c == 75 and m == 0 and y == 75 and k == 0:
                        return (90, 178, 121, 255) 
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

            def _should_border_and_color(current_items: list[dict]) -> tuple[bool, tuple[int, int, int, int]]:
                # Try to locate current pattern file by sku_name or saved_product
                import json as _json
                name = ""
                try:
                    if getattr(state, "sku_name", ""):
                        name = str(state.sku_name)
                    elif getattr(state, "saved_product", ""):
                        name = str(state.saved_product)
                except Exception:
                    name = ""
                border = False
                rgba = (0, 0, 0, 255)
                if name:
                    p = PRODUCTS_PATH / f"{name}.json"
                    if p.exists():
                        data = _json.loads(p.read_text(encoding="utf-8"))
                        if isinstance(data, dict):
                            border = ("FrontsideBarcode" in data) or ("BacksideBarcode" in data)
                            try:
                                cmyk = (((data.get("Scene") or {}).get("object_cmyk")) or "0,0,0,0")
                            except Exception:
                                cmyk = "0,0,0,0"
                            rgba = _parse_cmyk_to_rgba(cmyk, default=(0, 0, 0, 255))
                # If file not found or parsing failed, check current scene store
                if not border:
                    st = getattr(self.s, "_scene_store", {}) or {}
                    fr = st.get("front") or []
                    bk = st.get("back") or []
                    if any((isinstance(it, dict) and str(it.get("type", "")) == "barcode") for it in list(fr) + list(bk)):
                        border = True
                    # Color fallback from UI widget if present
                    if hasattr(self.s, "obj_cmyk") and callable(getattr(self.s.obj_cmyk, "get", None)):
                        rgba = _parse_cmyk_to_rgba(str(self.s.obj_cmyk.get() or "0,0,0,0"))
                # Lastly, directly inspect current items being rendered
                if not border:
                    if any((isinstance(it, dict) and str(it.get("type", "")) == "barcode") for it in list(current_items or [])):
                        border = True
                
                logger.debug(f"Border detection: draw_borders={border}, rgba={rgba}")
                return border, rgba

            draw_borders, border_rgba = _should_border_and_color(items)
            logger.info(f"Will draw kiss-cut borders: {draw_borders}")

            def _draw_borders_around_slots(it: dict) -> None:
                """Draw kiss-cut borders around all slots if enabled."""
                if draw_borders:
                    try:
                        # Desired inset from slot edge towards center
                        desired_inset_px = max(1, mm_to_px(1.0))  # 1mm inside the slot
                        stroke_px = max(1, int(round(px_per_mm * 0.25)))  # ~0.25mm stroke width
                        radius_px = max(1, int(round(px_per_mm * 1.5)))   # ~1.5mm corner radius

                        # Use slot_* coordinates if provided; fallback to image coords
                        try:
                            slot_x_mm = float(it["slot_x_mm"])
                        except Exception:
                            logger.error("No slot_x_mm for border drawing %s", it)
                            return
                        try:
                            slot_y_mm = float(it["slot_y_mm"])
                        except Exception:
                            logger.error("No slot_y_mm for border drawing %s", it)
                            return
                        try:
                            slot_w_mm = float(it["slot_w_mm"])
                        except Exception:
                            logger.error("No slot_w_mm for border drawing %s", it)
                            return
                        try:
                            slot_h_mm = float(it["slot_h_mm"])
                        except Exception:
                            logger.error("No slot_h_mm for border drawing %s", it)
                            return
                        
                        slot_left_px = mm_to_px(slot_x_mm)
                        slot_top_px  = mm_to_px(slot_y_mm)
                        sw_px = max(1, int(round(slot_w_mm * px_per_mm)))
                        sh_px = max(1, int(round(slot_h_mm * px_per_mm)))

                        # Ensure inset leaves room for stroke on all sides
                        max_inset_allowed = max(1, min((sw_px - 2) // 2, (sh_px - 2) // 2))
                        inset = min(desired_inset_px, max_inset_allowed)

                        # Clamp radius to fit available interior
                        avail_w = max(1, sw_px - 2 * inset)
                        avail_h = max(1, sh_px - 2 * inset)
                        rr = min(radius_px, avail_w // 2, avail_h // 2)

                        border_layer = _PIL_Image.new("RGBA", (sw_px, sh_px), (0, 0, 0, 0))
                        _bd = _PIL_Draw.Draw(border_layer, "RGBA")
                        half = stroke_px / 2.0
                        # Internal rect path: inset + half-stroke to keep stroke fully inside
                        x0 = inset + half
                        y0 = inset + half
                        x1 = sw_px - 1 - inset - half
                        y1 = sh_px - 1 - inset - half
                        if x1 <= x0 or y1 <= y0:
                            # Fallback: no inset
                            x0 = half; y0 = half; x1 = sw_px - 1 - half; y1 = sh_px - 1 - half
                        _bd.rounded_rectangle(
                            [(x0, y0), (x1, y1)],
                            radius=max(1, int(rr)),
                            outline=border_rgba,
                            width=stroke_px,
                        )
                        # Paste border on top positioned by slot coords
                        img.paste(border_layer, (int(slot_left_px), int(slot_top_px)), border_layer.split()[-1])
                        
                        # Also store border information for spot color version in combined PDF
                        it["_border_needed"] = True
                        it["_border_slot_x_mm"] = slot_x_mm
                        it["_border_slot_y_mm"] = slot_y_mm
                        it["_border_slot_w_mm"] = slot_w_mm
                        it["_border_slot_h_mm"] = slot_h_mm
                        it["_border_color_rgba"] = border_rgba
                    except Exception:
                        logger.exception("Failed to draw rounded border for image")

            for it in items:
                typ = str(it.get("type", ""))

                if typ == "slot":
                    l, top, r, btm = rect_from_mm(it.get("x_mm", 0.0), it.get("y_mm", 0.0), it.get("w_mm", 0.0), it.get("h_mm", 0.0))
                    draw.rectangle([l, top, r - 1, btm - 1], outline=(137, 137, 137, 255), width=10)
                    label = str(it.get("label", ""))
                    if label and font_small is not None:
                        cx = l + (r - l) // 2
                        cy = top + (btm - top) // 2
                        bbox = draw.textbbox((0, 0), label, font=font_small)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        draw.text((cx - tw // 2, cy - th // 2), label, fill=(200, 200, 200, 255), font=font_small)

                elif typ == "rect":
                    l, top, r, btm = rect_from_mm(
                        it.get("x_mm", 0.0),
                        it.get("y_mm", 0.0),
                        it.get("w_mm", 0.0),
                        it.get("h_mm", 0.0)
                    )
                    label = str(it.get("label", "")).strip()
                    if label:
                        # Get mirror flag for rect text objects (from per-ASIN setting)
                        mirror = bool(it.get("mirror", False))
                        
                        # Use rotated bounds to compute correct center from stored top-left
                        # Desired styling (with sensible defaults)
                        fam = str(it.get("label_font_family", "Myriad Pro"))
                        try:
                            size_pt = int(round(float(it.get("label_font_size", 10))))
                        except Exception:
                            size_pt = 10
                            raise
                        col = _parse_hex_rgba(it.get("label_fill", "#ffffff"), default=(255, 255, 255, 255))
                        # Convert pt -> px at target DPI
                        # size_px = max(1, int(round(size_pt * float(dpi) / 72.0 * TEXT_PT_TO_PX_SCALE)))
                        size_px = max(1, int(round(size_pt * float(dpi) / 25.4 * TEXT_PT_TO_PX_SCALE)))
                        try:
                            ang = float(it.get("angle", 0.0) or 0.0)
                        except Exception:
                            ang = 0.0
                            raise
                        # Rotated bounds (mm) based on original block size
                        try:
                            w_mm_orig = float(it.get("w_mm", 0.0) or 0.0)
                            h_mm_orig = float(it.get("h_mm", 0.0) or 0.0)
                        except Exception:
                            w_mm_orig, h_mm_orig = 0.0, 0.0
                            raise
                        try:
                            bw_mm, bh_mm = self.s._rotated_bounds_mm(float(w_mm_orig), float(h_mm_orig), float(ang))
                        except Exception:
                            bw_mm, bh_mm = float(w_mm_orig), float(h_mm_orig)
                            raise
                        # Fit font to rotated bounds in pixel space
                        bw_px = max(1, int(round(float(bw_mm) * px_per_mm)))
                        bh_px = max(1, int(round(float(bh_mm) * px_per_mm)))
                        fnt, _ = _fit_font_to_block(label, fam, size_px, bw_px, bh_px, ang)
                        # Center from stored top-left of rotated bounds to match on-canvas position
                        try:
                            x_mm = float(it.get("x_mm", 0.0) or 0.0)
                            y_mm = float(it.get("y_mm", 0.0) or 0.0)
                        except Exception:
                            x_mm, y_mm = 0.0, 0.0
                        cx = jx0 + mm_to_px(x_mm + bw_mm / 2.0)
                        cy = jy0 + mm_to_px(y_mm + bh_mm / 2.0)
                        _draw_rotated_text_center(label, int(cx), int(cy), fnt, col, ang, mirror)

                    _draw_borders_around_slots(it)

                elif typ == "image":
                    path_img = str(it.get("path", "")) or ""
                    if not path_img:
                        continue
                    try:
                        ang = float(it.get("angle", 0.0) or 0.0)
                    except Exception:
                        ang = 0.0
                    try:
                        w_mm_orig = float(it.get("w_mm", 0.0))
                        h_mm_orig = float(it.get("h_mm", 0.0))
                    except Exception:
                        w_mm_orig, h_mm_orig = 0.0, 0.0

                    left_px = mm_to_px(it.get("x_mm", 0.0))
                    top_px  = mm_to_px(it.get("y_mm", 0.0))
                    w_px = max(1, int(round(w_mm_orig * px_per_mm)))
                    h_px = max(1, int(round(h_mm_orig * px_per_mm)))
                    ext = os.path.splitext(path_img)[1].lower()

                    try:
                        if it.get("loaded_image", None):
                            im: _PIL_Image.Image = it.get("loaded_image")

                        elif ext == ".svg":
                            im = svg_to_png(str(path_img), width=int(w_px), height=int(h_px), device_pixel_ratio=1.0)
                            # ожидаем RGBA
                            if im.mode != "RGBA":
                                im = im.convert("RGBA")
                        else:
                            try:
                                im = _PIL_Image.open(path_img).convert("RGBA")
                            except FileNotFoundError:
                                try:
                                    im = _PIL_Image.open(PRODUCTS_PATH / path_img).convert("RGBA")
                                except Exception:
                                    logger.exception(f"Failed to open image file {path_img}")
                                    raise

                        # Apply mirror (flip horizontally) if per-ASIN mirror flag is set BEFORE any transformations
                        try:
                            if it.get("mirror", False):
                                im = im.transpose(_PIL_Image.FLIP_LEFT_RIGHT)
                        except Exception:
                            logger.exception("Failed to apply mirror flip for PDF render")
                        
                        im_resized = im.resize((int(w_px), int(h_px)), _PIL_Image.LANCZOS)
                        # Apply clip-based mask (same cut behavior as canvas)
                        try:
                            mpath = str(it.get("mask_path", "") or "")
                            if mpath:
                                mabs = mpath
                                try:
                                    if not os.path.isabs(mpath):
                                        cand = PRODUCTS_PATH / mpath
                                        if os.path.exists(cand):
                                            mabs = str(cand)
                                except Exception:
                                    pass
                                if os.path.exists(mabs) and hasattr(self.s, "images"):
                                    try:
                                        im_resized = self.s.images._apply_mask_clip(im_resized, mabs, int(w_px), int(h_px))
                                    except Exception:
                                        logger.exception("Failed applying clip-based mask for PDF render")
                        except Exception:
                            logger.exception("Failed to handle mask for PDF render")
                        if abs(ang) > 1e-6:
                            im_resized = im_resized.rotate(-ang, expand=True, resample=_PIL_Image.BICUBIC, fillcolor=(0, 0, 0, 0))

                        # Строгое наложение слоя поверх уже нарисованного (уважая z-порядок)
                        try:
                            # Pillow >= 9.1: поддерживает offset
                            img.alpha_composite(im_resized, (int(left_px), int(top_px)))
                        except Exception:
                            # Фолбэк для старых версий: paste по альфа-каналу
                            img.paste(im_resized, (int(left_px), int(top_px)), im_resized.split()[-1])

                        # Optional rounded border around image if pattern has barcode keys (internal inset using slot bounds)
                        # Store border information for spot color border drawing in PDF
                        _draw_borders_around_slots(it)
                    except Exception as e:
                        logger.exception(f"Failed to render image in PDF: {e}")

                elif typ == "text":
                    # Handle both plain text items and text blocks inside slots
                    try:
                        ang = float(it.get("angle", 0.0) or 0.0)
                    except Exception:
                        ang = 0.0
                        raise

                    # Get mirror flag for text objects (from per-ASIN setting)
                    mirror = bool(it.get("mirror", False))

                    has_block_size = ("w_mm" in it) and ("h_mm" in it)
                    if has_block_size:
                        # Text block serialized in slot: use label_* fields
                        txt = str(it.get("label", "")).strip()
                        if not txt:
                            continue
                        fam = str(it.get("label_font_family", "Myriad Pro"))
                        try:
                            size_pt = int(round(float(it.get("label_font_size", 10))))
                        except Exception:
                            size_pt = 10
                            raise
                        col = _parse_hex_rgba(it.get("label_fill", "#17a24b"), default=(23, 162, 75, 255))
                        size_px = max(1, int(round(size_pt * float(dpi) / 25.4 * TEXT_PT_TO_PX_SCALE)))

                        try:
                            w_mm = float(it.get("w_mm", 0.0))
                            h_mm = float(it.get("h_mm", 0.0))
                            x_mm = float(it.get("x_mm", 0.0))
                            y_mm = float(it.get("y_mm", 0.0))
                        except Exception:
                            w_mm, h_mm, x_mm, y_mm = 0.0, 0.0, 0.0, 0.0
                            raise
                        # Compute rotated block bounds and fit text to it
                        try:
                            bw_mm, bh_mm = self.s._rotated_bounds_mm(float(w_mm), float(h_mm), float(ang))
                        except Exception:
                            bw_mm, bh_mm = float(w_mm), float(h_mm)
                            raise
                        bw_px = max(1, int(round(float(bw_mm) * px_per_mm)))
                        bh_px = max(1, int(round(float(bh_mm) * px_per_mm)))
                        fnt, fitted_px = _fit_font_to_block(txt, fam, size_px, bw_px, bh_px, ang)
                        # Center using rotated bounds (matches on-canvas block placement semantics)
                        cx = jx0 + mm_to_px(x_mm + bw_mm / 2.0)
                        cy = jy0 + mm_to_px(y_mm + bh_mm / 2.0)
                        _draw_rotated_text_center(txt, int(cx), int(cy), fnt, col, ang, mirror)
                    else:
                        # Plain free text object, centered at (x_mm, y_mm)
                        txt = str(it.get("text", "")).strip()
                        if not txt:
                            continue
                        fam = str(it.get("font_family", "Myriad Pro"))
                        try:
                            size_pt = int(round(float(it.get("font_size_pt", 12))))
                        except Exception:
                            size_pt = 12
                            raise
                        col = _parse_hex_rgba(it.get("fill", "#17a24b"), default=(23, 162, 75, 255))
                        size_px = max(1, int(round(size_pt * float(dpi) / 72.0 * TEXT_PT_TO_PX_SCALE)))
                        fnt = _truetype_for_family(fam, size_px)
                        cx = jx0 + mm_to_px(it.get("x_mm", 0.0))
                        cy = jy0 + mm_to_px(it.get("y_mm", 0.0))
                        _draw_rotated_text_center(txt, int(cx), int(cy), fnt, col, ang, mirror)

                    _draw_borders_around_slots(it)

                elif typ == "barcode":
                    # Render Code128 barcode to PDF with rotation support
                    try:
                        import barcode
                        from barcode.writer import ImageWriter
                        
                        # Use barcode_text parameter instead of label field
                        bc_text = str(barcode_text).strip()
                        if not bc_text:
                            bc_text = "TEST"
                        
                        # Generate Code128 barcode WITHOUT built-in text
                        code128 = barcode.get_barcode_class('code128')
                        writer = ImageWriter()
                        barcode_instance = code128(bc_text, writer=writer)
                        
                        buffer = BytesIO()
                        # Disable text rendering in barcode library by passing write_text=False
                        barcode_instance.write(buffer, options={'write_text': False})
                        buffer.seek(0)
                        
                        barcode_img = _PIL_Image.open(buffer).convert("RGBA")
                        
                        # Make white background transparent
                        data__ = np.array(barcode_img)
                        r, g, b, a = data__[:,:,0], data__[:,:,1], data__[:,:,2], data__[:,:,3]
                        # Set alpha to 0 where pixels are white (or near-white)
                        white_mask = (r > 250) & (g > 250) & (b > 250)
                        data__[:,:,3] = np.where(white_mask, 0, 255)
                        barcode_img = _PIL_Image.fromarray(data__, mode="RGBA")
                        
                        # Get barcode dimensions, position, and rotation
                        w_mm = float(it.get("w_mm", 80.0))
                        h_mm = float(it.get("h_mm", 30.0))
                        x_mm = float(it.get("x_mm", 0.0))
                        y_mm = float(it.get("y_mm", 0.0))
                        try:
                            angle = float(it.get("angle", 0.0) or 0.0)
                        except Exception:
                            angle = 0.0
                        
                        # Convert to pixels
                        w_px = max(1, int(round(w_mm * px_per_mm)))
                        h_px = max(1, int(round(h_mm * px_per_mm)))
                        
                        # Calculate space allocation: 70% for barcode, 15% for barcode text, 15% for reference text
                        barcode_h_px = int(h_px * 0.7)
                        barcode_text_h_px = int(h_px * 0.15)
                        reference_text_h_px = h_px - barcode_h_px - barcode_text_h_px
                        
                        # Small padding between items (in pixels)
                        padding = max(2, int(h_px * 0.01))
                        
                        # Resize barcode to allocated space (barcode only, no text)
                        barcode_resized = barcode_img.resize((w_px, barcode_h_px), _PIL_Image.LANCZOS)
                        
                        # Create combined image with barcode, barcode text, and reference text
                        combined_img = _PIL_Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
                        
                        # Paste barcode at the top
                        combined_img.paste(barcode_resized, (0, 0), barcode_resized.split()[-1])
                        
                        text_draw = _PIL_Draw.Draw(combined_img, "RGBA")
                        
                        # Add barcode text below barcode with minimal padding
                        if bc_text and barcode_text_h_px > 0:
                            # Calculate font size to fit the barcode text space
                            bc_text_font_size_px = max(8, int(barcode_text_h_px * 0.8))
                            try:
                                bc_text_font = _truetype_for_family("Myriad Pro", bc_text_font_size_px)
                            except Exception:
                                bc_text_font = _PIL_Font.load_default()
                            
                            # Draw barcode text centered below barcode with minimal top padding
                            try:
                                bbox = text_draw.textbbox((0, 0), bc_text, font=bc_text_font)
                                text_w = bbox[2] - bbox[0]
                                text_h = bbox[3] - bbox[1]
                            except Exception:
                                text_w, text_h = 0, 0
                            
                            text_x = (w_px - text_w) // 2
                            text_y = barcode_h_px + padding
                            text_draw.text((text_x, text_y), bc_text, font=bc_text_font, fill=(0, 0, 0, 255))
                        
                        # Add reference text below barcode text with minimal padding
                        ref_text = str(reference_text).strip()
                        if ref_text and reference_text_h_px > 0:
                            # Calculate font size to fit the reference text space
                            ref_text_font_size_px = max(8, int(reference_text_h_px * 0.8))
                            try:
                                ref_text_font = _truetype_for_family("Myriad Pro", ref_text_font_size_px)
                            except Exception:
                                ref_text_font = _PIL_Font.load_default()
                            
                            # Draw reference text centered at bottom with minimal top padding
                            try:
                                bbox = text_draw.textbbox((0, 0), ref_text, font=ref_text_font)
                                text_w = bbox[2] - bbox[0]
                                text_h = bbox[3] - bbox[1]
                            except Exception:
                                text_w, text_h = 0, 0
                            
                            text_x = (w_px - text_w) // 2
                            text_y = barcode_h_px + barcode_text_h_px + padding
                            text_draw.text((text_x, text_y), ref_text, font=ref_text_font, fill=(0, 0, 0, 255))
                        
                        # Now use combined image for rotation
                        barcode_resized = combined_img
                        
                        # Apply rotation if any (same direction as rect labels)
                        # For rect/barcode, stored angle is already signed to match desired clockwise rotation
                        if abs(angle) > 1e-6:
                            try:
                                barcode_resized = barcode_resized.rotate(angle, expand=True, resample=_PIL_Image.BICUBIC, fillcolor=(0, 0, 0, 0))
                            except Exception:
                                barcode_resized = barcode_resized.rotate(angle, expand=True)
                        
                        # Compute rotated bounds for placement
                        import math
                        a = math.radians(abs(angle) % 360.0)
                        ca = abs(math.cos(a))
                        sa = abs(math.sin(a))
                        bw = int((w_px * ca) + (h_px * sa))
                        bh = int((w_px * sa) + (h_px * ca))
                        
                        # Position at top-left of rotated bounds (consistent with rect behavior)
                        left_px = mm_to_px(x_mm)
                        top_px = mm_to_px(y_mm)
                        
                        # Composite barcode onto output image
                        try:
                            img.alpha_composite(barcode_resized, (int(left_px), int(top_px)))
                        except Exception:
                            img.paste(barcode_resized, (int(left_px), int(top_px)), barcode_resized.split()[-1])
                        
                    except Exception as e:
                        logger.exception(f"Failed to render barcode in PDF: {e}")

        # out_rgb = _PIL_Image.new("RGB", (page_w_px, page_h_px), "white")
        out_rgb = _PIL_Image.new("RGBA", (page_w_px, page_h_px), (255, 255, 255, 0))
        alpha = img.split()[-1]
        out_rgb.paste(img.convert("RGB"), mask=alpha)
        out_rgb = _darken_white_color(out_rgb)

        width_px, height_px = out_rgb.size

        # Переводим пиксели в пункты (1 дюйм = 72 точки)
        width_pt = width_px * 72 / dpi
        height_pt = height_px * 72 / dpi

        # Создаём PDFSurface
        surface = cairo.PDFSurface(path, width_pt, height_pt)
        context = cairo.Context(surface)

        # Загружаем PNG в Cairo
        with io.BytesIO() as buffer:
            out_rgb.save(buffer, format="PNG")
            buffer.seek(0)
            image_surface = cairo.ImageSurface.create_from_png(buffer)

        # Масштабируем, чтобы учесть DPI
        scale = 72.0 / dpi
        context.scale(scale, scale)

        # Рисуем изображение
        context.set_source_surface(image_surface, 0, 0)
        context.paint()

        # Завершаем PDF
        surface.finish()

        # Add kiss-cut spot color borders for images if needed
        try:
            self._add_kiss_cut_borders_to_pdf(path, items, jig_w_mm, jig_h_mm, dpi)
        except Exception as e:
            logger.exception(f"Failed to add kiss-cut borders: {e}")

        # Expose last rendered raster (for PNG/JPG export)
        try:
            # Keep a copy so later modifications do not affect stored reference
            self._last_render_image = out_rgb.copy()
            self._last_render_dpi = int(dpi)
        except Exception:
            # Non-fatal: auxiliary export may be unavailable
            self._last_render_image = None
            self._last_render_dpi = None

    def _add_kiss_cut_borders_to_pdf(
        self,
        pdf_path: str,
        items: list[dict],
        jig_w_mm: float,
        jig_h_mm: float,
        dpi: int
    ) -> None:
        """Add kiss-cut spot color borders around images that need them."""
        try:
            import pikepdf
        except ImportError:
            logger.warning("pikepdf not available, skipping kiss-cut borders")
            return

        # Collect items that need borders
        border_items = [it for it in items if it.get("_border_needed", False)]
        if not border_items:
            logger.debug("No items need kiss-cut borders")
            return

        logger.info(f"Adding kiss-cut borders to {len(border_items)} images in {pdf_path}")

        # Open the PDF
        pdf = pikepdf.Pdf.open(pdf_path, allow_overwriting_input=True)

        if len(pdf.pages) == 0:
            logger.warning("PDF has no pages")
            pdf.close()
            return

        page = pdf.pages[0]

        # Get CMYK from first border item (all should have same color)
        first_item = border_items[0]
        border_rgba = first_item.get("_border_color_rgba", (0, 0, 0, 255))

        # Convert RGBA to CMYK (reverse of the CMYK->RGBA conversion)
        def rgba_to_cmyk_normalized(rgba: tuple) -> tuple:
            """Convert RGBA (0-255) to normalized CMYK (0-1)."""
            r, g, b, a = [x / 255.0 for x in rgba]
            # Simple RGB to CMYK conversion
            k = 1 - max(r, g, b)
            if k < 1.0:
                c = (1 - r - k) / (1 - k)
                m = (1 - g - k) / (1 - k)
                y = (1 - b - k) / (1 - k)
            else:
                c = m = y = 0.0
            return (c, m, y, k)

        c, m, y, k = rgba_to_cmyk_normalized(border_rgba)
        logger.info(f"Using CMYK for kiss-cut: C={c:.2f}, M={m:.2f}, Y={y:.2f}, K={k:.2f}")

        # Create spot color "cutcontourkiss"
        spot_color_name = "cutcontourkiss"

        # Tint transform function (PostScript Type 4)
        tint_function_code = (
            f"{{ "
            f"dup dup dup "
            f"{c} mul 4 1 roll "
            f"{m} mul 3 1 roll "
            f"{y} mul exch "
            f"{k} mul "
            f"}}"
        ).encode('latin-1')

        tint_transform = pikepdf.Stream(pdf, tint_function_code)
        tint_transform.FunctionType = 4
        tint_transform.Domain = [0, 1]
        tint_transform.Range = [0, 1, 0, 1, 0, 1, 0, 1]

        separation_colorspace = pikepdf.Array([
            pikepdf.Name.Separation,
            pikepdf.Name("/" + spot_color_name),
            pikepdf.Name.DeviceCMYK,
            tint_transform
        ])

        # Add ColorSpace to page resources
        if pikepdf.Name.Resources not in page:
            page.Resources = pikepdf.Dictionary()

        if pikepdf.Name.ColorSpace not in page.Resources:
            page.Resources.ColorSpace = pikepdf.Dictionary()

        page.Resources.ColorSpace.KissColor = separation_colorspace

        # Build content stream for rounded rectangles
        mm_to_pt = 72.0 / 25.4
        content_lines = []

        # Border parameters (1mm inset, 0.25mm stroke, 1.5mm radius)
        inset_mm = 1.0
        stroke_mm = 0.25
        radius_mm = 1.5

        inset_pt = inset_mm * mm_to_pt
        stroke_pt = stroke_mm * mm_to_pt
        radius_pt = radius_mm * mm_to_pt

        for item in border_items:
            try:
                slot_x_mm = item["_border_slot_x_mm"]
                slot_y_mm = item["_border_slot_y_mm"]
                slot_w_mm = item["_border_slot_w_mm"]
                slot_h_mm = item["_border_slot_h_mm"]

                # Convert to points
                x_pt = slot_x_mm * mm_to_pt
                y_pt = slot_y_mm * mm_to_pt
                w_pt = slot_w_mm * mm_to_pt
                h_pt = slot_h_mm * mm_to_pt

                # Calculate inset rectangle
                x0 = x_pt + inset_pt
                y0 = y_pt + inset_pt
                x1 = x_pt + w_pt - inset_pt
                y1 = y_pt + h_pt - inset_pt

                # Ensure valid dimensions
                if x1 <= x0 or y1 <= y0:
                    continue

                # Draw rounded rectangle path using Bézier curves for corners
                # PDF coordinate system: origin at bottom-left
                r = min(radius_pt, (x1 - x0) / 2, (y1 - y0) / 2)
                
                # Magic number for circular arc approximation with cubic Bézier
                kappa = 0.5522847498  # (4/3) * tan(π/8)

                content_lines.append(b"q")  # Save state
                content_lines.append(b"/KissColor CS")  # Set stroke color space
                content_lines.append(b"1 SCN")  # Set stroke color (100% tint)
                content_lines.append(f"{stroke_pt:.4f} w".encode())  # Set line width

                # Start at top-left (after the arc)
                content_lines.append(f"{x0 + r:.4f} {y1:.4f} m".encode())

                # Top edge to top-right corner
                content_lines.append(f"{x1 - r:.4f} {y1:.4f} l".encode())

                # Top-right corner (90° arc using Bézier curve)
                cp1_x = x1 - r + r * kappa
                cp1_y = y1
                cp2_x = x1
                cp2_y = y1 - r + r * kappa
                end_x = x1
                end_y = y1 - r
                content_lines.append(f"{cp1_x:.4f} {cp1_y:.4f} {cp2_x:.4f} {cp2_y:.4f} {end_x:.4f} {end_y:.4f} c".encode())

                # Right edge to bottom-right corner
                content_lines.append(f"{x1:.4f} {y0 + r:.4f} l".encode())

                # Bottom-right corner
                cp1_x = x1
                cp1_y = y0 + r - r * kappa
                cp2_x = x1 - r + r * kappa
                cp2_y = y0
                end_x = x1 - r
                end_y = y0
                content_lines.append(f"{cp1_x:.4f} {cp1_y:.4f} {cp2_x:.4f} {cp2_y:.4f} {end_x:.4f} {end_y:.4f} c".encode())

                # Bottom edge to bottom-left corner
                content_lines.append(f"{x0 + r:.4f} {y0:.4f} l".encode())

                # Bottom-left corner
                cp1_x = x0 + r - r * kappa
                cp1_y = y0
                cp2_x = x0
                cp2_y = y0 + r - r * kappa
                end_x = x0
                end_y = y0 + r
                content_lines.append(f"{cp1_x:.4f} {cp1_y:.4f} {cp2_x:.4f} {cp2_y:.4f} {end_x:.4f} {end_y:.4f} c".encode())

                # Left edge to top-left corner
                content_lines.append(f"{x0:.4f} {y1 - r:.4f} l".encode())

                # Top-left corner
                cp1_x = x0
                cp1_y = y1 - r + r * kappa
                cp2_x = x0 + r - r * kappa
                cp2_y = y1
                end_x = x0 + r
                end_y = y1
                content_lines.append(f"{cp1_x:.4f} {cp1_y:.4f} {cp2_x:.4f} {cp2_y:.4f} {end_x:.4f} {end_y:.4f} c".encode())

                content_lines.append(b"S")  # Stroke path (capital S)
                content_lines.append(b"Q")  # Restore state

                logger.debug(f"Added kiss-cut border at ({x_pt:.2f}, {y_pt:.2f}) {w_pt:.2f}x{h_pt:.2f}pt")

            except Exception as e:
                logger.exception(f"Failed to add kiss-cut border for item: {e}")
                continue

        # Append to existing page content
        if pikepdf.Name.Contents in page:
            existing_content = page.Contents.read_bytes()
            new_content = existing_content + b"\n" + b"\n".join(content_lines) + b"\n"
            page.Contents = pikepdf.Stream(pdf, new_content)
        else:
            page.Contents = pikepdf.Stream(pdf, b"\n".join(content_lines))

        # Save and close
        pdf.save(pdf_path)
        pdf.close()

        logger.info(f"Added {len(border_items)} kiss-cut borders with spot color '{spot_color_name}'")

    def save_last_render_as_png(self, path: str) -> None:
        try:
            if getattr(self, "_last_render_image", None) is None:
                raise RuntimeError("No last render image available for PNG export")
            # Ensure 8-bit per channel RGBA
            img = self._last_render_image
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            try:
                dpi = int(getattr(self, "_last_render_dpi", 300) or 300)
            except Exception:
                dpi = 300
            img.save(path, format="PNG", dpi=(dpi, dpi))
        except Exception as e:
            logger.exception(f"Failed to save PNG: {e}")
            raise

    def save_last_render_as_jpg(self, path: str, quality: int = 95) -> None:
        try:
            if getattr(self, "_last_render_image", None) is None:
                raise RuntimeError("No last render image available for JPG export")
            img = self._last_render_image
            if img.mode != "RGB":
                # Flatten alpha over white
                if img.mode == "RGBA":
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else:
                    img = img.convert("RGB")
            try:
                dpi = int(getattr(self, "_last_render_dpi", 300) or 300)
            except Exception:
                dpi = 300
            img.save(
                path,
                format="JPEG",
                quality=max(1, min(100, int(quality))),
                dpi=(dpi, dpi),
                subsampling=0,
                optimize=True,
            )
        except Exception as e:
            logger.exception(f"Failed to save JPG: {e}")
            raise

    def save_last_render_as_bmp(self, path: str) -> None:
        try:
            if getattr(self, "_last_render_image", None) is None:
                raise RuntimeError("No last render image available for BMP export")
            img = self._last_render_image
            if img.mode != "RGB":
                if img.mode == "RGBA":
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else:
                    img = img.convert("RGB")
            try:
                dpi = int(getattr(self, "_last_render_dpi", 300) or 300)
            except Exception:
                dpi = 300
            img.save(path, format="BMP", dpi=(dpi, dpi))
        except Exception as e:
            logger.exception(f"Failed to save BMP: {e}")
            raise
        
        # out_rgb.save(path, "PDF", resolution=dpi)
        
        
    def render_jig_to_svg(
        self,
        path: str,
        items: list[dict],
        jig_w_mm: float,
        jig_h_mm: float,
    ) -> None:
        """Render only the jig outline and slot rectangles to an SVG (units in mm).

        - The SVG uses millimeters for width/height and viewBox in mm coordinates
        - Draws outer jig rectangle from (0,0) to (jig_w_mm, jig_h_mm)
        - Draws every item with type == "slot" as a rectangle at (x_mm,y_mm,w_mm,h_mm)
        - No fills, only strokes suitable for laser cutting
        """
        w_mm = float(jig_w_mm)
        h_mm = float(jig_h_mm)

        def f(num: float) -> str:
            try:
                return f"{float(num):.3f}"
            except Exception:
                return "0"

        lines: list[str] = []
        lines.append("<?xml version='1.0' encoding='UTF-8'?>")
        lines.append(
            (
                "<svg xmlns='http://www.w3.org/2000/svg' "
                f"width='{f(w_mm)}mm' height='{f(h_mm)}mm' viewBox='0 0 {f(w_mm)} {f(h_mm)}' "
                "stroke='#000000' fill='none'>"
            )
        )
        # Outer jig rectangle
        lines.append(
            (
                f"<rect x='0' y='0' width='{f(w_mm)}' height='{f(h_mm)}' stroke-width='0.600'/>"
            )
        )

        # Slot rectangles
        for it in items:
            typ = str(it.get("type", ""))
            if typ != "slot":
                continue
            try:
                x = float(it.get("x_mm", 0.0))
                y = float(it.get("y_mm", 0.0))
                sw = float(it.get("w_mm", 0.0))
                sh = float(it.get("h_mm", 0.0))
            except Exception:
                x, y, sw, sh = 0.0, 0.0, 0.0, 0.0
            lines.append(
                (
                    f"<rect x='{f(x)}' y='{f(y)}' width='{f(sw)}' height='{f(sh)}' stroke-width='0.300'/>"
                )
            )

        lines.append("</svg>")

        try:
            with open(path, "w", encoding="utf-8") as fp:
                fp.write("\n".join(lines))
        except Exception as e:
            logger.exception(f"Failed to write jig SVG: {e}")

    def render_single_pattern_svg(self, path: str, slot_entry: dict) -> None:
        """Render a single slot and outlines of objects inside it to an SVG.

        The SVG canvas is the slot bounds sized in millimeters. All coordinates
        are translated so the slot's top-left is (0,0).

        - Slot outline: black stroke
        - Image objects: draw axis-aligned rectangle of their rotated bounds
        - Text rectangles (green blocks): draw rotated rectangle outline in green
        - Plain text labels are ignored
        """
        try:
            sx = float(slot_entry.get("x_mm", 0.0))
            sy = float(slot_entry.get("y_mm", 0.0))
            sw = float(slot_entry.get("w_mm", 0.0))
            sh = float(slot_entry.get("h_mm", 0.0))
        except Exception:
            sx, sy, sw, sh = 0.0, 0.0, 0.0, 0.0

        def f(num: float) -> str:
            try:
                return f"{float(num):.3f}"
            except Exception:
                return "0"

        lines: list[str] = []
        lines.append("<?xml version='1.0' encoding='UTF-8'?>")
        lines.append(
            (
                "<svg xmlns='http://www.w3.org/2000/svg' "
                f"width='{f(sw)}mm' height='{f(sh)}mm' viewBox='0 0 {f(sw)} {f(sh)}' "
                "fill='none'>"
            )
        )
        # Slot outline
        lines.append(f"<rect x='0' y='0' width='{f(sw)}' height='{f(sh)}' stroke='#808080' stroke-width='0.300'/>")

        # Draw objects
        for obj in list(slot_entry.get("objects", [])):
            typ = str(obj.get("type", ""))
            # Text rectangles were encoded as type 'text' but have w_mm/h_mm
            has_block_size = ("w_mm" in obj) and ("h_mm" in obj)
            if typ == "image":
                try:
                    w_mm = float(obj.get("w_mm", 0.0))
                    h_mm = float(obj.get("h_mm", 0.0))
                    ang = float(obj.get("angle", 0.0) or 0.0)
                    x_mm = float(obj.get("x_mm", 0.0))
                    y_mm = float(obj.get("y_mm", 0.0))
                except Exception:
                    w_mm, h_mm, ang, x_mm, y_mm = 0.0, 0.0, 0.0, 0.0, 0.0
                # rotated bounds rectangle
                try:
                    bw_mm, bh_mm = self.s._rotated_bounds_mm(float(w_mm), float(h_mm), float(ang))
                except Exception:
                    bw_mm, bh_mm = float(w_mm), float(h_mm)
                left_mm = x_mm + (w_mm - bw_mm) / 2.0 - sx
                top_mm = y_mm + (h_mm - bh_mm) / 2.0 - sy
                lines.append(
                    f"<rect x='{f(left_mm)}' y='{f(top_mm)}' width='{f(bw_mm)}' height='{f(bh_mm)}' stroke='#000000' stroke-width='0.300'/>"
                )
            elif typ == "text" and has_block_size:
                # Green text block rectangle, possibly rotated
                try:
                    w_mm = float(obj.get("w_mm", 0.0))
                    h_mm = float(obj.get("h_mm", 0.0))
                    ang = float(obj.get("angle", 0.0) or 0.0)
                    x_mm = float(obj.get("x_mm", 0.0))
                    y_mm = float(obj.get("y_mm", 0.0))
                except Exception:
                    w_mm, h_mm, ang, x_mm, y_mm = 0.0, 0.0, 0.0, 0.0, 0.0
                # compute rotated rectangle polygon points around center
                cx = (x_mm - sx) + w_mm / 2.0
                cy = (y_mm - sy) + h_mm / 2.0
                a = 0.0
                try:
                    a = -float(ang) * 3.141592653589793 / 180.0
                except Exception:
                    a = 0.0
                ca = math.cos(a)
                sa = math.sin(a)
                half_w = w_mm / 2.0
                half_h = h_mm / 2.0
                corners = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
                pts: list[str] = []
                for (dx, dy) in corners:
                    rx = dx * ca - dy * sa
                    ry = dx * sa + dy * ca
                    px = cx + rx
                    py = cy + ry
                    pts.append(f(f(px)))
                    pts.append(f(f(py)))
                lines.append(
                    f"<polygon points='{" ".join(pts)}' stroke='#17a24b' stroke-width='0.300' fill='none'/>"
                )
            else:
                # ignore plain text labels or unknowns
                continue

        lines.append("</svg>")

        try:
            with open(path, "w", encoding="utf-8") as fp:
                fp.write("\n".join(lines))
        except Exception as e:
            logger.exception(f"Failed to write single pattern SVG: {e}")