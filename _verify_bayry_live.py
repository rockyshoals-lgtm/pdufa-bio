# -*- coding: utf-8 -*-
"""Final live check on the BAYRY pair: neither surface may name the withdrawn goal date."""
import re
import sys
import urllib.request


def get(p):
    r = urllib.request.Request("https://www.pdufa.bio" + p,
                               headers={"User-Agent": "pdufa.bio builder",
                                        "Cache-Control": "no-cache"})
    return urllib.request.urlopen(r, timeout=60).read().decode("utf-8", "replace")


fail = 0
for path in ("/pdufa/BAYRY-sevabertinib", "/fda-decision/BAYRY-2026-09-09"):
    d = get(path)
    body = re.sub(r"<script.*?</script>", " ", d, flags=re.S)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
    ti = re.search(r"<title>(.*?)</title>", d, re.S)
    has_day = "2026-11-30" in txt or "November 30, 2026" in txt
    has_early = bool(re.search(r"\d+\s+[Dd]ays?\s+[Ee]arly|\d+ days before its", txt))
    has_link = "All November 2026 PDUFA dates" in d
    print(f"\n{path}")
    print(f"   title           : {(ti.group(1) if ti else '')[:92]}")
    print(f"   withdrawn day   : {'STILL PRESENT' if has_day else 'gone'}")
    print(f"   earliness figure: {'STILL PRESENT' if has_early else 'gone'}")
    print(f"   month link      : {'STILL PRESENT' if has_link else 'gone'}")
    m = re.search(r"goal date[^.]{0,120}", txt)
    if m:
        print(f"   says            : {m.group(0)[:140]}")
    fail += has_day + has_early + has_link

print("\nBOTH SURFACES CLEAN" if not fail else f"\n{fail} remaining issue(s)")
sys.exit(1 if fail else 0)
