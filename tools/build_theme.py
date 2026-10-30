#!/usr/bin/env python3
"""
Build iOS "Liquid Glass" style themes for Fcitx5 for Android.

Output is a zip that can be imported from
  Fcitx5 设置 -> 主题 -> 右上角 "+" -> 导入
The zip layout and JSON schema follow fcitx5-android's
ThemeFilesManager / CustomThemeSerializer (theme version 2.1).

Usage:
  python3 tools/build_theme.py                       # build built-in light/dark variants
  python3 tools/build_theme.py --wallpaper my.jpg    # build glass themes from your own wallpaper
"""

import argparse
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PREVIEW = ROOT / "preview"

# keyboard background size (stretched to fit the keyboard area by the app)
BG_W, BG_H = 1080, 1000

IOS_BLUE = 0xFF0A84FF


def argb(v: int) -> int:
    """0xAARRGGBB -> signed 32-bit int, which is how the app stores colors."""
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


# Colors are 0xAARRGGBB. Translucent key colors are drawn on top of the
# frosted background image, which is what gives the glass look.
PALETTES = {
    "LiquidGlassLight": dict(
        isDark=False,
        backgroundColor=0xFFE8EBF1,
        barColor=0x00FFFFFF,
        keyboardColor=0xFFE8EBF1,
        keyBackgroundColor=0x99FFFFFF,
        keyTextColor=0xFF1C1C1E,
        candidateTextColor=0xFF1C1C1E,
        candidateLabelColor=0xFF3A3A3C,
        candidateCommentColor=0x993C3C43,
        altKeyBackgroundColor=0x59AEB5C2,
        altKeyTextColor=0xFF1C1C1E,
        accentKeyBackgroundColor=IOS_BLUE,
        accentKeyTextColor=0xFFFFFFFF,
        keyPressHighlightColor=0x1F000000,
        keyShadowColor=0xB3FFFFFF,  # used as the bright glass rim with "key border stroke"
        popupBackgroundColor=0xF2FAFAFC,
        popupTextColor=0xFF000000,
        spaceBarColor=0x99FFFFFF,
        dividerColor=0x1F3C3C43,
        clipboardEntryColor=0x99FFFFFF,
        genericActiveBackgroundColor=IOS_BLUE,
        genericActiveForegroundColor=0xFFFFFFFF,
    ),
    "LiquidGlassDark": dict(
        isDark=True,
        backgroundColor=0xFF1C1C1E,
        barColor=0x00000000,
        keyboardColor=0xFF1C1C1E,
        keyBackgroundColor=0x38FFFFFF,
        keyTextColor=0xFFF5F5F7,
        candidateTextColor=0xFFF5F5F7,
        candidateLabelColor=0xFFD1D1D6,
        candidateCommentColor=0x99EBEBF5,
        altKeyBackgroundColor=0x1AFFFFFF,
        altKeyTextColor=0xFFF5F5F7,
        accentKeyBackgroundColor=IOS_BLUE,
        accentKeyTextColor=0xFFFFFFFF,
        keyPressHighlightColor=0x29FFFFFF,
        keyShadowColor=0x47FFFFFF,
        popupBackgroundColor=0xF23A3A3C,
        popupTextColor=0xFFFFFFFF,
        spaceBarColor=0x38FFFFFF,
        dividerColor=0x29FFFFFF,
        clipboardEntryColor=0x38FFFFFF,
        genericActiveBackgroundColor=IOS_BLUE,
        genericActiveForegroundColor=0xFFFFFFFF,
    ),
}

# soft color blobs behind the glass: (x, y, radius, rgb) in relative units
BLOBS = {
    False: ((0.10, 0.15, 0.55, (176, 214, 255)), (0.85, 0.20, 0.50, (255, 214, 236)),
            (0.55, 0.90, 0.60, (214, 236, 255)), (0.20, 0.85, 0.45, (232, 222, 255))),
    True: ((0.10, 0.20, 0.55, (38, 64, 112)), (0.85, 0.15, 0.50, (86, 44, 92)),
           (0.55, 0.95, 0.60, (24, 52, 84)), (0.20, 0.85, 0.45, (58, 42, 96))),
}
BASE = {False: (232, 235, 241), True: (24, 24, 28)}


