#!/usr/bin/env python3
"""
Simulated rendering of the "glass" patches (0001 blur backdrop, 0003 glass keys, 0004 refraction).
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


LOCAL_SIZE = (0, 0)  # size of the local key canvas, set by glass_key

# Keep in sync with RefractionPainter (GlassRefraction.kt)
BEVEL_DP, STRENGTH_DP, ABERRATION, ZOOM, RIM_SHADE = 14.0, 11.0, 0.95, 0.97, 0.10
TAPS = 7  # spectral samples per pixel
REFRACTED_TINT_SCALE = 0.5


def bilinear(img, x, y):
    """Sample img (H, W, 3 float) at continuous pixel coordinates, pixel centers at +0.5, clamped."""
    h, w = img.shape[:2]
    x = np.clip(x - 0.5, 0, w - 1)
    y = np.clip(y - 0.5, 0, h - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    top = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    bot = img[y1, x0] * (1 - fx) + img[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def refract(backdrop, box, r, origin):
    """numpy version of the AGSL in RefractionPainter. Everything is in 1x pixels; `box` and `origin`
    are given in supersampled pixels and converted. Returns an (H, W, 3) float image in 0..255."""
    x0, y0, x1, y1 = [v / SS for v in box]
    ox, oy = origin[0] / SS, origin[1] / SS  # local canvas origin, in backdrop coordinates
    lw, lh = LOCAL_SIZE
    yy, xx = np.mgrid[0:lh, 0:lw].astype(np.float32)
    px, py = (xx + 0.5) / SS, (yy + 0.5) / SS
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    dx, dy = px - cx, py - cy
    rad = r / SS
    qx, qy = np.abs(dx) - hx + rad, np.abs(dy) - hy + rad
    sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rad
    bevel = BEVEL_DP * DENSITY
    edge = 1 - np.clip(-sd / bevel, 0, 1)
    k = edge ** 3
    qlen = np.maximum(np.hypot(qx, qy), 1e-4)
    nx = np.where((qx > 0) & (qy > 0), qx / qlen, np.where(qx > qy, 1.0, 0.0))
    ny = np.where((qx > 0) & (qy > 0), qy / qlen, np.where(qx > qy, 0.0, 1.0))
    nx = nx * np.where(dx < 0, -1.0, 1.0)
    ny = ny * np.where(dy < 0, -1.0, 1.0)
    bx, by = cx + dx * ZOOM, cy + dy * ZOOM
    strength = STRENGTH_DP * DENSITY
    kd = edge ** 2  # dispersion reaches further in than the bend itself
    out = np.empty((lh, lw, 3), np.float32)
    # outside the bevel there is no bend and no dispersion: a single sample is enough
    out[:] = bilinear(backdrop, bx + ox, by + oy)
    inside = edge > 0.01
    ix = np.nonzero(inside)
    bxi, byi = bx[ix], by[ix]
    nxi, nyi = nx[ix], ny[ix]
    shift = strength * k[ix]
    spread = strength * ABERRATION * kd[ix]
    acc = np.zeros((len(bxi), 3), np.float32)
    wsum = np.zeros(3, np.float32)
    for i in range(TAPS):
        t = (i - (TAPS - 1) / 2) / ((TAPS - 1) / 2)  # -1 .. 1
        # blue bends the most, red the least, like in real glass; weights are triangles over t
        w = np.array([np.clip(1 - (t + 1) / 1.1, 0, 1),   # red, peaks at t = -1
                      np.clip(1 - abs(t) / 0.9, 0, 1),     # green, peaks at t = 0
                      np.clip(1 - (1 - t) / 1.1, 0, 1)],   # blue, peaks at t = 1
                     np.float32)
        d = shift + spread * t
        c = bilinear(backdrop, bxi + nxi * d + ox, byi + nyi * d + oy)
        acc += c * w
        wsum += w
    out[ix] = acc / wsum
    return out * (1 - RIM_SHADE * k)[..., None]


def glass_key(layer, box, r, rgb, dark, accent=False, backdrop=None):
    """Draw one key. All sizes are in supersampled pixels. Mirrors GlassKeyDrawable.draw().
    Works on a small local canvas, the full layer is far too big for per-key numpy work."""
    g = GLASS[dark]
    u = DENSITY / 2.6  # the constants below were tuned at 2.6
    pad = int(14 * SS * u)
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
        grow = i * 1.1 * SS * u
        m = rrect_mask(size, (x0 - grow, y0 - grow + 2.6 * SS * u, x1 + grow, y1 + grow + 2.6 * SS * u), r + grow)
        over(local, paint(size, (0, 0, 0), g["shadow"] * (1 - i / 6) * 0.55, m))

    # 2. glass body: vertical alpha gradient of the key color
    body = rrect_mask(size, box, r)
    top, bot = (0.88, 0.80) if accent else (g["body_top"], g["body_bottom"])
    if backdrop is not None and not accent:
        # refracted copy of the background, with a lighter tint on top
        global LOCAL_SIZE
        LOCAL_SIZE = size
        lens = refract(backdrop, box, r, (ox, oy))
        arr = np.zeros(size[::-1] + (4,), np.uint8)
        arr[..., :3] = np.clip(lens, 0, 255).astype(np.uint8)
        arr[..., 3] = np.asarray(body, np.uint8)
        over(local, Image.fromarray(arr, "RGBA"))
        top, bot = top * REFRACTED_TINT_SCALE, bot * REFRACTED_TINT_SCALE
    over(local, paint(size, rgb, top + (bot - top) * ty, body))

    # 3. sheen over the upper half
    sh = rrect_mask(size, (x0 + 1.5 * SS * u, y0 + 1.5 * SS * u, x1 - 1.5 * SS * u, y1 - 1.5 * SS * u),
                    max(r - 1.5 * SS * u, 1))
    over(local, paint(size, (255, 255, 255), g["sheen"] * np.clip(1 - ty / 0.5, 0, 1) ** 1.5, sh))

    # 4. dark hairline just outside (light mode only)
    if g["hairline"]:
        outer = np.asarray(rrect_mask(size, (x0 - SS * u, y0 - SS * u, x1 + SS * u, y1 + SS * u), r + SS * u), np.int16)
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


class Metrics:
    """Pixel sizes of a keyboard. `scale` is TabletLayout.scale(): labels and the candidate bar grow
    on large screens. Rows are laid out inside `keys_h`, the candidate bar sits above."""

    def __init__(self, canvas_w, keyboard_w, density, bar_dp, keys_h_px, scale=1.0, radius_dp=6.0):
        self.W, self.kb_w, self.density, self.scale = canvas_w, keyboard_w, density, scale
        self.kb_left = (canvas_w - keyboard_w) // 2
        self.bar_h = round(bar_dp * density)
        self.row_h = keys_h_px / 4
        self.H = self.bar_h + keys_h_px + round(6 * density)  # a little room below the last row
        self.gap_x = 2.7 * density
        self.gap_y = 4.6 * density
        self.radius = radius_dp * density
        self.label = 18.5 * scale * density
        self.small = 13.1 * scale * density
        self.cand = 17.7 * scale * density


def glass_keyboard(palette: dict, dark: bool, backdrop=None, m=None) -> Image.Image:
    """Candidate bar + glass keys on a transparent layer."""
    global DENSITY
    m = m or PHONE
    DENSITY = m.density
    s = SS
    layer = Image.new("RGBA", (m.W * s, int(m.H) * s))
    d = ImageDraw.Draw(layer)
    txt = bt.rgba(palette["keyTextColor"])
    bar_h = m.bar_h
    for i, word in enumerate(("Liquid", "Glass", "glassy", "glance")):
        d.text(((m.kb_left + 18 * m.density + i * 90 * m.density) * s, bar_h // 2 * s), word,
               font=font(int(m.cand * s)), anchor="lm", fill=txt)
    d.line([(m.kb_left * s, bar_h * s), ((m.kb_left + m.kb_w) * s, bar_h * s)],
           fill=(255, 255, 255, 60 if dark else 110), width=2 * s)

    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    side = 4 * m.density / 2.6
    left, right = m.kb_left + side, m.kb_left + m.kb_w - side
    top, rh = bar_h + 8 * m.density / 2.6, m.row_h
    kw = (right - left) / 10
    r = m.radius * s

    def rgb_of(c):  # the app takes the RGB of the theme's key colors, the alpha comes from GlassKeyDrawable
        return ((c >> 16) & 255, (c >> 8) & 255, c & 255)

    white = rgb_of(palette["keyBackgroundColor"])
    fn_rgb = rgb_of(palette["altKeyBackgroundColor"])
    blue = rgb_of(palette["accentKeyBackgroundColor"])

    def key(x0, y0, x1, y1, label, rgb, color=txt, small=False, accent=False):
        box = ((x0 + m.gap_x) * s, (y0 + m.gap_y / 2) * s, (x1 - m.gap_x) * s, (y1 - m.gap_y / 2) * s)
        glass_key(layer, box, r, rgb, dark, accent, backdrop)
        ImageDraw.Draw(layer).text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label,
                                   font=font(int((m.small if small else m.label) * s)), anchor="mm", fill=color)

    for ri, row in enumerate(rows):
        y = top + ri * rh
        if ri == 2:
            key(left, y, left + kw * 1.5, y + rh, "⇧", fn_rgb)
            x = left + kw * 1.5
            for ch in row:
                key(x, y, x + kw, y + rh, ch, white)
                x += kw
            key(x, y, right, y + rh, "⌫", fn_rgb)
        else:
            x = left + (right - left - kw * len(row)) / 2
            for ch in row:
                key(x, y, x + kw, y + rh, ch, white)
                x += kw
    y = top + 3 * rh
    key(left, y, left + kw * 1.5, y + rh, "123", fn_rgb, small=True)
    key(left + kw * 1.5, y, left + kw * 2.5, y + rh, ",", fn_rgb)
    key(left + kw * 2.5, y, left + kw * 7, y + rh, "space", white, small=True)
    key(left + kw * 7, y, left + kw * 8, y + rh, ".", fn_rgb)
    key(left + kw * 8, y, right, y + rh, "return", blue, (255, 255, 255, 255), True, accent=True)
    return layer.resize((m.W, int(m.H)), Image.LANCZOS)


# phone: 1080 px wide at 2.6x, rows as before; the bar is 40dp, keys area 4 rows of 176 px
PHONE = Metrics(W, W, 2.6, 40, KB_H - round(40 * 2.6) - round(6 * 2.6))


# ------------------------------------------------------------------ backdrop + compose

def flat_keyboard_layer(palette):
    return bt.keyboard_layer(palette, W, KB_H)


def static_background(palette):
    dark = palette["isDark"]
    return bt.glassify(bt.default_backdrop(dark), dark).resize((W, KB_H))


def blurred_backdrop(app: Image.Image, dark: bool, kb_h=None, sigma=BLUR_SIGMA) -> Image.Image:
    """GlassBackdrop: the content behind the keyboard, blurred, plus a light tint and a rim."""
    kb_h = kb_h or KB_H
    w, h = app.size
    pad = sigma * 3
    ctx = app.crop((0, max(0, h - kb_h - pad), w, h)).filter(ImageFilter.GaussianBlur(sigma))
    region = ctx.crop((0, ctx.height - kb_h, w, ctx.height)).convert("RGBA")
    base = (28, 28, 30) if dark else (240, 242, 250)
    tint = Image.new("RGBA", region.size, base + (0x55 if dark else 0x5C,))
    out = Image.alpha_composite(region, tint)
    out.alpha_composite(Image.new("RGBA", (w, 2), (255, 255, 255, 0x40 if dark else 0xB0)), (0, 0))
    return out.convert("RGB")


def compose(app, kb_bg, kb_layer):
    img = app.copy().convert("RGBA")
    y = app.height - kb_bg.height
    img.paste(kb_bg.convert("RGBA"), (0, y))
    img.alpha_composite(kb_layer, (0, y))
    return img.convert("RGB")


def caption(img, text, sub):
    h = 150
    out = Image.new("RGB", (img.width, img.height + h), (24, 24, 27))
    out.paste(img, (0, h))
    d = ImageDraw.Draw(out)
    d.text((img.width // 2, 52), text, font=font(54, True), fill=(255, 255, 255), anchor="mm")
    d.text((img.width // 2, 110), sub, font=font(34, True), fill=(170, 170, 180), anchor="mm")
    return out


def mock_app_tablet(dark: bool, w: int, h: int) -> Image.Image:
    """A landscape tablet: contact list on the left, chat on the right, wallpaper behind everything."""
    if dark:
        blobs = [(0.1, 0.1, 0.7, (88, 54, 220)), (0.95, 0.35, 0.6, (210, 40, 120)),
                 (0.2, 0.9, 0.6, (0, 130, 230)), (0.7, 0.95, 0.6, (255, 120, 40))]
        base = (20, 20, 40)
    else:
        blobs = [(0.1, 0.1, 0.7, (130, 180, 255)), (0.95, 0.35, 0.6, (255, 140, 190)),
                 (0.2, 0.9, 0.6, (110, 220, 255)), (0.7, 0.95, 0.6, (255, 190, 90))]
        base = (235, 238, 250)
    img = mesh(w, h, blobs, base)
    d = ImageDraw.Draw(img, "RGBA")
    fg = (255, 255, 255, 255) if dark else (28, 28, 30, 255)
    panel = (255, 255, 255, 40) if dark else (255, 255, 255, 150)
    d.text((60, 36), "9:41", font=font(40), fill=fg)
    d.rounded_rectangle((40, 110, 560, h - 40), 36, fill=panel)
    names = ["Aurora", "Beam", "Cedar", "Dune", "Ember", "Fjord", "Grove"]
    for i, n in enumerate(names):
        y = 140 + i * 150
        d.ellipse((70, y, 150, y + 80), fill=(255, 255, 255, 230))
        d.text((175, y + 6), n, font=font(40), fill=fg)
        d.text((175, y + 52), "好的,晚点见" if i % 2 else "看看这张照片", font=font(30, True), fill=fg[:3] + (150,))
    d.rounded_rectangle((600, 110, w - 40, h - 40), 36, fill=panel)
    me, them = (10, 132, 255, 255), ((255, 255, 255, 215) if not dark else (255, 255, 255, 70))
    texts = [(0, "今晚看极光吗?"), (1, "走!我带相机"), (0, "拍到了这张"), (1, "太美了!"),
             (0, "再来一张"), (1, "好呀"), (0, "凌晨三点见")]
    for i, (mine, t) in enumerate(texts):
        bw = 120 + len(t) * 60
        x = (w - 40 - 40 - bw) if mine else 640
        y = 150 + i * 170
        d.rounded_rectangle((x, y, x + bw, y + 110), 40, fill=me if mine else them)
        d.text((x + 36, y + 55), t, font=font(40, True), anchor="lm", fill=(255, 255, 255, 255) if mine else fg)
    return img


def tablet_demo(out_dir):
    global DENSITY
    TW, TH, density = 2560, 1600, 2.0
    for name in ("LiquidGlassLight", "LiquidGlassDark"):
        palette = bt.PALETTES[name]
        dark = palette["isDark"]
        app = mock_app_tablet(dark, TW, TH)
        # before: the phone layout stretched over the whole width, rows from the percentage preference
        m0 = Metrics(TW, TW, density, 40, round(TH * 0.49), scale=1.0)
        # after: TabletLayout, 900dp wide, 340dp of keys, a 48dp candidate bar, 1.2x labels
        m1 = Metrics(TW, round(900 * density), density, 48, round(340 * density), scale=1.2)
        shots = []
        for m in (m0, m1):
            bg = blurred_backdrop(app, dark, int(m.H), sigma=round(16 * density))
            shots.append(compose(app, bg, glass_keyboard(palette, dark, None, m)))
        a = caption(shots[0], "之前 · 手机布局拉伸到整个宽度", "键宽 250px 以上,键盘整个横屏占掉半个屏幕")
        b = caption(shots[1], "之后 · 平板布局", "最大宽度 900dp 居中,键高 340dp,字号和候选栏放大 1.2 倍")
        sheet = Image.new("RGB", (a.width, a.height * 2 + 30), (24, 24, 27))
        sheet.paste(a, (0, 0))
        sheet.paste(b, (0, a.height + 30))
        sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
        sheet.save(out_dir / f"demo_tablet_{name}.png", optimize=True)
        print("wrote tablet", name)


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

        # refraction mode: the keys bend the keyboard's own (crisp) background image
        crisp = np.asarray(bt.crisp_backdrop(dark, W, KB_H), np.float32)
        kb_bg = Image.fromarray(crisp.astype(np.uint8))
        plain = compose(app, kb_bg, glass_keyboard(palette, dark))
        refr = compose(app, kb_bg, glass_keyboard(palette, dark, crisp))
        a = caption(plain, "玻璃按键 · 无折射", "补丁 0003")
        b = caption(refr, "玻璃按键 + 折射", "补丁 0004 · 折射键盘自带的背景图")
        sheet = Image.new("RGB", (a.width * 2 + gap, a.height), (24, 24, 27))
        sheet.paste(a, (0, 0))
        sheet.paste(b, (a.width + gap, 0))
        sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
        sheet.save(out_dir / f"demo_refraction_{name}.png", optimize=True)
        stack = Image.new("RGB", (W, (H - KB_Y + 20) * 2 + 10), (24, 24, 27))
        stack.paste(plain.crop((0, KB_Y - 20, W, H)), (0, 0))
        stack.paste(refr.crop((0, KB_Y - 20, W, H)), (0, H - KB_Y + 30))
        stack.save(out_dir / f"demo_refraction_{name}_closeup.png", optimize=True)
        print("wrote refraction", name)


if __name__ == "__main__":
    if "--tablet" in sys.argv:
        tablet_demo(Path(__file__).resolve().parent.parent / "preview")
    else:
        main()
        tablet_demo(Path(__file__).resolve().parent.parent / "preview")
