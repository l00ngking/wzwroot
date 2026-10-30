#!/usr/bin/env python3
"""
Simulated rendering of the real-time glass blur patch (patches/0001), NOT a device screenshot.

A mock edge-to-edge app is drawn so that content runs behind the keyboard, then the keyboard
region is rendered twice:
  - before: the static frosted background that ships inside the theme zip
  - after:  a Gaussian blur of what is behind the keyboard + the tint GlassBackdrop applies
            (theme.keyboardColor at alpha 0x99 / 0x8C and a 1dp white rim on top)
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_theme as bt  # noqa: E402

W, H = 1080, 2100
KB_H = 860
KB_Y = H - KB_H
BLUR_SIGMA = 38  # ~24dp blur radius on a 420dpi screen

CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def font(size):
    for f in (CJK, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


PHOTOS = [  # (top color, bottom color)
    ((255, 138, 101), (255, 64, 129)), ((79, 195, 247), (41, 98, 255)),
    ((129, 199, 132), (0, 150, 136)), ((255, 213, 79), (255, 112, 67)),
    ((186, 104, 200), (92, 107, 192)), ((77, 182, 172), (38, 198, 218)),
    ((255, 171, 145), (239, 83, 80)), ((144, 202, 249), (126, 87, 194)),
]


def gradient(w, h, c0, c1):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    a = np.repeat(a, w, axis=1)
    return Image.fromarray(a.astype(np.uint8))


def mock_app(dark: bool) -> Image.Image:
    """A photo-feed app drawn edge to edge: its content continues behind the keyboard."""
    bg = (18, 18, 20) if dark else (246, 247, 250)
    fg = (240, 240, 245) if dark else (28, 28, 30)
    sub = (150, 150, 160) if dark else (120, 120, 130)
    card = (34, 34, 38) if dark else (255, 255, 255)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    # status + app bar
    d.text((48, 40), "9:41", font=font(36), fill=fg)
    d.text((48, 110), "发现 Discover", font=font(64), fill=fg)

    # feed of cards with photos, continuing all the way to the bottom edge
    y, i = 230, 0
    while y < H:
        cw = (W - 48 * 2 - 32) // 2
        for col in range(2):
            x = 48 + col * (cw + 32)
            ph = 380 if (i + col) % 2 == 0 else 470
            d.rounded_rectangle((x, y, x + cw, y + ph + 130), 40, fill=card)
            c0, c1 = PHOTOS[(i * 2 + col) % len(PHOTOS)]
            photo = gradient(cw - 24, ph - 12, c0, c1)
            mask = Image.new("L", photo.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, *photo.size), 30, fill=255)
            img.paste(photo, (x + 12, y + 12), mask)
            d.ellipse((x + cw - 150, y + ph - 150, x + cw - 40, y + ph - 40), fill=(255, 255, 255))
            d.text((x + 28, y + ph + 22), f"Aurora #{i * 2 + col + 1}", font=font(34), fill=fg)
            d.text((x + 28, y + ph + 72), "2.4k likes", font=font(28), fill=sub)
        y += 600
        i += 1
    return img


def static_background(palette):
    dark = palette["isDark"]
    return bt.glassify(bt.default_backdrop(dark), dark).resize((W, KB_H))


def blurred_backdrop(app: Image.Image, palette) -> Image.Image:
    """What GlassBackdrop produces: blurred content behind the keyboard + tint + 1dp rim."""
    dark = palette["isDark"]
    region = app.crop((0, KB_Y, W, H))
    # blur with the pixels above/below included so the edges don't darken
    pad = BLUR_SIGMA * 3
    ctx = app.crop((0, max(0, KB_Y - pad), W, H)).filter(ImageFilter.GaussianBlur(BLUR_SIGMA))
    region = ctx.crop((0, ctx.height - KB_H, W, ctx.height)).convert("RGBA")
    base = palette["keyboardColor"] & 0x00FFFFFF
    alpha = 0x8C if dark else 0x99
    tint = Image.new("RGBA", region.size, ((base >> 16) & 255, (base >> 8) & 255, base & 255, alpha))
    out = Image.alpha_composite(region, tint)
    rim = Image.new("RGBA", (W, 2), (255, 255, 255, 0x33 if dark else 0x99))
    out.alpha_composite(rim, (0, 0))  # blend; ImageDraw would overwrite the pixels
    return out.convert("RGB")


def compose(app, kb_bg, palette):
    img = app.copy()
    img.paste(kb_bg, (0, KB_Y))
    layer = bt.keyboard_layer(palette, W, KB_H)
    img = img.convert("RGBA")
    img.alpha_composite(layer, (0, KB_Y))
    return img.convert("RGB")


def caption(img, text, sub):
    h = 150
    out = Image.new("RGB", (img.width, img.height + h), (24, 24, 27))
    out.paste(img, (0, h))
    d = ImageDraw.Draw(out)
    d.text((img.width // 2, 52), text, font=font(54), fill=(255, 255, 255), anchor="mm")
    d.text((img.width // 2, 110), sub, font=font(34), fill=(170, 170, 180), anchor="mm")
    return out


def main():
    out_dir = Path(__file__).resolve().parent.parent / "preview"
    out_dir.mkdir(exist_ok=True)
    for name in ("LiquidGlassLight", "LiquidGlassDark"):
        palette = bt.PALETTES[name]
        app = mock_app(palette["isDark"])
        before = compose(app, static_background(palette), palette)
        after = compose(app, blurred_backdrop(app, palette), palette)
        a = caption(before, "之前 · 静态毛玻璃背景", "主题 zip 自带的图片,与键盘后面的内容无关")
        b = caption(after, "之后 · 实时模糊", "模糊的是键盘后面真实的内容")
        gap = 40
        sheet = Image.new("RGB", (a.width * 2 + gap, a.height), (24, 24, 27))
        sheet.paste(a, (0, 0))
        sheet.paste(b, (a.width + gap, 0))
        sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
        out = out_dir / f"demo_blur_{name}.png"
        sheet.save(out, optimize=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
