# -*- coding: utf-8 -*-
import io, re, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = io.open("pdufa_site_src/calendar/index.html", encoding="utf-8").read()
for m in re.finditer(r"GRACE resubmission", t):
    seg = t[max(0, m.start() - 700): m.start() + 300]
    print(re.findall(r'href="([^"]+)"', seg))
    print(re.sub(r"<[^>]+>", " ", seg)[-500:].replace("\n", " "))
    print("----")
# how many calendar rows link /pdufa/<TICKER> bare vs dataset url
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
bad = []
for r in rows:
    if r["type"] != "PDUFA" or r.get("st") != "Upcoming":
        continue
    u = str(r.get("url"))
    if not u.startswith("/pdufa/"):
        continue
    if f'href="{u}"' not in t and f'href="{u}/"' not in t:
        bad.append((r["id"], u))
print("upcoming PDUFA rows whose dataset url is not linked from /calendar:", len(bad))
for b in bad[:40]:
    print("  ", b)
