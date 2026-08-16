# -*- coding: utf-8 -*-
"""sync_conferences_to_api.py -- the conference API serves what the conference page shows.

Red team 2026-08-16 section 2.2: /conferences showed 41 meetings with presenters and 2027
events while /api/v1/conferences served 14 meetings, 0 presenters, nothing past 2026 -- and
/llms.txt points AI crawlers at the API, so the machine-readable surface we deliberately hand
to engines was four months stale. Same recurring disease: one surface learned, the other
didn't.

This replaces the dataset's type=Conference rows wholesale from conferences.json (the
organiser-verified calendar the page renders) and attaches the SAME gated presenter selection
build_conferences.py publishes -- verified rows, high-confidence mined rows, and history rows
that pass the edition gate. One selection, two surfaces, no divergence possible.

Runs daily right after build_conferences.py.

    python sync_conferences_to_api.py [--dry-run]
"""
import argparse, datetime as dt, json, os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")

sys.path.insert(0, HERE)
import build_conferences as BC


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date().isoformat()

    data = json.load(open(os.path.join(HERE, "conferences.json"), encoding="utf-8"))
    by_code = BC.load_presenters()

    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    kept = [r for r in rows if r.get("type") != "Conference"]

    added = 0
    for c in data["conferences"]:
        pres = BC.presenters_for(c, by_code)
        row = {
            "id": f"conf_{c['code'].lower()}_{c['start']}",
            "t": c["code"], "company": c["name"],
            "d": c["start"], "dp": "day",
            "name": c["name"], "type": "Conference", "ta": c.get("focus", ""),
            "cap": "", "st": ("Ended" if c["end"] < today else "Scheduled"),
            "url": "/conferences",
            "ua": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "_d": {
                "end": c["end"],
                "location": c.get("location", ""),
                "organiser_url": c.get("url", ""),
                "presenters": [
                    {"ticker": (p.get("ticker") or "").upper(),
                     "company": p.get("company", ""),
                     "drug": p.get("drug", ""),
                     "pres_type": p.get("pres_type", ""),
                     "source_url": p.get("source_url", "")}
                    for p in pres],
                "presenter_note": "Presenters are sourced from company filings and releases; "
                                  "this is not the organiser's programme.",
            },
        }
        # insert in date order among all rows
        idx = next((i for i, r in enumerate(kept)
                    if str(r.get("d", "")) > c["start"]), len(kept))
        kept.insert(idx, row)
        added += 1

    n_pres = sum(len(r["_d"]["presenters"]) for r in kept
                 if r.get("type") == "Conference")
    if not a.dry_run:
        open(DATASET, "w", encoding="utf-8").write(
            "export default " + json.dumps(kept, indent=1) + ";\n")
    print(f"conference API sync: {added} conferences (was "
          f"{sum(1 for r in rows if r.get('type') == 'Conference')}), "
          f"{n_pres} presenter entries, dataset now {len(kept)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
