# -*- coding: utf-8 -*-
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}


def txt(u):
    b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
    return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", b.decode("utf-8", "replace"))))


# 1. the FDA press release link from the feed
feed = urllib.request.urlopen(urllib.request.Request(
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml", headers=UA), timeout=60).read().decode("utf-8", "replace")
m = re.search(r"<item>.*?Sanfilippo.*?</item>", feed, re.S)
link = re.search(r"<link>(.*?)</link>", m.group(0)).group(1).strip()
print("FDA press release:", link)
t = txt(link)
i = t.find("Sanfilippo")
for key in ("approved", "brand", "Ultragenyx", "UX111", "ABO-102", "September"):
    j = t.find(key, i - 2000 if i > 2000 else 0)
print(t[max(0, t.find("today approved") - 200): t.find("today approved") + 900] if "today approved" in t else t[i - 300: i + 1200])

# 2. Ultragenyx 8-K 2026-09-17 (the main document; EX-99.1 is usually the release)
print("\n\n== Ultragenyx 8-K 2026-09-17 ==")
idx = txt("https://www.sec.gov/Archives/edgar/data/1515673/000151567326000006/")
exs = re.findall(r"(rare-[a-z0-9_.-]+\.htm)", idx)
print("   files:", sorted(set(exs)))
for f in sorted(set(exs)):
    u = "https://www.sec.gov/Archives/edgar/data/1515673/000151567326000006/" + f
    d = txt(u)
    if re.search(r"approv", d, re.I):
        k = d.lower().find("approv")
        print(f"   [{f}] ...{d[max(0, k - 350): k + 600]}")
        break
