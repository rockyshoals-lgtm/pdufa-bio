# -*- coding: utf-8 -*-
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = "pdufa_site_src"

print("== /drug/inluriyo ==")
d = io.open(f"{SITE}/drug/inluriyo/index.html", encoding="utf-8", errors="replace").read()
print("   title:", re.search(r"<title>(.*?)</title>", d, re.S).group(1)[:90])
for pat in (r"(\d+) FDA decisions? on record", r"approved it on\s*<b>([^<]+)</b>", r"Sep 18, 2026", r"abemaciclib"):
    m = re.search(pat, d)
    print(f"   {pat[:34]:<36} -> {m.group(0)[:70] if m else 'ABSENT'}")

print("\n== /fda-decision/LLY-2026-09-18 ==")
p = f"{SITE}/fda-decision/LLY-2026-09-18/index.html"
if os.path.exists(p):
    t = io.open(p, encoding="utf-8", errors="replace").read()
    print("   title:", re.search(r"<title>(.*?)</title>", t, re.S).group(1)[:95])
    print("   states a goal date:", bool(re.search(r"goal date</span><b>\d{4}", t)))
    print("   says we hold none:", "do not state a goal date" in t or "does not hold" in t)
    print("   links FDA source:", "fda.gov/drugs/resources-information-approved-drugs" in t)
    print("   earliness claim:", bool(re.search(r"\d+ Days? (?:Early|Late)", t)))
else:
    print("   MISSING")

print("\n== dead link hunt in ticker hubs ==")
have = set()
for root, dirs, files in os.walk(SITE):
    if "index.html" in files:
        have.add("/" + os.path.relpath(root, SITE).replace("\\", "/").rstrip("."))
have = {h.rstrip("/") or "/" for h in have}
bad = []
for f in sorted(os.listdir(f"{SITE}/ticker")):
    p = f"{SITE}/ticker/{f}/index.html"
    if not os.path.isfile(p):
        continue
    t = io.open(p, encoding="utf-8", errors="replace").read()
    for href in set(re.findall(r'href="(/[^"#?]*)"', t)):
        h = href.rstrip("/") or "/"
        if h.startswith(("/api", "/fonts", "/favicon")) or "." in h.rsplit("/", 1)[-1]:
            continue
        if h not in have:
            bad.append((f, href))
for b in bad[:12]:
    print("   DEAD:", b)
print("   total dead:", len(bad))
