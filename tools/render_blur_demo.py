#!/usr/bin/env python3
"""
Simulated rendering of the "glass" patches (patches/0001 blur backdrop, patches/0003 glass keys).
This is NOT a device screenshot: a mock edge-to-edge chat app is drawn so that its content runs
behind the keyboard, the keyboard region is blurred like GlassBackdrop does, and the keys are
drawn with the same recipe as GlassKeyDrawable (GLASS below mirrors the constants in that class).
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_theme as bt  # noqa: E402

W, H = 1080, 2200
KB_H = 900
KB_Y = H - KB_H
SS = 3  # supersampling for the keys
BLUR_SIGMA = 26  # ~16dp blur radius on a 420dpi screen

# Keep in sync with GlassKeyDrawable.kt
GLASS = {
    False: dict(  # light
        body_top=0.46, body_bottom=0.18,           # alpha of the key color, top -> bottom
        sheen=0.34,                                 # white sheen over the upper half
        rim=(0.95, 0.10, 0.10, 0.60),              # rim alpha at t = 0, .3, .7, 1 along the diagonal
        hairline=0.10,                              # thin dark outline, keeps white keys visible on white
        shadow=0.10,
    ),
    True: dict(  # dark
        body_top=0.26, body_bottom=0.07,
        sheen=0.20,
        rim=(0.80, 0.07, 0.07, 0.42),
        hairline=0.0,
        shadow=0.30,
    ),
}
RIM_WIDTH_DP = 0.9
RIM_POS = (0.0, 0.3, 0.7, 1.0)
DENSITY = 2.6

CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, cjk=False):
    for f in ((CJK, LATIN) if cjk else (LATIN, CJK)):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


# ------------------------------------------------------------------ mock app

def mesh(w, h, blobs, base):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.zeros((h, w, 3), np.float32) + np.array(base, np.float32)
    for bx, by, br, rgb in blobs:
        d = np.hypot(xx - bx * w, yy - by * h) / (br * w)
        wgt = np.clip(1 - d, 0, 1) ** 1.6
        a = a * (1 - wgt[..., None]) + np.array(rgb, np.float32) * wgt[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def mock_app(dark: bool) -> Image.Image:
    """A chat app on a vivid wallpaper; the wallpaper and the last bubbles run behind the keyboard."""
    if dark:
        blobs = [(0.1, 0.12, 0.9, (88, 54, 220)), (0.95, 0.30, 0.8, (210, 40, 120)),
                 (0.2, 0.62, 0.7, (0, 130, 230)), (0.85, 0.80, 0.8, (255, 120, 40)),
                 (0.45, 0.96, 0.7, (20, 190, 150))]
        base = (20, 20, 40)
    else:
        blobs = [(0.1, 0.12, 0.9, (130, 180, 255)), (0.95, 0.30, 0.8, (255, 140, 190)),
                 (0.2, 0.62, 0.7, (110, 220, 255)), (0.85, 0.80, 0.8, (255, 190, 90)),
                 (0.45, 0.96, 0.7, (120, 235, 190))]
        base = (235, 238, 250)
    # draw on an RGB image: ImageDraw only blends translucent fills there, on RGBA it overwrites
    img = mesh(W, H, blobs, base)
    d = ImageDraw.Draw(img, "RGBA")

    fg = (255, 255, 255) if dark else (28, 28, 30)
    d.text((48, 44), "9:41", font=font(36), fill=fg + (255,))
    d.ellipse((48, 130, 136, 218), fill=(255, 255, 255, 230))
    d.text((160, 138), "Aurora", font=font(46, True), fill=fg + (255,))
    d.text((160, 192), "在线 · online", font=font(28, True), fill=fg + (170,))

    them = (255, 255, 255, 215) if not dark else (255, 255, 255, 60)
    me = (10, 132, 255, 255)
    tfg = (28, 28, 30, 255) if not dark else (255, 255, 255, 255)

    def bubble(x, y, w, h, mine, text=None):
        d.rounded_rectangle((x, y, x + w, y + h), 46, fill=me if mine else them)
        if text:
            d.text((x + 36, y + h / 2), text, font=font(40, True), anchor="lm",
                   fill=(255, 255, 255, 255) if mine else tfg)

    bubble(48, 290, 640, 110, False, "今晚看极光吗?")
    bubble(300, 430, 730, 110, True, "走!我带相机")
    # a "photo" bubble with its own colors, so the blur behind the keyboard has structure
    photo = mesh(540, 420, [(0.2, 0.2, 0.9, (255, 94, 98)), (0.9, 0.8, 0.9, (255, 195, 113)),
                            (0.5, 0.5, 0.6, (255, 255, 255))], (255, 153, 102))
    mask = Image.new("L", photo.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *photo.size), 46, fill=255)
    img.paste(photo, (48, 580), mask)
    bubble(48, 1030, 560, 110, False, "拍到了这张")
    bubble(380, 1180, 650, 110, True, "太美了!")
    # bubbles that are only visible *through* the keyboard
    bubble(60, 1330, 600, 110, False, "再来一张")
    bubble(500, 1520, 520, 110, True, "好呀")
    bubble(80, 1760, 700, 120, False, "凌晨三点见")
    # coloured pills at the very bottom
    d.rounded_rectangle((640, 1990, 1060, 2120), 65, fill=(255, 220, 60, 255))
    d.rounded_rectangle((30, 2050, 520, 2180), 65, fill=(255, 70, 120, 255))
    return img


# ------------------------------------------------------------------ glass keys

def rrect_mask(size, box, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
    return m


def over(dst: Image.Image, src: Image.Image):
    dst.alpha_composite(src)


def paint(size, rgb, alpha_arr, mask):
    """RGBA layer of one color whose alpha is alpha_arr * mask."""
    a = (np.asarray(mask, np.float32) / 255.0) * alpha_arr
    arr = np.zeros(size[::-1] + (4,), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = rgb
    arr[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def glass_key(layer, box, r, rgb, dark, accent=False):
    """Draw one key. All sizes are in supersampled pixels. Mirrors GlassKeyDrawable.draw().
    Works on a small local canvas, the full layer is far too big for per-key numpy work."""
    g = GLASS[dark]
    pad = int(14 * SS)
    ox, oy = int(box[0]) - pad, int(box[1]) - pad
    x0, y0, x1, y1 = box[0] - ox, box[1] - oy, box[2] - ox, box[3] - oy
    size = (int(x1 + pad), int(y1 + pad))
    local = Image.new("RGBA", size)
    h = y1 - y0
    yy, xx = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    ty = np.clip((yy - y0) / h, 0, 1)
    box = (x0, y0, x1, y1)

    # 1. soft shadow below the key (stacked rounded rects, no real blur needed)
    for i in range(1, 6):
        grow = i * 1.1 * SS
        m = rrect_mask(size, (x0 - grow, y0 - grow + 2.6 * SS, x1 + grow, y1 + grow + 2.6 * SS), r + grow)
        over(local, paint(size, (0, 0, 0), g["shadow"] * (1 - i / 6) * 0.55, m))

    # 2. glass body: vertical alpha gradient of the key color
    body = rrect_mask(size, box, r)
    top, bot = (0.88, 0.80) if accent else (g["body_top"], g["body_bottom"])
    over(local, paint(size, rgb, top + (bot - top) * ty, body))

    # 3. sheen over the upper half
    sh = rrect_mask(size, (x0 + 1.5 * SS, y0 + 1.5 * SS, x1 - 1.5 * SS, y1 - 1.5 * SS), r - 1.5 * SS)
    over(local, paint(size, (255, 255, 255), g["sheen"] * np.clip(1 - ty / 0.5, 0, 1) ** 1.5, sh))

    # 4. dark hairline just outside (light mode only)
    if g["hairline"]:
        outer = np.asarray(rrect_mask(size, (x0 - SS, y0 - SS, x1 + SS, y1 + SS), r + SS), np.int16)
        ring = Image.fromarray(np.clip(outer - np.asarray(body, np.int16), 0, 255).astype(np.uint8))
        over(local, paint(size, (40, 50, 80), g["hairline"], ring))

    # 5. specular rim: bright at the top-left and bottom-right, dim in between
    sw = RIM_WIDTH_DP * DENSITY * SS
    inner = rrect_mask(size, (x0 + sw, y0 + sw, x1 - sw, y1 - sw), max(r - sw, 1))
    ring = Image.fromarray(np.clip(np.asarray(body, np.int16) - np.asarray(inner, np.int16), 0, 255).astype(np.uint8))
    t = ((xx - x0) / (x1 - x0) + (yy - y0) / h) / 2  # 0 top-left -> 1 bottom-right
    rim_a = np.interp(t, RIM_POS, g["rim"]).astype(np.float32)
    over(local, paint(size, (255, 255, 255), rim_a, ring))

    layer.alpha_composite(local, (ox, oy))


def glass_keyboard(palette: dict, dark: bool) -> Image.Image:
    """Candidate bar + glass keys on a transparent layer."""
    s = SS
    layer = Image.new("RGBA", (W * s, KB_H * s))
    d = ImageDraw.Draw(layer)
    txt = bt.rgba(palette["keyTextColor"])
    bar_h = 120
    for i, word in enumerate(("Liquid", "Glass", "glassy", "glance")):
        d.text(((48 + i * 235) * s, bar_h // 2 * s), word, font=font(46 * s), anchor="lm", fill=txt)
    d.line([(0, bar_h * s), (W * s, bar_h * s)], fill=(255, 255, 255, 60 if dark else 110), width=2 * s)

    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    m, top, rh = 10, bar_h + 22, 176
    kw = (W - 2 * m) / 10
    r = 50 * s

    def rgb_of(c):  # the app takes the RGB of the theme's key colors, the alpha comes from GlassKeyDrawable
        return ((c >> 16) & 255, (c >> 8) & 255, c & 255)

    white = rgb_of(palette["keyBackgroundColor"])
    fn_rgb = rgb_of(palette["altKeyBackgroundColor"])
    blue = rgb_of(palette["accentKeyBackgroundColor"])

    def key(x0, y0, x1, y1, label, rgb, color=txt, size=48, accent=False):
        box = ((x0 + 7) * s, (y0 + 12) * s, (x1 - 7) * s, (y1 - 12) * s)
        glass_key(layer, box, r, rgb, dark, accent)
        ImageDraw.Draw(layer).text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label,
                                   font=font(size * s), anchor="mm", fill=color)

    for ri, row in enumerate(rows):
        y = top + ri * rh
        if ri == 2:
            key(m, y, m + kw * 1.5, y + rh, "⇧", fn_rgb)
            x = m + kw * 1.5
            for ch in row:
                key(x, y, x + kw, y + rh, ch, white)
                x += kw
            key(x, y, W - m, y + rh, "⌫", fn_rgb)
        else:
            x = m + (W - 2 * m - kw * len(row)) / 2
            for ch in row:
                key(x, y, x + kw, y + rh, ch, white)
                x += kw
    y = top + 3 * rh
    key(m, y, m + kw * 1.5, y + rh, "123", fn_rgb, size=34)
    key(m + kw * 1.5, y, m + kw * 2.5, y + rh, ",", fn_rgb)
    key(m + kw * 2.5, y, m + kw * 7, y + rh, "space", white, size=34)
    key(m + kw * 7, y, m + kw * 8, y + rh, ".", fn_rgb)
    key(m + kw * 8, y, W - m, y + rh, "return", blue, (255, 255, 255, 255), 34, accent=True)
    return layer.resize((W, KB_H), Image.LANCZOS)


# ------------------------------------------------------------------ backdrop + compose

def flat_keyboard_layer(palette):
    return bt.keyboard_layer(palette, W, KB_H)


def static_background(palette):
    dark = palette["isDark"]
    return bt.glassify(bt.default_backdrop(dark), dark).resize((W, KB_H))


def blurred_backdrop(app: Image.Image, dark: bool) -> Image.Image:
    """GlassBackdrop: the content behind the keyboard, blurred, plus a light tint and a rim."""
    pad = BLUR_SIGMA * 3
    ctx = app.crop((0, max(0, KB_Y - pad), W, H)).filter(ImageFilter.GaussianBlur(BLUR_SIGMA))
    region = ctx.crop((0, ctx.height - KB_H, W, ctx.height)).convert("RGBA")
    base = (28, 28, 30) if dark else (240, 242, 250)
    tint = Image.new("RGBA", region.size, base + (0x55 if dark else 0x5C,))
    out = Image.alpha_composite(region, tint)
    out.alpha_composite(Image.new("RGBA", (W, 2), (255, 255, 255, 0x40 if dark else 0xB0)), (0, 0))
    return out.convert("RGB")


def compose(app, kb_bg, kb_layer):
    img = app.copy().convert("RGBA")
    img.paste(kb_bg.convert("RGBA"), (0, KB_Y))
    img.alpha_composite(kb_layer, (0, KB_Y))
    return img.convert("RGB")


def caption(img, text, sub):
    h = 150
    out = Image.new("RGB", (img.width, img.height + h), (24, 24, 27))
    out.paste(img, (0, h))
    d = ImageDraw.Draw(out)
    d.text((img.width // 2, 52), text, font=font(54, True), fill=(255, 255, 255), anchor="mm")
    d.text((img.width // 2, 110), sub, font=font(34, True), fill=(170, 170, 180), anchor="mm")
    return out


def main():
    out_dir = Path(__file__).resolve().parent.parent / "preview"
    out_dir.mkdir(exist_ok=True)
    for name in ("LiquidGlassLight", "LiquidGlassDark"):
        palette = bt.PALETTES[name]
        dark = palette["isDark"]
        app = mock_app(dark)
        before = compose(app, static_background(palette), flat_keyboard_layer(palette))
        after = compose(app, blurred_backdrop(app, dark), glass_keyboard(palette, dark))
        a = caption(before, "之前 · 静态背景 + 普通按键", "仅用主题就能做到的程度")
        b = caption(after, "之后 · 实时模糊 + 玻璃按键", "模糊键盘后面真实的内容")
        gap = 40
        sheet = Image.new("RGB", (a.width * 2 + gap, a.height), (24, 24, 27))
        sheet.paste(a, (0, 0))
        sheet.paste(b, (a.width + gap, 0))
        sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
        out = out_dir / f"demo_blur_{name}.png"
        sheet.save(out, optimize=True)
        # also a full-resolution crop of the patched keyboard for a closer look
        close = after.crop((0, KB_Y - 160, W, H))
        close.save(out_dir / f"demo_glass_{name}_closeup.png", optimize=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
