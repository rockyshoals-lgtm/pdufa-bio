
# -*- coding: utf-8 -*-
"""Live check on audit items 7 and 7b."""
import re
import sys
import urllib.request


def get(p):
    r = urllib.request.Request("https://www.pdufa.bio" + p,
                               headers={"User-Agent": "pdufa.bio builder",
                                        "Cache-Control": "no-cache"})
    return urllib.request.urlopen(r, timeout=60).read().decode("utf-8", "replace")


fail = 0
for slug, word in (("oncology", "oncology"), ("rare-disease", "rare disease")):
    try:
        d = get(f"/readouts/{slug}")
    except Exception as e:  # noqa: BLE001
        print(f"/readouts/{slug}: FETCH {e}")
        fail += 1
        continue
    t = re.search(r"<title>(.*?)</title>", d, re.S)
    rows = len(re.findall(r'<a class="row"', d))
    floor = "floor, not a complete census" in d
    odds = bool(re.search(r"\bodds\b|probability of success", re.sub(r"<[^>]+>", " ", d), re.I))
    print(f"\n/readouts/{slug}")
    print(f"   title : {(t.group(1) if t else '')[:80]}")
    print(f"   rows  : {rows}")
    print(f"   coverage sentence: {'present' if floor else 'MISSING'}")
    print(f"   approval-odds language: {'PRESENT (bad)' if odds else 'none'}")
    fail += (rows == 0) + (not floor)

d = get("/learn/what-is-a-pdufa-date")
heads = [re.sub(r"<[^>]+>", "", h).strip()
         for h in re.findall(r"<h2[^>]*>(.*?)</h2>", d, re.S)]
print("\n/learn/what-is-a-pdufa-date H2 sections:")
for h in heads:
    print(f"   - {h[:70]}")
stock = "What happens to the stock?" in d
timing = bool(re.search(r"came before the goal date", re.sub(r"<[^>]+>", " ", d)))
print(f"   trade-framing section: {'STILL PRESENT' if stock else 'gone'}")
print(f"   citable timing sentence: {'intact' if timing else 'LOST'}")
fail += stock + (not timing)

r = get("/readouts")
print(f"\n/readouts links both hubs: "
      f"{'/readouts/oncology' in r and '/readouts/rare-disease' in r}")

print("\nLIVE VERIFIED" if not fail else f"\n{fail} issue(s)")
sys.exit(1 if fail else 0)
