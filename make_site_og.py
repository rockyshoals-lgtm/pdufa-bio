# -*- coding: utf-8 -*-
"""make_site_og.py -- the site-wide share image (pdufa_site_src/og.png), evergreen and true.

2026-11-08: the image every page shares (og:image / twitter:image on ~1,900 pages) was made on 2026-07-25 for the
pre-launch site: "COMING SOON · 2026", "live options", "Mobile app", an em dash, and a chart line drawn through the
text. It is what a link to pdufa.bio looks like in Slack, X, iMessage and many AI answer cards. Rebuilt with no counts
or dates (those go stale; the pages carry them) and only claims the site makes everywhere: every PDUFA date, sourced,
updated daily, facts not advice. 1200x630. Run locally when the wording changes; CI does not need fonts.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdufa_site_src", "og.png")
W, H = 1200, 630
F = r"C:\Windows\Fonts"
bold = lambda s: ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), s)
reg = lambda s: ImageFont.truetype(os.path.join(F, "segoeui.ttf"), s)

img = Image.new("RGB", (W, H), "#02060d")
d = ImageDraw.Draw(img)
for y in range(H):  # quiet vertical gradient
    t = y / H
    d.line([(0, y), (W, y)], fill=(int(2 + 8 * t), int(6 + 18 * t), int(13 + 38 * t)))
GOLD, WHITE, MUT = "#e3ba5e", "#f2f6fc", "#a7bcd9"
# pill
_pill = "UPDATED DAILY \u00b7 SOURCE-LINKED"
d.rounded_rectangle([72, 70, 116 + d.textlength(_pill, font=bold(22)) + 22, 118], radius=24, outline="#46d17f", width=2)
d.ellipse([92, 88, 104, 100], fill="#46d17f")
d.text((116, 76), "UPDATED DAILY \u00b7 SOURCE-LINKED", font=bold(22), fill="#46d17f")
# wordmark
d.text((72, 140), "pdufa", font=bold(112), fill=WHITE)
x = 72 + d.textlength("pdufa", font=bold(112))
d.text((x, 140), ".bio", font=bold(112), fill=GOLD)
d.text((72, 292), "Every FDA PDUFA date, with its source.", font=bold(50), fill=WHITE)
d.text((72, 360), "Facts, not advice.", font=bold(50), fill=GOLD)
d.text((72, 446), "Upcoming decision dates, past approvals and CRLs, and the", font=reg(30), fill=MUT)
d.text((72, 486), "measured stock run-up into each decision.", font=reg(30), fill=MUT)
d.line([(72, 560), (W - 72, 560)], fill="#1a3358", width=2)
d.text((72, 574), "PDUFA calendar  \u00b7  Decisions archive  \u00b7  Run-up study  \u00b7  Data API", font=reg(24), fill=MUT)
wm = "pdufa.bio"
d.text((W - 72 - d.textlength(wm, font=bold(28)), 570), wm, font=bold(28), fill=GOLD)
img.save(OUT, optimize=True)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
