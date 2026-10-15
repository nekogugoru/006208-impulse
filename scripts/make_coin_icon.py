"""遊戲風金幣圖示（卡通描邊款）。

用法：python scripts/make_coin_icon.py "0050"            → 只有代號
      python scripts/make_coin_icon.py "006208" "富邦台50" → 代號＋下方小字
輸出到 icons/：icon-512.png、icon-192.png、apple-touch-icon.png、icon-maskable-512.png、preview.png
"""
import math
import pathlib
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

S = 2048
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
OUT = pathlib.Path(__file__).resolve().parent.parent / 'icons'

INK = (74, 36, 6)          # 深咖啡描邊
GOLD_HI = (255, 236, 120)
GOLD = (255, 196, 30)
GOLD_LO = (226, 128, 8)
EDGE = (190, 96, 6)


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def disk(cx, cy, r):
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    return m


def vgrad(top, bottom, y0, y1):
    g = Image.new('RGB', (1, 256))
    for i in range(256):
        t = i / 255
        g.putpixel((0, i), tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3)))
    full = Image.new('RGB', (S, S), bottom)
    full.paste(top, (0, 0, S, max(0, int(y0))))
    full.paste(g.resize((S, max(1, int(y1 - y0)))), (0, int(y0)))
    return full


def radial_bg(cx, cy, r, c_in, c_out):
    im = Image.new('RGB', (S, S), c_out)
    d = ImageDraw.Draw(im)
    for i in range(160, 0, -1):
        t = i / 160
        rr = r * t
        col = tuple(int(c_in[k] + (c_out[k] - c_in[k]) * t) for k in range(3))
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    return im.filter(ImageFilter.GaussianBlur(10))


def fit_font(text, max_w, start):
    size = int(start)
    while size > 20:
        f = ImageFont.truetype(FONT, size)
        bb = f.getbbox(text)
        if bb[2] - bb[0] <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(FONT, size)


def outlined_text(im, text, font, cx, cy, stroke, fill_top, fill_bot):
    """白色厚描邊 → 深色外框 → 漸層字面，再加一道淺色上緣，像遊戲裡的數字。"""
    def mask(off=(0, 0), sw=0):
        m = Image.new('L', (S, S), 0)
        ImageDraw.Draw(m).text((cx + off[0], cy + off[1]), text, font=font, fill=255,
                               anchor='mm', stroke_width=sw, stroke_fill=255)
        return m
    # 投影
    im.paste(INK, (0, 0), mask((0, int(stroke * 0.9)), stroke).filter(ImageFilter.GaussianBlur(2)))
    # 外框
    im.paste(INK, (0, 0), mask((0, 0), stroke))
    # 字面漸層
    m = mask()
    bb = m.getbbox() or (0, 0, S, S)
    im.paste(vgrad(fill_top, fill_bot, bb[1], bb[3]), (0, 0), m)
    # 上緣反光
    hi = ImageChops.subtract(m, mask((0, int(stroke * 0.45))))
    im.paste((255, 255, 235), (0, 0), hi)


def star4(d, x, y, L, w, col):
    d.polygon([(x, y - L), (x + w, y), (x, y + L), (x - w, y)], fill=col)
    d.polygon([(x - L, y), (x, y - w), (x + L, y), (x, y + w)], fill=col)


