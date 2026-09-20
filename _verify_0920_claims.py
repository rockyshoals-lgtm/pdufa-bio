# -*- coding: utf-8 -*-
"""Verify the 09-20 audit's four claims against LIVE before touching anything."""
import html, json, re, sys, urllib.request, datetime as dt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"; UA = {"User-Agent": "pdufa-builder-verify/0920", "Cache-Control": "no-cache"}
def get(p):
    r = urllib.request.urlopen(urllib.request.Request(B + p, headers=UA), timeout=30); return r.read().decode("utf-8", "replace")
def text(d):
    d = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", d); return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", d)))

ev = json.loads(get("/api/v1/events?limit=2000")); rows = ev["data"] if isinstance(ev, dict) and "data" in ev else ev
by = {r["id"]: r for r in rows}
print("== P0-A TLX")
t = by["pdufa_tlx_2026-09-11"]; print({k: t.get(k) for k in ("status", "outcome", "decision_date", "decision_date_note", "source", "source_url")})
print("API keys on the row:", sorted(t.keys())[:40])
for p in ("/research/fda-decision-timing", "/calendar", "/learn/what-is-a-pdufa-date"):
    x = text(get(p)); m = re.search(r".{0,80}September 14, 2026.{0,80}", x); print(p, "->", m.group(0) if m else "(TLX not quoted)")
print("\n== P0-B /fda-this-month")
x = text(get("/fda-this-month"))
for m in re.finditer(r"Ahead of its [A-Z][a-z]+ \d{1,2} goal date, on [A-Z][a-z]+ \d{1,2}[^.]{0,80}", x): print("  ", m.group(0))
for i in ("pdufa_tak_2026-09-30", "pdufa_pfe_2026-09-30", "pdufa_ptgx_2026-09-30", "pdufa_bayry_2026-11-30"):
    r = by.get(i); print("  ", i, {k: r.get(k) for k in ("date", "date_precision", "status", "decision_date")} if r else "MISSING")
print("\n== P0-C countdown")
bi = json.loads(get("/build-info.json")); print({k: bi.get(k) for k in ("built", "next_ticker", "next_date", "next_days", "next_status", "as_of")})
print("  Eastern now:", dt.datetime.utcnow() - dt.timedelta(hours=4))
print("\n== item 4 lede/meta")
d = get("/fda-this-month"); print("  meta:", re.search(r'<meta name="description" content="([^"]*)"', d).group(1)[:160])
m = re.search(r"\d+ FDA decision dates remain in September 2026[^.]*\.", text(d)); print("  lede:", m.group(0) if m else "-")
sep = [r for r in rows if r.get("type") == "PDUFA" and str(r.get("date") or "").startswith("2026-09") and r.get("status") not in ("Decided",)]
print("  API Sept undecided day rows:", [(r["ticker"], r["date"], r.get("drug")) for r in sep])
