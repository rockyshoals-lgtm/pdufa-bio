# -*- coding: utf-8 -*-
"""
assemble_site.py  —  fold the freshly-generated pages into pdufa_site_src/ for one clean deploy.

Copies, into the deployable site folder (pdufa_site_src/):
  site_category_pages/readouts.html   -> readouts/index.html
  site_category_pages/devices.html    -> devices/index.html
  seo_pages/**/index.html             -> same relative path  (calendar+readouts month archives,
                                          condition pages, why-no-approval-probability, coverage)
  pricing_pro.html                    -> pricing.html
Then refreshes sitemap.xml with the new public routes.

Does NOT touch app.html / today.html — those are the encrypted gated build (re-encrypt separately
with the production gate password; the fixed plaintext is in pdufa_bio_preview/).

Usage:  python assemble_site.py
"""
import os, glob, shutil, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "pdufa_site_src")
if not os.path.isdir(SRC):
    raise SystemExit("pdufa_site_src/ not found next to this script.")

copied, routes = [], set()
def put(src_rel, dst_rel):
    s = os.path.join(HERE, src_rel)
    if not os.path.exists(s):
        print(f"  [skip] missing {src_rel}"); return
    d = os.path.join(SRC, dst_rel)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(s, d); copied.append(dst_rel)
    routes.add("/" + dst_rel.replace("\\", "/").replace("/index.html", "").rstrip("/"))

# 1) category calendars
put("site_category_pages/readouts.html", "readouts/index.html")
put("site_category_pages/devices.html",  "devices/index.html")

# 2) SEO pages (recursive: calendar/2026/<m>, readouts/2026/<m>, condition/<slug>, why-..., coverage)
seo = os.path.join(HERE, "seo_pages")
if os.path.isdir(seo):
    for f in glob.glob(os.path.join(seo, "**", "index.html"), recursive=True):
        rel = os.path.relpath(f, seo).replace("\\", "/")
        put(os.path.join("seo_pages", rel), rel)
else:
    print("  [skip] seo_pages/ not found — run the crawler/build_seo_pages first")

# 3) pricing page
put("pricing_pro.html", "pricing.html")

# 4) confirm the Stripe API functions are present
for fn in ("create-checkout-session.js", "stripe-webhook.js", "verify-access.js"):
    p = os.path.join(SRC, "api", fn)
    print(("  [ok]  " if os.path.exists(p) else "  [MISSING] ") + f"api/{fn}")

# 5) refresh sitemap.xml with the new routes (merge, dedupe)
sm = os.path.join(SRC, "sitemap.xml")
existing = ""
try: existing = open(sm, encoding="utf-8").read()
except Exception: pass
have = set(re.findall(r"<loc>\s*([^<]+?)\s*</loc>", existing))
add = sorted({("https://www.pdufa.bio" + r) for r in routes} | {"https://www.pdufa.bio/pricing",
             "https://www.pdufa.bio/coverage", "https://www.pdufa.bio/why-no-approval-probability"} - have)
if add:
    blocks = "".join(f"<url><loc>{u}</loc><changefreq>daily</changefreq></url>\n" for u in add)
    if "</urlset>" in existing:
        existing = existing.replace("</urlset>", blocks + "</urlset>")
    else:
        existing = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    + blocks + "</urlset>\n")
    open(sm, "w", encoding="utf-8").write(existing)

print(f"\nassembled {len(copied)} pages into pdufa_site_src/  (+{len(add)} new sitemap URLs)")
print("Deploy-ready: pdufa_site_src/  (static public site + Stripe api/).")
print("NOT included (do separately): /app + /today — re-encrypt pdufa_bio_preview/ with the prod gate password.")