def make(code, sub=None, scale=1.0):
    cx = cy = S // 2
    R = int(S * 0.40 * scale)
    ow = int(R * 0.055)  # 外框粗細

    im = radial_bg(cx, int(cy * 0.92), int(S * 0.78), hexc('#4a3220'), hexc('#140d08'))
    # 金色光暈＋放射光
    rays = Image.new('L', (S, S), 0)
    dr = ImageDraw.Draw(rays)
    for k in range(16):
        a0 = 2 * math.pi * k / 16
        a1 = a0 + math.pi / 32
        far = S
        dr.polygon([(cx, cy), (cx + far * math.cos(a0), cy + far * math.sin(a0)),
                    (cx + far * math.cos(a1), cy + far * math.sin(a1))], fill=38)
    rays = ImageChops.multiply(rays, disk(cx, cy, int(R * 1.55)).filter(ImageFilter.GaussianBlur(R * 0.35)))
    im = Image.composite(Image.new('RGB', (S, S), hexc('#ffc23a')), im, rays)
    glow = disk(cx, cy, int(R * 1.18)).point(lambda v: v * 0.42).filter(ImageFilter.GaussianBlur(R * 0.22))
    im = Image.composite(Image.new('RGB', (S, S), hexc('#ffb52e')), im, glow)

    # 地面陰影
    sh = Image.new('L', (S, S), 0)
    ImageDraw.Draw(sh).ellipse((cx - R * 0.9, cy + R * 1.02, cx + R * 0.9, cy + R * 1.16), fill=150)
    im = Image.composite(Image.new('RGB', (S, S), (8, 5, 2)), im, sh.filter(ImageFilter.GaussianBlur(R * 0.05)))

    thick = int(R * 0.11)
    # 厚度（側邊）與外框
    im.paste(INK, (0, 0), disk(cx, cy + thick, R + ow))
    im.paste(INK, (0, 0), disk(cx, cy, R + ow))
    im.paste(vgrad(GOLD_LO, EDGE, cy, cy + R + thick), (0, 0), disk(cx, cy + thick, R))
    # 側邊直條紋
    side = Image.new('L', (S, S), 0)
    ds = ImageDraw.Draw(side)
    for i in range(-14, 15):
        x = cx + R * math.sin(i / 15 * math.pi / 2)
        ds.line((x, cy, x, cy + R + thick + 4), fill=255, width=max(2, int(R * 0.012)))
    side = ImageChops.multiply(side, ImageChops.subtract(disk(cx, cy + thick, R), disk(cx, cy, R)))
    im.paste(INK, (0, 0), side)

    # 正面：外圈（平塗＋上亮下暗）
    im.paste(vgrad(GOLD_HI, GOLD_LO, cy - R, cy + R), (0, 0), disk(cx, cy, R))
    # 外圈與內面的分隔線
    ri = int(R * 0.80)
    im.paste(INK, (0, 0), disk(cx, cy, ri + int(ow * 0.6)))
    # 內面（略凹：下亮上暗）
    im.paste(vgrad(hexc('#f2a51a'), hexc('#ffd84a'), cy - ri, cy + ri), (0, 0), disk(cx, cy, ri))
    # 外圈上的小圓點（遊戲幣常見）
    d = ImageDraw.Draw(im)
    rd = R * 0.90
    for k in range(20):
        a = 2 * math.pi * k / 20 - math.pi / 2
        x, y = cx + rd * math.cos(a), cy + rd * math.sin(a)
        r0 = R * 0.028
        d.ellipse((x - r0, y - r0, x + r0, y + r0), fill=EDGE)
        d.ellipse((x - r0 * 0.5 - r0 * 0.25, y - r0 * 0.5 - r0 * 0.3, x + r0 * 0.5 - r0 * 0.25, y + r0 * 0.5 - r0 * 0.3),
                  fill=GOLD_HI)

    # 文字
    if sub:
        f_main = fit_font(code, ri * 1.62, R * 0.50)
        f_sub = fit_font(sub, ri * 1.30, R * 0.235)
        outlined_text(im, code, f_main, cx, cy - R * 0.10, int(R * 0.035), (255, 255, 255), hexc('#fff0b0'))
        # 下方小字：深色字＋金色緞帶
        d = ImageDraw.Draw(im)
        by = cy + R * 0.38
        bw, bh = ri * 0.78, R * 0.155
        d.rounded_rectangle((cx - bw, by - bh, cx + bw, by + bh), radius=int(bh), fill=INK)
        d.rounded_rectangle((cx - bw + ow * 0.6, by - bh + ow * 0.6, cx + bw - ow * 0.6, by + bh - ow * 0.6),
                            radius=int(bh), fill=hexc('#c0221f'))
        d.text((cx, by + R * 0.005), sub, font=f_sub, fill=(255, 246, 214), anchor='mm')
        # 上方小星星
        for sx in (-0.2, 0, 0.2):
            star4(d, cx + R * sx, cy - R * 0.55, R * 0.06, R * 0.022, EDGE)
    else:
        f_main = fit_font(code, ri * 1.55, R * 0.62)
        outlined_text(im, code, f_main, cx, cy - R * 0.02, int(R * 0.04), (255, 255, 255), hexc('#fff0b0'))
        d = ImageDraw.Draw(im)
        for sx in (-0.2, 0, 0.2):
            star4(d, cx + R * sx, cy - R * 0.50, R * 0.06, R * 0.022, EDGE)
        for sx in (-0.2, 0, 0.2):
            star4(d, cx + R * sx, cy + R * 0.50, R * 0.06, R * 0.022, EDGE)

    # 斜向亮光條（卡通反光）
    hl = Image.new('L', (S, S), 0)
    dh = ImageDraw.Draw(hl)
    for off, w, a in ((-0.55, 0.16, 120), (-0.28, 0.06, 95)):
        x0 = cx + R * off
        dh.polygon([(x0, cy - R * 1.2), (x0 + R * w, cy - R * 1.2),
                    (x0 + R * w - R * 0.7, cy + R * 1.2), (x0 - R * 0.7, cy + R * 1.2)], fill=a)
    hl = ImageChops.multiply(hl, disk(cx, cy, int(R - ow * 0.2)))
    im = Image.composite(Image.new('RGB', (S, S), (255, 255, 240)), im, hl)

    # 閃光（放在錢幣右上外緣，避開文字）
    sp = Image.new('L', (S, S), 0)
    dsp = ImageDraw.Draw(sp)
    star4(dsp, cx + R * 0.80, cy - R * 0.78, R * 0.26, R * 0.045, 255)
    star4(dsp, cx - R * 0.88, cy + R * 0.66, R * 0.13, R * 0.025, 255)
    im = Image.composite(Image.new('RGB', (S, S), (255, 255, 236)), im, sp.filter(ImageFilter.GaussianBlur(2)))
    return im


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else '0050'
    sub = sys.argv[2] if len(sys.argv) > 2 else None
    OUT.mkdir(parents=True, exist_ok=True)
    big = make(code, sub)
    big.resize((512, 512), Image.LANCZOS).save(OUT.parent / 'preview.png')
    for n, s in (('icon-512.png', 512), ('icon-192.png', 192), ('apple-touch-icon.png', 180)):
        big.resize((s, s), Image.LANCZOS).save(OUT / n)
    make(code, sub, scale=0.78).resize((512, 512), Image.LANCZOS).save(OUT / 'icon-maskable-512.png')


if __name__ == '__main__':
    main()