def make_noise(w, h, amount, seed=7):
    rng = np.random.default_rng(seed)
    return rng.normal(0, amount, (h, w, 1))


def glassify(img: Image.Image, dark: bool) -> Image.Image:
    """Turn any image into a frosted, slightly refractive glass backdrop."""
    img = img.convert("RGB")
    # cover-crop to keyboard aspect
    scale = max(BG_W / img.width, BG_H / img.height)
    img = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - BG_W) // 2, (img.height - BG_H) // 2
    img = img.crop((left, top, left + BG_W, top + BG_H))

    # heavy blur = frosted glass
    img = img.filter(ImageFilter.GaussianBlur(60))
    a = np.asarray(img).astype(np.float32)

    # boost saturation a bit (iOS materials are vibrant), then wash with white/black
    gray = a.mean(axis=2, keepdims=True)
    a = gray + (a - gray) * 1.35
    tint, strength = ((20, 20, 24), 0.55) if dark else ((246, 247, 250), 0.50)
    a = a * (1 - strength) + np.array(tint, np.float32) * strength

    # top specular sheen + gentle bottom vignette, like light through a lens
    y = np.linspace(0, 1, BG_H, dtype=np.float32)[:, None, None]
    sheen = np.exp(-((y - 0.0) / 0.10) ** 2) * (28 if not dark else 18)
    vignette = (y ** 2) * (10 if not dark else 14)
    a = a + sheen - vignette

    # subtle grain so banding doesn't show on AMOLED panels
    a = a + make_noise(BG_W, BG_H, 1.6)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    # thin bright edge at the very top: the "liquid" rim of the glass panel
    d = ImageDraw.Draw(out, "RGBA")
    d.line([(0, 1), (BG_W, 1)], fill=(255, 255, 255, 150 if not dark else 70), width=3)
    return out


