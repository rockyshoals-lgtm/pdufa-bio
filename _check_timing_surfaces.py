# -*- coding: utf-8 -*-
"""What do the three surfaces actually say, locally and live?"""
import io, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
H = {"User-Agent": "pdufa-verify/1.0", "Cache-Control": "no-cache"}
PAGES = {"/research/fda-decision-timing": "pdufa_site_src/research/fda-decision-timing/index.html",
         "/calendar": "pdufa_site_src/calendar/index.html",
         "/learn/what-is-a-pdufa-date": "pdufa_site_src/learn/what-is-a-pdufa-date/index.html"}
PAT = re.compile(r"(\d+)\s*(?:FDA )?decisions?[^.]{0,120}?(\d+)\s*came before[^.]{0,60}?(\d+)\s*landed on it[^.]{0,60}?(\d+)")
for url, local in PAGES.items():
    try:
        lt = io.open(local, encoding="utf-8", errors="replace").read()
    except Exception as e:
        print(f"{url}: local missing ({e})"); continue
    lm = PAT.search(re.sub(r"<[^>]+>", " ", lt))
    try:
        rt = re.sub(r"<[^>]+>", " ", urllib.request.urlopen(
            urllib.request.Request("https://www.pdufa.bio" + url, headers=H), timeout=90)
            .read().decode("utf-8", "replace"))
        rm = PAT.search(rt)
    except Exception as e:
        rm = None
        print(f"   ({url} fetch: {e})")
    print(f"{url}")
    print("   local:", lm.groups() if lm else "no match")
    print("   live :", rm.groups() if rm else "no match")
