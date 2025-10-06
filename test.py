from __future__ import annotations
from typing import List, Tuple, Optional
from io import BytesIO
import os
import functools
import urllib.request
from PIL import Image, ImageDraw, ImageFont
import emoji


TWEMOJI_PNG_DIR: Optional[str] = None
TWEMOJI_CDN = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"


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


if __name__ == "__main__":
    font = ImageFont.truetype("C:/Users/vboxuser/Desktop/zyntra/zyntra1.0/_internal/fonts/MyriadPro-Regular.ttf", 48)
    text = "Allosty🤍 Hello 😄😎  🇺🇦🇯🇵  test"

    mw, mh = measure_text_with_emojis(text, font, emoji_scale=1.0)
    print("measure:", mw, mh)

    canvas = Image.new("RGBA", (mw + 40, mh + 40), (255, 255, 255, 0))
    draw_text_with_emojis(canvas, (20, 20), text, font, fill=(0, 0, 0, 255), emoji_scale=1.0)
    canvas.save("out.png")

    rw, rh = measure_rotated_text_with_emojis(text, font, 20.0, emoji_scale=1.0)
    print("rotated measure:", rw, rh)

    tmp = Image.new("RGBA", (mw + 20, mh + 20), (0, 0, 0, 0))
    draw_text_with_emojis(tmp, (10, 10), text, font, fill=(0, 0, 0, 255), emoji_scale=1.0)
    try:
        tmp = tmp.rotate(20.0, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    except Exception:
        tmp = tmp.rotate(20.0, expand=True)
    bbox = tmp.getbbox()
    if bbox:
        tmp = tmp.crop(bbox)

    canvas2 = Image.new("RGBA", (rw + 40, rh + 40), (255, 255, 255, 0))
    canvas2.alpha_composite(tmp, dest=(20, 20))
    canvas2.show()