def default_backdrop(dark: bool) -> Image.Image:
    a = np.zeros((BG_H, BG_W, 3), np.float32) + np.array(BASE[dark], np.float32)
    yy, xx = np.mgrid[0:BG_H, 0:BG_W].astype(np.float32)
    for bx, by, br, rgb in BLOBS[dark]:
        dist = np.hypot(xx / BG_W - bx, (yy / BG_H - by) * BG_H / BG_W)
        w = np.exp(-(dist / br) ** 2 * 3)[..., None]
        a = a * (1 - w) + np.array(rgb, np.float32) * w
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def crisp_backdrop(dark: bool, w: int = BG_W, h: int = BG_H) -> Image.Image:
    """A vivid backdrop with *crisp* shapes. Heavily blurred backgrounds give a lens nothing to bend,
    so the glass keys of the refraction mode need edges to refract."""
    if dark:
        base, blobs = (16, 18, 44), ((0.1, 0.1, 0.9, (70, 52, 200)), (0.95, 0.5, 0.8, (200, 40, 120)),
                                      (0.3, 0.95, 0.8, (0, 120, 220)))
        shapes = [("disc", 0.18, 0.30, 0.17, (255, 80, 140), (255, 160, 90)),
                  ("disc", 0.74, 0.20, 0.13, (80, 220, 255), (60, 120, 255)),
                  ("ring", 0.52, 0.62, 0.20, (255, 214, 10), None),
                  ("disc", 0.88, 0.78, 0.16, (120, 255, 190), (30, 200, 160)),
                  ("band", 0.0, 0.0, 0.0, (170, 110, 255), (90, 60, 220))]
    else:
        base, blobs = (238, 241, 252), ((0.1, 0.1, 0.9, (150, 190, 255)), (0.95, 0.5, 0.8, (255, 170, 205)),
                                         (0.3, 0.95, 0.8, (140, 225, 255)))
        shapes = [("disc", 0.18, 0.30, 0.17, (255, 94, 140), (255, 170, 100)),
                  ("disc", 0.74, 0.20, 0.13, (60, 200, 255), (60, 120, 255)),
                  ("ring", 0.52, 0.62, 0.20, (255, 196, 0), None),
                  ("disc", 0.88, 0.78, 0.16, (80, 230, 170), (20, 190, 150)),
                  ("band", 0.0, 0.0, 0.0, (160, 110, 255), (100, 70, 230))]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.zeros((h, w, 3), np.float32) + np.array(base, np.float32)
    for bx, by, br, rgb in blobs:
        d = np.hypot(xx - bx * w, yy - by * h) / (br * w)
        wgt = np.clip(1 - d, 0, 1) ** 1.6
        a = a * (1 - wgt[..., None]) + np.array(rgb, np.float32) * wgt[..., None]
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    S = 3  # draw shapes supersampled for clean edges
    big = Image.new("RGBA", (w * S, h * S))
    for kind, cx, cy, rr, c0, c1 in shapes:
        layer = Image.new("RGBA", big.size)
        m = Image.new("L", big.size, 0)
        md = ImageDraw.Draw(m)
        R = rr * w * S
        if kind == "disc":
            md.ellipse((cx * w * S - R, cy * h * S - R, cx * w * S + R, cy * h * S + R), fill=255)
        elif kind == "ring":
            md.ellipse((cx * w * S - R, cy * h * S - R, cx * w * S + R, cy * h * S + R), fill=255)
            r2 = R * 0.62
            md.ellipse((cx * w * S - r2, cy * h * S - r2, cx * w * S + r2, cy * h * S + r2), fill=0)
        else:  # diagonal ribbon
            md.polygon([(0, 0.78 * h * S), (w * S, 0.34 * h * S), (w * S, 0.46 * h * S), (0, 0.90 * h * S)], fill=255)
        if c1 is None:
            col = Image.new("RGBA", big.size, c0 + (255,))
        else:  # vertical gradient fill
            t = np.linspace(0, 1, big.size[1], dtype=np.float32)[:, None, None]
            g = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
            col = Image.fromarray(np.repeat(g, big.size[0], axis=1).astype(np.uint8)).convert("RGBA")
        layer.paste(col, (0, 0), m)
        big.alpha_composite(layer)
    # thin bright lines: they make the bending of the lens easy to see
    ld = ImageDraw.Draw(big, "RGBA")
    for i in range(1, 7):
        y = int(h * S * (0.12 + i * 0.14))
        ld.line([(0, y), (w * S, y - int(0.10 * h * S))], fill=(255, 255, 255, 90 if not dark else 70), width=3 * S)
    shapes_img = big.resize((w, h), Image.LANCZOS)
    img = img.convert("RGBA")
    img.alpha_composite(shapes_img)
    return img.convert("RGB")


def theme_json(name: str, palette: dict, cropped: str, src: str) -> dict:
    p = dict(palette)
    is_dark = p.pop("isDark")
    data = {
        "name": name,
        "isDark": is_dark,
        "backgroundImage": {
            "croppedFilePath": cropped,
            "srcFilePath": src,
            "brightness": 100,  # the image is already toned, don't darken it
            "cropRect": None,
            "cropRotation": 0,
        },
    }
    data.update({k: argb(v) for k, v in p.items()})
    data["version"] = "2.1"
    return data


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def write_zip(name: str, data: dict, bg: Image.Image) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{name}.zip"
    raw = png_bytes(bg)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for entry, payload in (
            (data["backgroundImage"]["croppedFilePath"], raw),
            (data["backgroundImage"]["srcFilePath"], raw),
            (f"{name}.json", json.dumps(data, ensure_ascii=False, indent=2).encode()),
        ):
            info = zipfile.ZipInfo(entry, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, payload)
    return out


# ---------------------------------------------------------------- preview

def rgba(v: int):
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255, (v >> 24) & 255)


