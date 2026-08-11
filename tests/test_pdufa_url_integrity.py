# -*- coding: utf-8 -*-
"""test_pdufa_url_integrity.py -- a live catalyst's URL must never resolve to a decided event.

Red team, 2026-08-11, T-2 before Lantheus's PDUFA: /pdufa/LNTH 308-redirected to the June CRL for
LNTH-2501 while the canonical url for the upcoming Aug 13 MK-6240 decision was that same
/pdufa/LNTH. Wrong-drug landing at exactly the moment search volume peaks. Six tickers were in
that state, and the mechanism regenerates itself: bare-ticker redirects are written when a
ticker's only story is finished, then silently become wrong when the same ticker gets a new
catalyst. ARQT showed the worst failure mode -- same brand, different strength, so the reader
concludes the pending product is already approved.

Two invariants, checked against the live dataset every run:

  1. NO bare /pdufa/{TICKER} redirect in vercel.json for any ticker with an upcoming PDUFA.
     (Drug-slugged redirects like /pdufa/LNTH-lnth-2501 name a specific finished event and are
     always allowed.)
  2. /pdufa/{TICKER}/index.html EXISTS for every such ticker and mentions at least one upcoming
     drug by name -- so the URL serves the live story, whether as a rich event page or as the
     ticker index build_pdufa_ticker_index.py writes.

build_pdufa_ticker_index.py is the fixer; this guard proves it ran and won.
"""
import datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
STOP = {"the", "with", "plus", "and", "for", "cream", "tablet", "tablets", "capsule", "capsules",
        "injection", "oral", "dose", "low", "high", "weekly", "daily", "patch", "gel", "solution",
        "spray", "extended", "release", "acid", "sodium", "hydrochloride"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(s or "").lower())
            if len(w) >= 3 and w not in STOP and not w.isdigit()}


def main():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
               encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    up = {}
    for r in rows:
        if (r.get("type") == "PDUFA" and r.get("t")
                and str(r.get("st", "")).lower() != "decided" and str(r.get("d", "")) >= TODAY):
            up.setdefault(str(r["t"]).upper(), set()).update(toks(r.get("name")))

    cfg = json.load(open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
    bad = []
    for rd in cfg.get("redirects", []):
        m = re.match(r"^/pdufa/([A-Z]{1,6})$", str(rd.get("source", "")))
        if m and m.group(1) in up:
            bad.append(f"/pdufa/{m.group(1)} redirects to {rd.get('destination')} while "
                       f"{m.group(1)} has an upcoming PDUFA -- a live catalyst resolving to a "
                       f"dead event")

    for t, names in sorted(up.items()):
        p = os.path.join(SITE, "pdufa", t, "index.html")
        if not os.path.exists(p):
            bad.append(f"/pdufa/{t} has neither page nor (permitted) redirect: 404 for a ticker "
                       f"with an upcoming PDUFA -- run build_pdufa_ticker_index.py")
            continue
        doc = html.unescape(re.sub(r"<[^>]+>", " ",
                                   open(p, encoding="utf-8", errors="replace").read()))
        if names and not (names & toks(doc)):
            bad.append(f"/pdufa/{t} exists but never names any upcoming drug "
                       f"({', '.join(sorted(names)[:4])}...) -- the page is about a past event")

    if bad:
        print(f"FAIL: {len(bad)} /pdufa URL(s) point a live catalyst at the wrong story.")
        for b in bad[:10]:
            print(f"   {b}")
        print("\n   Fix: python build_pdufa_ticker_index.py  (drops stale bare-ticker redirects,")
        print("   writes /pdufa/{T} as the ticker's event index).")
        return 1
    print(f"  PASS: {len(up)} tickers with upcoming PDUFAs; every /pdufa/{{T}} URL serves the "
          f"live story, none redirects to a decided event")
    return 0


if __name__ == "__main__":
    sys.exit(main())
