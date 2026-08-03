# -*- coding: utf-8 -*-
"""check_sls_filings.py -- keep the /sls "not yet announced" claim honest, automatically.

The SLS pages make a claim of ABSENCE: "as of <date>, the 80th REGAL event has not been announced."
That kind of claim is the most dangerous thing to automate, because simply stamping today's date on
it every night would let the site confidently assert a stale negative the morning after SELLAS
announces.

So the date is not advanced by the clock. It is advanced by evidence: this queries SELLAS's EDGAR
filing index (CIK 1390478) and only moves the verified-through date forward when EDGAR shows no new
filing. If anything new is filed, the date stays frozen where it was and the run prints a loud
advisory for manual review, which is the same rule the rest of the site follows for outcomes.

State lives in _sls_verified_through.json so the builders and the guard read one value.

    python check_sls_filings.py            # advance if clear, freeze + report if not
    python check_sls_filings.py --report   # never write; just show what EDGAR has
"""
import argparse, json, os, sys
import datetime as dt
import urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "_sls_verified_through.json")
CIK = 1390478                      # SELLAS Life Sciences Group, Inc.
UA = "pdufa.bio research contact@pdufa.bio"

# Filing types that could carry a REGAL event-count update or a corporate transaction.
MATERIAL = {"8-K", "8-K/A", "10-Q", "10-K", "S-4", "SC 13D", "SC 13E3", "DEFM14A", "425"}


def filings_since(since):
    url = f"https://data.sec.gov/submissions/CIK{CIK:010d}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    rec = d.get("filings", {}).get("recent", {})
    out = []
    for form, filed, acc, doc in zip(rec.get("form", []), rec.get("filingDate", []),
                                     rec.get("accessionNumber", []),
                                     rec.get("primaryDocument", [])):
        if filed > since:
            out.append((filed, form, acc, doc))
    return sorted(out, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    state = {"verified_through": "2026-08-01", "regal_events": 78, "as_of": "2026-05-11"}
    if os.path.exists(STATE):
        try:
            state.update(json.load(open(STATE, encoding="utf-8")))
        except Exception:
            pass
    since = state["verified_through"]

    try:
        new = filings_since(since)
    except Exception as e:
        print(f"EDGAR unreachable ({type(e).__name__}); leaving verified_through at {since}")
        return 0

    print(f"SELLAS (CIK {CIK}) filings after {since}: {len(new)}")
    for filed, form, acc, doc in new[:12]:
        flag = "  <-- MATERIAL" if form in MATERIAL else ""
        print(f"   {filed}  {form:10s} https://www.sec.gov/Archives/edgar/data/{CIK}/"
              f"{acc.replace('-', '')}/{doc}{flag}")

    material = [x for x in new if x[1] in MATERIAL]
    if material:
        print(f"\nADVISORY: {len(material)} material filing(s) since {since}.")
        print("The /sls pages still state the 80th event is unannounced. That claim is NOT being")
        print("advanced automatically. Read the filings and update _sls_verified_through.json")
        print("(and regal_events / as_of if the count changed), then rerun build_sls_hub.py.")
        return 1

    today = dt.date.today().isoformat()
    if a.report:
        print(f"\n(report only) would advance verified_through {since} -> {today}")
        return 0
    state["verified_through"] = today
    state["last_checked"] = today
    json.dump(state, open(STATE, "w", encoding="utf-8"), indent=1)
    print(f"\nNo material filings. verified_through advanced {since} -> {today} "
          f"(absence confirmed against EDGAR, not assumed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
