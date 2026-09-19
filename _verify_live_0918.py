# -*- coding: utf-8 -*-
"""Live verification of the 09-18 pass from a non-browser client."""
import json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
H = {"User-Agent": "pdufa-verify/1.0", "Cache-Control": "no-cache"}


def get(p):
    return urllib.request.urlopen(urllib.request.Request("https://www.pdufa.bio" + p, headers=H),
                                  timeout=90).read().decode("utf-8", "replace")


api = json.loads(get("/api/v1/events?limit=1000"))
rows = api.get("data") or []
print("API rows:", len(rows), "| as_of:", (api.get("meta") or {}).get("as_of"))
up = [r for r in rows if r.get("type") == "PDUFA" and r.get("status") == "Upcoming"]
print("upcoming PDUFA:", len(up), "| with source_url:", sum(1 for r in up if r.get("source_url")))

lly = next((r for r in rows if r.get("id") == "pdufa_lly_2026-09-18"), None)
print("\nLLY imlunestrant row:", {k: lly.get(k) for k in
      ("date", "status", "outcome", "decision_date", "url", "source_url")} if lly else "MISSING")

for p, needle in [("/fda-decision/LLY-2026-09-18", "imlunestrant"),
                  ("/drug/inluriyo", "FDA decisions on record")]:
    t = get(p)
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    print(f"\n{p}: {ti.group(1)[:88] if ti else '?'}")
    if p.startswith("/drug"):
        m = re.search(r"(\d+) FDA decisions? on record", t)
        links = set(re.findall(r'href="(/fda-decision/[^"]+)"', t))
        print("   says:", m.group(0) if m else "?", "| distinct decision links:", len(links))

for p in ("/research/fda-decision-timing", "/calendar", "/learn/does-the-fda-decide-early"):
    t = get(p)
    m = re.search(r"(\d+) FDA decisions in 2026[^.]*?(\d+) came before[^,]*, (\d+) landed on it, and (\d+)", t)
    m2 = re.search(r"(\d+) (?:of them |)came before the goal date, (\d+) landed on it, and (\d+)", t)
    hit = m or m2
    print(f"\n{p}: timing sentence -> {hit.group(0)[:130] if hit else 'pattern not found'}")

t = get("/decisions/approvals")
dead = [h for h in set(re.findall(r'href="(/fda-decision/[^"]+)"', t))
        if h in ("/fda-decision/AZN-2026-06-30", "/fda-decision/GSK-2026-06-18",
                 "/fda-decision/SPRO-2026-06-18", "/fda-decision/VRDN-2026-06-29",
                 "/fda-decision/VRDN-2026-06-30")]
print("\n/decisions/approvals still links the 5 dead targets:", dead or "none")

nav = get("/")
print("/ nav links /pricing:", 'href="/pricing"' in nav, "| links /developers#tiers:",
      'href="/developers#tiers"' in nav)
bi = json.loads(get("/build-info.json"))
print("\nbuild-info:", bi)
