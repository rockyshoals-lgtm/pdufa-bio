# -*- coding: utf-8 -*-
"""The pdufa.bio favicon: Odin's eye, the one he gave at Mimir's well.

This started as ODIN, the scoring module, and became pdufa.bio. Odin traded an eye for
the sight to see what is coming; the site exists to see what is coming on the FDA
calendar. The mark is that eye, and it is meant to be a little haunting: a heavy upper
lid, the gaze drifted up and to the right as if watching something past the viewer, the
iris as the dark of the well with faint gold ripple rings, a single green pinpoint (the
site's "approved" colour), and one tear below the lower lid. A dark halo behind the eye
lifts it off near-black so it floats.

Detail is size-aware on purpose. At 16px an outline eye thins to a squiggle and ripples
become mud, so below 32px only the lid, the void and the glint survive, and the raster is
a solid gold almond with an off-centre dark iris -- still unmistakably an eye. The SVG
carries every detail and browsers that render SVG favicons scale it themselves.

Writes favicon.svg, PNG fallbacks at 16/32/180/192/512, a maskable 512, and a multi-size
favicon.ico, all drawn natively with Pillow at 8x supersampling from the SAME Bezier
control points the SVG uses, so vector and raster are one shape.
"""
import io
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BG = (4, 7, 15, 255)           # near-black
HALO = (11, 21, 38, 255)       # the navy the site uses; here the well's dark water
GOLD = (240, 200, 106, 255)
VOID = (2, 6, 13, 255)
GREEN = (70, 209, 127, 255)

# 64-unit design grid, asymmetric: heavy upper lid (control at y=4), lower at y=54.
TIP_L, TIP_R, CTRL_TOP, CTRL_BOT = (4, 33), (60, 33), (32, 4), (32, 54)
IRIS = (37, 29, 13.0)          # off-centre: the drifted gaze
RINGS = ((9.5, 0.70), (6.0, 0.45))
PUPIL = (37.5, 29.5, 3.6)
GLINT = (40, 25.5, 1.7)
TEAR = ((30, 52), (31, 58), (33, 60), (35, 58), (33, 53))   # a small drop below the lid
HALO_C = (32, 34, 30)


def _hex(c):
    return "#%02x%02x%02x" % c[:3]


SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    f'<rect width="64" height="64" rx="14" fill="{_hex(BG)}"/>'
    f'<circle cx="{HALO_C[0]}" cy="{HALO_C[1]}" r="{HALO_C[2]}" fill="{_hex(HALO)}"/>'
    f'<path d="M{TIP_L[0]} {TIP_L[1]} Q{CTRL_TOP[0]} {CTRL_TOP[1]} {TIP_R[0]} {TIP_R[1]} '
    f'Q{CTRL_BOT[0]} {CTRL_BOT[1]} {TIP_L[0]} {TIP_L[1]} Z" fill="{_hex(GOLD)}"/>'
    f'<circle cx="{IRIS[0]}" cy="{IRIS[1]}" r="{IRIS[2]}" fill="{_hex(HALO)}"/>'
    + "".join(f'<circle cx="{IRIS[0]}" cy="{IRIS[1]}" r="{r}" fill="none" '
              f'stroke="{_hex(GOLD)}" stroke-width="1.2" opacity="{op}"/>' for r, op in RINGS)
    + f'<circle cx="{PUPIL[0]}" cy="{PUPIL[1]}" r="{PUPIL[2]}" fill="{_hex(VOID)}"/>'
    f'<circle cx="{GLINT[0]}" cy="{GLINT[1]}" r="{GLINT[2]}" fill="{_hex(GREEN)}"/>'
    f'<path d="M{TEAR[0][0]} {TEAR[0][1]} Q{TEAR[1][0]} {TEAR[1][1]} {TEAR[2][0]} {TEAR[2][1]} '
    f'Q{TEAR[3][0]} {TEAR[3][1]} {TEAR[4][0]} {TEAR[4][1]} Z" fill="{_hex(GOLD)}" opacity=".85"/>'
    "</svg>"
)


def _quad(p0, c, p1, n=72):
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]))
    return pts


def render(size, maskable=False):
    S = 8
    n = size * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 64.0
    detail = size >= 32          # ripples + tear only where they can be seen
    if maskable:
        d.rectangle([0, 0, n, n], fill=BG)
        sc, off = 0.80, 0.10 * 64
    else:
        d.rounded_rectangle([0, 0, n, n], radius=14 * u, fill=BG)
        sc, off = 1.0, 0.0

    def P(x, y):
        return ((off + x * sc) * u, (off + y * sc) * u)

    def C(cx, cy, r, fill=None, outline=None, width=0):
        x, y = P(cx, cy)
        rr = r * sc * u
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=fill, outline=outline,
                  width=max(1, int(width * sc * u)))

    C(*HALO_C, fill=HALO)
    almond = ([P(*p) for p in _quad(TIP_L, CTRL_TOP, TIP_R)]
              + [P(*p) for p in _quad(TIP_R, CTRL_BOT, TIP_L)])
    d.polygon(almond, fill=GOLD)
    C(*IRIS, fill=HALO)
    if detail:
        for r, op in RINGS:
            col = tuple(int(HALO[i] + (GOLD[i] - HALO[i]) * op) for i in range(3)) + (255,)
            C(IRIS[0], IRIS[1], r, outline=col, width=1.2)
    C(*PUPIL, fill=VOID)
    C(*GLINT, fill=GREEN)
    if detail:
        tear = ([P(*p) for p in _quad(TEAR[0], TEAR[1], TEAR[2])]
                + [P(*p) for p in _quad(TEAR[2], TEAR[3], TEAR[4])])
        tcol = tuple(int(BG[i] + (GOLD[i] - BG[i]) * 0.85) for i in range(3)) + (255,)
        d.polygon(tear, fill=tcol)
    return img.resize((size, size), Image.LANCZOS)


def main():
    io.open(os.path.join(SITE, "favicon.svg"), "w", encoding="utf-8").write(SVG)
    out = {"favicon-16.png": 16, "favicon-32.png": 32, "apple-touch-icon.png": 180,
           "icon-192.png": 192, "icon-512.png": 512}
    for name, size in out.items():
        render(size).save(os.path.join(SITE, name), "PNG", optimize=True)
    render(512, maskable=True).save(os.path.join(SITE, "icon-maskable-512.png"), "PNG",
                                    optimize=True)
    ims = [render(s) for s in (16, 32, 48)]
    ims[0].save(os.path.join(SITE, "favicon.ico"), format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48)], append_images=ims[1:])
    print("favicon (Odin's eye, the well): svg + " + ", ".join(out)
          + ", icon-maskable-512.png, favicon.ico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
