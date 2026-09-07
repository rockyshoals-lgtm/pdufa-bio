# -*- coding: utf-8 -*-
"""The pdufa.bio favicon: a calendar tile with a check. Dates, decided.

Replaces the thin gold zigzag (2026-09-06), which blurred to noise at 16px and read as
either a pulse or a price chart -- ambiguous in exactly the tab strip where the site
sits next to Yahoo Finance, Robinhood and Seeking Alpha. The new mark is the product:
a calendar (the #1 traffic page) carrying the green check the site uses for
"Approved". Two colours on navy, strokes thick enough to survive 16px.

Writes favicon.svg (crisp on Chrome/Firefox/Edge/Safari 17+) and PNG fallbacks at
16/32/180/192/512 plus a maskable 512, all drawn natively with Pillow at 8x
supersampling so no external SVG rasteriser is needed on CI.
"""
import io
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
NAVY, GOLD, GREEN = (11, 21, 38, 255), (240, 200, 106, 255), (70, 209, 127, 255)

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0b1526"/>'
    '<rect x="10" y="14" width="44" height="40" rx="6" fill="none" stroke="#f0c86a" stroke-width="5"/>'
    '<rect x="10" y="14" width="44" height="12" rx="4" fill="#f0c86a"/>'
    '<path d="M20 38 L28 46 L44 30" fill="none" stroke="#46d17f" stroke-width="7" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>"
)


def render(size, maskable=False):
    S = 8                                   # supersample
    n = size * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 64.0                            # 64-unit design grid -> pixels

    def R(x, y, w, h, r, fill=None, outline=None, width=0):
        d.rounded_rectangle([x * u, y * u, (x + w) * u, (y + h) * u], radius=r * u,
                            fill=fill, outline=outline, width=int(width * u))

    if maskable:
        # maskable icons must survive a circular crop: full-bleed navy, mark scaled to
        # the 80% safe zone.
        d.rectangle([0, 0, n, n], fill=NAVY)
        pad = 0.10 * 64
        sc = 0.80
        off = pad
    else:
        R(0, 0, 64, 64, 14, fill=NAVY)
        sc, off = 1.0, 0.0

    def P(x, y):
        return (off + x * sc) * u, (off + y * sc) * u

    # calendar frame (gold outline) + header bar (gold fill)
    fx, fy = P(10, 14)
    fx2, fy2 = P(54, 54)
    d.rounded_rectangle([fx, fy, fx2, fy2], radius=6 * sc * u, outline=GOLD,
                        width=int(5 * sc * u))
    hx, hy = P(10, 14)
    hx2, hy2 = P(54, 26)
    d.rounded_rectangle([hx, hy, hx2, hy2], radius=4 * sc * u, fill=GOLD)
    # check (green), round joins via circles at the vertices
    pts = [P(20, 38), P(28, 46), P(44, 30)]
    w = 7 * sc * u
    d.line(pts, fill=GREEN, width=int(w), joint="curve")
    for (px, py) in pts:
        d.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=GREEN)
    return img.resize((size, size), Image.LANCZOS)


def main():
    io.open(os.path.join(SITE, "favicon.svg"), "w", encoding="utf-8").write(SVG)
    out = {"favicon-16.png": 16, "favicon-32.png": 32, "apple-touch-icon.png": 180,
           "icon-192.png": 192, "icon-512.png": 512}
    for name, size in out.items():
        render(size).save(os.path.join(SITE, name), "PNG", optimize=True)
    render(512, maskable=True).save(os.path.join(SITE, "icon-maskable-512.png"), "PNG",
                                    optimize=True)
    # ICO for legacy UAs and the /favicon.ico default probe
    ims = [render(s) for s in (16, 32, 48)]
    ims[0].save(os.path.join(SITE, "favicon.ico"), format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48)], append_images=ims[1:])
    print("favicon: svg + " + ", ".join(out) + ", icon-maskable-512.png, favicon.ico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
