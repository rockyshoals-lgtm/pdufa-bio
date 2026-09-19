# -*- coding: utf-8 -*-
"""Audit 09-15 section 5: fetch /build-info.json as two different clients within one minute and
compare body, last-modified, age and the edge (x-vercel-id). Prints; asserts nothing."""
import json, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
URL = "https://www.pdufa.bio/build-info.json"
CLIENTS = [("default-client", {"User-Agent": "pdufa-verify/1.0"}),
           ("browser-like", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
                             "Accept": "application/json,*/*"}),
           ("no-cache", {"User-Agent": "pdufa-verify/1.0", "Cache-Control": "no-cache", "Pragma": "no-cache"})]
seen = []
for name, hdr in CLIENTS:
    r = urllib.request.urlopen(urllib.request.Request(URL, headers=hdr), timeout=30)
    body = json.loads(r.read())
    h = {k.lower(): v for k, v in r.headers.items()}
    seen.append((name, body.get("built"), body.get("commit_at_build"), h.get("last-modified"), h.get("age"), h.get("x-vercel-cache"), str(h.get("x-vercel-id", "")).split("::")[0]))
    print(f"{name:<15} built={body.get('built')} commit={body.get('commit_at_build')} next_days={body.get('next_days')!r} "
          f"next_status={body.get('next_status')} | last-modified={h.get('last-modified')} age={h.get('age')} "
          f"cache={h.get('x-vercel-cache')} edge={str(h.get('x-vercel-id','')).split('::')[0]}")
    time.sleep(2)
bodies = {s[1:3] for s in seen}
lm = {s[3] for s in seen}
print("one body across clients:", len(bodies) == 1, "| one last-modified:", len(lm) == 1)
