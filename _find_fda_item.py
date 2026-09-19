# -*- coding: utf-8 -*-
"""Find the canonical FDA URL for the 2026-09-18 imlunestrant item, from the same feeds our
reconciler reads."""
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}


def get(u, t=45):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read().decode("utf-8", "replace")


FEEDS = [
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml",
    "https://www.fda.gov/drugs/resources-information-approved-drugs/oncology-cancer-hematologic-malignancies-approval-notifications",
]
for f in FEEDS:
    try:
        t = get(f)
    except Exception as e:
        print(f"{f[-60:]}: {e}")
        continue
    print(f"\n== {f[-70:]}")
    for m in re.finditer(r'<(?:link|loc)>([^<]+)</(?:link|loc)>|href="(/drugs/[^"]+)"', t):
        u = m.group(1) or m.group(2)
        if u and re.search(r"imlunestrant|inluriyo", u, re.I):
            print("   HIT:", u)
    for m in re.finditer(r"imlunestrant", t, re.I):
        seg = t[max(0, m.start() - 400): m.start() + 300]
        hrefs = re.findall(r'href="([^"]+)"', seg)
        print("   near-mention hrefs:", [h for h in hrefs if "/drugs/" in h][:3])
        print("   text:", re.sub(r"<[^>]+>", " ", seg)[-260:].strip()[:260])
        break
