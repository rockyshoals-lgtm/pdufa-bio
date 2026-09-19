# -*- coding: utf-8 -*-
"""Which of each duplicate-title pair does the dataset link, and who else links each?"""
import glob, io, json, os, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src"
src = io.open(f"{SITE}/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
ds_urls = {str(r.get("url")).rstrip("/"): r["id"] for r in rows}
titles = defaultdict(list)
for f in glob.glob(f"{SITE}/pdufa/*/index.html"):
    slug = os.path.basename(os.path.dirname(f))
    t = io.open(f, encoding="utf-8", errors="replace").read()
    if re.search(r'<meta name="robots" content="noindex', t):
        continue
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    titles[re.sub(r"\s+", " ", m.group(1)).strip() if m else "?"].append(slug)
# inbound link counts across site (excluding backups)
allhtml = [f for f in glob.glob(f"{SITE}/**/*.html", recursive=True) if "_pdufa_" not in f and "bak" not in f]
def inbound(slug):
    n = 0; who = []
    pat = re.compile(rf'href="(?:https://www\.pdufa\.bio)?/pdufa/{re.escape(slug)}["/#?]')
    for f in allhtml:
        rel = os.path.relpath(f, SITE).replace("\\", "/")
        if rel == f"pdufa/{slug}/index.html":
            continue
        if pat.search(io.open(f, encoding="utf-8", errors="replace").read()):
            n += 1; who.append(rel.replace("/index.html", ""))
    return n, who[:4]
for title, slugs in sorted(titles.items()):
    if len(slugs) < 2:
        continue
    print(title[:80])
    for s in slugs:
        n, who = inbound(s)
        print(f"   {s:<28} dataset={ds_urls.get('/pdufa/'+s, '-'):<28} inbound={n} {who}")
