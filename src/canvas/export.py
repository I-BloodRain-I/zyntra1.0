from __future__ import annotations

import os
import logging
from typing import List

from src.core import MM_TO_PX
from src.core.state import FONTS_PATH
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
        print("items", items)

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
                        W = max(1, r - l)
                        H = max(1, btm - top)
                        lo, hi = 1, H
                        best_font = None
                        best_bbox = None
                        font_path = FONTS_PATH / "MyriadPro-Regular.ttf"
                        while lo <= hi:
                            mid = (lo + hi) // 2
                            f = _PIL_Font.truetype(font_path, mid)
                            bb = draw.textbbox((0, 0), label, font=f)
                            tw = bb[2] - bb[0]
                            th = bb[3] - bb[1]
                            if tw <= W and th <= H:
                                best_font, best_bbox = f, bb
                                lo = mid + 1
                            else:
                                hi = mid - 1
                        if best_font is None:
                            best_font = _PIL_Font.truetype(font_path, H)
                            best_bbox = draw.textbbox((0, 0), label, font=best_font)

                        tw = best_bbox[2] - best_bbox[0]
                        th = best_bbox[3] - best_bbox[1]
                        cx = l + W // 2
                        cy = top + H // 2

                        try:
                            ang = float(it.get("angle", 0.0) or 0.0)
                        except Exception:
                            ang = 0.0
                        # здесь мы не вращаем текст (как и у вас), лишь подбираем бокс; логика сохранена
                        x = cx - tw // 2
                        y = cy - th // 2 - best_bbox[1]
                        draw.text((x, y), label, font=best_font, fill=(0, 255, 0, 255))

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
                        if ext == ".svg":
                            im = svg_to_png(str(path_img), width=int(w_px), height=int(h_px), device_pixel_ratio=1.0)
                            # ожидаем RGBA
                            if im.mode != "RGBA":
                                im = im.convert("RGBA")
                        else:
                            im = _PIL_Image.open(path_img).convert("RGBA")

                        im_resized = im.resize((int(w_px), int(h_px)), _PIL_Image.LANCZOS)
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
                    txt = str(it.get("text", ""))
                    fill_hex = str(it.get("fill", "#17a24b"))
                    if fill_hex.startswith("#") and len(fill_hex) == 7:
                        r = int(fill_hex[1:3], 16); g = int(fill_hex[3:5], 16); b = int(fill_hex[5:7], 16)
                        col = (r, g, b, 255)
                    else:
                        col = (23, 162, 75, 255)
                    cx = jx0 + mm_to_px(it.get("x_mm", 0.0))
                    cy = jy0 + mm_to_px(it.get("y_mm", 0.0))
                    if font_small is not None and txt:
                        bbox = draw.textbbox((0, 0), txt, font=font_small)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        draw.text((int(cx - tw / 2), int(cy - th / 2)), txt, fill=col, font=font_small)

        # «Сплющивание» на белый фон и сохранение в PDF
        out_rgb = _PIL_Image.new("RGB", (page_w_px, page_h_px), "white")
        # используем альфа-канал итогового холста как маску
        alpha = img.split()[-1]
        out_rgb.paste(img.convert("RGB"), mask=alpha)
        out_rgb.save(path, "PDF", resolution=dpi)
