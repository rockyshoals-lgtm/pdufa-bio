# -*- coding: utf-8 -*-
"""TLX101-Px (Pixclara) goal date was 2026-09-11; the site has said 'awaiting' for 7 days.
Has Telix announced anything? Checked without asserting anything I cannot see."""
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 pdufa.bio builder rockyshoals@gmail.com"}
for u in ("https://telixpharma.com/news-views/",
          "https://telixpharma.com/investor-centre/asx-announcements/"):
    try:
        t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"{u}: {e}")
        continue
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    print(f"\n== {u}")
    hits = 0
    for m in re.finditer(r"(Pixclara|TLX101|glioma|FDA)", txt):
        seg = txt[max(0, m.start() - 200): m.end() + 260].strip()
        if re.search(r"2026", seg):
            hits += 1
            print("   ...", seg[:330])
            if hits >= 4:
                break
    if not hits:
        print("   (no 2026-dated Pixclara/TLX101/FDA item found in the page text)")
