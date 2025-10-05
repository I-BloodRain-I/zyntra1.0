from __future__ import annotations

import os
import logging
from typing import List

import math
import arabic_reshaper
from bidi.algorithm import get_display

from src.core import MM_TO_PX
from src.core.state import FONTS_PATH, PRODUCTS_PATH
from src.utils import svg_to_png


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
        dpi: int = 300
    ) -> None:
        """Render a scene (slots + items) into a single-page PDF (jig == page)."""
        try:
            from PIL import Image as _PIL_Image  # type: ignore
            from PIL import ImageDraw as _PIL_Draw  # type: ignore
            from PIL import ImageFont as _PIL_Font  # type: ignore
        except Exception as e:
            raise RuntimeError("Pillow (PIL) is required to export PDF.") from e

        import os

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
            try:
                s = str(hex_str or "").strip()
                if s.startswith("#") and len(s) == 7:
                    r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
                    return (r, g, b, 255)
            except Exception:
                raise
            return default

        def _draw_rotated_text_center(
            text: str,
            center_x: int,
            center_y: int,
            font,
            fill: tuple[int, int, int, int],
            angle_deg: float,
        ) -> None:
            reshaped_text = arabic_reshaper.reshape(text)
            text = get_display(reshaped_text)
            # Measure text bbox to create tight canvas
            bb = draw.textbbox((0, 0), text, font=font)
            tw = max(1, bb[2] - bb[0])
            th = max(1, bb[3] - bb[1])
            temp_img = _PIL_Image.new("RGBA", (int(tw), int(th)), (0, 0, 0, 0))
            temp_draw = _PIL_Draw.Draw(temp_img, "RGBA")
            # Shift by -bb[0], -bb[1] to neutralize baseline offsets
            temp_draw.text((-bb[0], -bb[1]), text, font=font, fill=fill)
            if abs(float(angle_deg)) > 1e-6:
                try:
                    temp_img = temp_img.rotate(float(angle_deg), expand=True, resample=_PIL_Image.BICUBIC, fillcolor=(0, 0, 0, 0))
                except Exception:
                    temp_img = temp_img.rotate(float(angle_deg), expand=True)
            left = int(round(center_x - temp_img.width / 2.0))
            top = int(round(center_y - temp_img.height / 2.0))
            try:
                img.alpha_composite(temp_img, (left, top))
            except Exception:
                img.paste(temp_img, (left, top), temp_img.split()[-1])

        def _measure_rotated_text_size_px(text: str, font, angle_deg: float) -> tuple[int, int]:
            """Measure rendered (rotated) text raster size in pixels.

            Uses same shaping and drawing logic as _draw_rotated_text_center.
            """
            reshaped_text = arabic_reshaper.reshape(text)
            text_disp = get_display(reshaped_text)
            bb = draw.textbbox((0, 0), text_disp, font=font)
            tw = max(1, bb[2] - bb[0])
            th = max(1, bb[3] - bb[1])
            tmp = _PIL_Image.new("RGBA", (int(tw), int(th)), (0, 0, 0, 0))
            td = _PIL_Draw.Draw(tmp, "RGBA")
            td.text((-bb[0], -bb[1]), text_disp, font=font, fill=(0, 0, 0, 255))
            if abs(float(angle_deg)) > 1e-6:
                try:
                    tmp = tmp.rotate(float(angle_deg), expand=True, resample=_PIL_Image.BICUBIC, fillcolor=(0, 0, 0, 0))
                except Exception:
                    tmp = tmp.rotate(float(angle_deg), expand=True)
            return int(tmp.width), int(tmp.height)

        def _fit_font_to_block(text: str, family: str, initial_size_px: int, max_w_px: int, max_h_px: int, angle_deg: float):
            """Return a truetype font scaled down so rotated text fits within max_w_px x max_h_px."""
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

        # Рамка «джига»
        jw = max(1, int(round(jig_w_mm * px_per_mm)))
        jh = max(1, int(round(jig_h_mm * px_per_mm)))
        jx0 = 0
        jy0 = 0
        jx1 = page_w_px - 1
        jy1 = page_h_px - 1
        draw.rectangle([jx0, jy0, jx1, jy1], outline=(221, 221, 221, 255), width=3)

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
                        _draw_rotated_text_center(label, int(cx), int(cy), fnt, col, ang)

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

                        im_resized = im.resize((int(w_px), int(h_px)), _PIL_Image.LANCZOS)
                        # Apply window-based mask composition (same as canvas & orders)
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
                                        im_resized = self.s.images._apply_mask_window_compose(im_resized, mabs, int(w_px), int(h_px))
                                    except Exception:
                                        logger.exception("Failed applying window-based mask for PDF render")
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

                    except Exception as e:
                        logger.exception(f"Failed to render image in PDF: {e}")

                elif typ == "text":
                    # Handle both plain text items and text blocks inside slots
                    try:
                        ang = float(it.get("angle", 0.0) or 0.0)
                    except Exception:
                        ang = 0.0
                        raise

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
                        _draw_rotated_text_center(txt, int(cx), int(cy), fnt, col, ang)
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
                        _draw_rotated_text_center(txt, int(cx), int(cy), fnt, col, ang)

        # «Сплющивание» на белый фон и сохранение в PDF
        out_rgb = _PIL_Image.new("RGB", (page_w_px, page_h_px), "white")
        # используем альфа-канал итогового холста как маску
        alpha = img.split()[-1]
        out_rgb.paste(img.convert("RGB"), mask=alpha)
        # out_rgb.save(f"output_{path.split('\\')[-1].split('.')[0]}.png", "png")
        out_rgb.save(path, "PDF", resolution=dpi)
        
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