def find_font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def keyboard_layer(palette: dict, W: int = BG_W, H: int = 860) -> Image.Image:
    """Transparent RGBA layer with candidate bar and keys, as the app draws them
    (key border + stroke on, radius 12dp)."""
    layer = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(layer)
    font, small = find_font(44), find_font(30)

    # candidate bar
    bar_h = 120
    for i, word in enumerate(("Liquid", "Glass", "glassy", "glance")):
        d.text((40 + i * 230, bar_h // 2), word, font=font, anchor="lm",
               fill=rgba(palette["candidateTextColor"]))
    d.line([(0, bar_h), (W, bar_h)], fill=rgba(palette["dividerColor"]), width=2)

    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    m, top, rh = 8, bar_h + 16, 170
    kw = (W - 2 * m) / 10
    r = 30

    def key(x0, y0, x1, y1, fill, label, color, f=font):
        box = (x0 + 6, y0 + 10, x1 - 6, y1 - 10)
        d.rounded_rectangle(box, r, fill=rgba(fill), outline=rgba(palette["keyShadowColor"]), width=3)
        d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, font=f, anchor="mm",
               fill=rgba(color))

    kb, kt = palette["keyBackgroundColor"], palette["keyTextColor"]
    ab, at = palette["altKeyBackgroundColor"], palette["altKeyTextColor"]
    for ri, row in enumerate(rows):
        y = top + ri * rh
        if ri == 2:
            key(m, y, m + kw * 1.5, y + rh, ab, "⇧", at)
            x = m + kw * 1.5
            for ch in row:
                key(x, y, x + kw, y + rh, kb, ch, kt)
                x += kw
            key(x, y, W - m, y + rh, ab, "⌫", at)
        else:
            x = m + (W - 2 * m - kw * len(row)) / 2
            for ch in row:
                key(x, y, x + kw, y + rh, kb, ch, kt)
                x += kw
    y = top + 3 * rh
    key(m, y, m + kw * 1.5, y + rh, ab, "123", at, small)
    key(m + kw * 1.5, y, m + kw * 2.5, y + rh, ab, ",", at)
    key(m + kw * 2.5, y, m + kw * 7, y + rh, palette["spaceBarColor"], "space", kt, small)
    key(m + kw * 7, y, m + kw * 8, y + rh, ab, ".", at)
    key(m + kw * 8, y, W - m, y + rh, palette["accentKeyBackgroundColor"], "return",
        palette["accentKeyTextColor"], small)

    return layer


def render_preview(name: str, palette: dict, bg: Image.Image) -> Path:
    W, H = BG_W, 860
    canvas = bg.resize((W, H)).convert("RGBA")
    canvas = Image.alpha_composite(canvas, keyboard_layer(palette, W, H)).convert("RGB")
    PREVIEW.mkdir(exist_ok=True)
    out = PREVIEW / f"{name}.png"
    canvas.save(out, optimize=True)
    return out


def build(name: str, palette: dict, bg: Image.Image):
    data = theme_json(name, palette, f"{name}-cropped.png", f"{name}-src")
    print("built", write_zip(name, data, bg).relative_to(ROOT),
          "/", render_preview(name, palette, bg).relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wallpaper", type=Path, help="build glass themes from this image instead")
    ap.add_argument("--name", default="LiquidGlassWallpaper", help="theme name prefix for --wallpaper")
    args = ap.parse_args()

    if args.wallpaper:
        src = Image.open(args.wallpaper)
        for suffix, base in (("Light", "LiquidGlassLight"), ("Dark", "LiquidGlassDark")):
            build(args.name + suffix, PALETTES[base], glassify(src, PALETTES[base]["isDark"]))
        return

    for name, palette in PALETTES.items():
        dark = palette["isDark"]
        build(name, palette, glassify(default_backdrop(dark), dark))
        # same colors on a backdrop with crisp shapes, for the glass refraction mode of the patched app
        build(name.replace("LiquidGlass", "LiquidGlassCrystal"), palette, crisp_backdrop(dark))


if __name__ == "__main__":
    main()
