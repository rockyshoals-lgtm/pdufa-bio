# -*- coding: utf-8 -*-
"""Live verification of commit 00106da20 (09-19) from a non-browser client."""
import json, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "https://www.pdufa.bio"
UA = {"User-Agent": "pdufa-builder-verify/0919"}

def get(p):
    r = urllib.request.urlopen(urllib.request.Request(B + p, headers=UA), timeout=30)
    return r.status, r.read().decode("utf-8", "replace")

ok = True
def chk(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

# 1. API rows
s, t = get("/api/v1/events?limit=2000")
ev = json.loads(t); rows = ev["data"] if isinstance(ev, dict) and "data" in ev else ev
by = {r["id"]: r for r in rows}
rare = by.get("pdufa_rare_2026-09-19"); tlx = by.get("pdufa_tlx_2026-09-11")
chk("API RARE decided/approved 09-17", rare and rare.get("status") == "Decided" and rare.get("outcome") == "Approved"
    and rare.get("decision_date") == "2026-09-17", json.dumps({k: rare.get(k) for k in ("status", "outcome", "decision_date", "url")}) if rare else "row missing")
chk("API TLX decided/approved 09-14", tlx and tlx.get("status") == "Decided" and tlx.get("outcome") == "Approved"
    and tlx.get("decision_date") == "2026-09-14", json.dumps({k: tlx.get(k) for k in ("status", "outcome", "decision_date", "url")}) if tlx else "row missing")
fut_dec = [r["id"] for r in rows if r.get("status") == "Decided" and not r.get("outcome")]
chk("no Decided rows without outcome", not fut_dec, str(fut_dec[:5]))

# 2. decision pages
for p, needle in (("/fda-decision/RARE-2026-09-17", "FAYUVI"), ("/fda-decision/TLX-2026-09-14", "Pixclara")):
    try:
        s, t = get(p); chk(f"{p} 200 + '{needle}'", s == 200 and needle in t, f"status {s}")
    except Exception as e:
        chk(f"{p} 200", False, str(e))

# 3. calendar
s, cal = get("/calendar")
sent = re.search(r"30 FDA decisions in 2026[^.]*19 came before the goal date, 7 landed on it, and 4 came after", cal)
chk("calendar timing sentence 30/19/7/4", sent is not None, sent.group(0)[:120] if sent else "not found")
for tk, href in (("ABEO / RARE", "/fda-decision/RARE-2026-09-17"), ("TLX", "/fda-decision/TLX-2026-09-14")):
    m = re.search(rf'<a class="row" data-dec="1" href="{re.escape(href)}">(?:(?!</a>).)*?</a>', cal, re.S)
    chk(f"calendar {tk} row marked decided -> {href}", m and "Approved" in m.group(0) and tk in m.group(0),
        (m.group(0)[:160] if m else "row not found"))

# 4. other timing surfaces
for p in ("/learn/what-is-a-pdufa-date", "/research/fda-decision-timing"):
    s, t = get(p); chk(f"{p} says 19 of 30", "19 of 30" in t, (re.search(r"\d+ of \d+ came", t) or [""])[0] if not "19 of 30" in t else "")

# 5. build-info
s, t = get("/build-info.json"); bi = json.loads(t)
chk("build-info next = MRK 2026-09-21 upcoming", bi.get("next_ticker") == "MRK" and bi.get("next_date") == "2026-09-21",
    json.dumps({k: bi.get(k) for k in ("next_ticker", "next_date", "next_status", "next_days", "commit", "as_of")}))

# 6. /pricing IS live (vercel.json rewrite -> pricing.html; the 09-18 "never existed" claim was wrong)
#    and the frozen nav's Pro entry points at it again on every page
s, t = get("/pricing"); chk("/pricing 200 + pricing title", s == 200 and "Pricing" in t[:600], f"status {s}")
for p in ("/calendar", "/developers", "/fda-decision/RARE-2026-09-17"):
    s, t = get(p); chk(f"{p} nav Pro -> /pricing", '<a class="pro" href="/pricing"' in t and "developers#tiers" not in t)
s, t = get("/pdufa/RPRX"); chk("/pdufa/RPRX shows decision banner", "under FDA review" not in t and ("approved" in t.lower()), "")

# 7. duplicate canonical
s, t = get("/pdufa/TLX-tlx101-px"); chk("/pdufa/TLX-tlx101-px canonical->TLX noindex",
    'canonical" href="https://www.pdufa.bio/pdufa/TLX"' in t and "noindex,follow" in t)

print("\nALL PASS" if ok else "\nSOME FAILED")
