# -*- coding: utf-8 -*-
"""test_retail_profiles.py -- the deep-dive pages are the most quotable thing we publish.

These pages exist to be read by retail investors days before an FDA decision, in plain English,
about names they are actively trading. That makes them the highest-consequence copy on the site and
the easiest place to do damage: a confident sentence about a trial result, with no source, that a
reader acts on.

The rules this enforces are the ones that make the pages defensible:

  1. Every profile carries the required fields. A half-filled profile must not publish, because a
     stub for a heavily-searched ticker is exactly the thin content that already left 92 hubs
     noindexed and 478 URLs uncrawled.
  2. Every timeline entry and every trial result cites a source URL. No exceptions.
  3. Verdicts come from a fixed vocabulary. "contested" exists specifically because CAPR's HOPE-3
     both met and missed its primary endpoint depending on which statistical plan is used, and
     flattening that into "met" or "missed" would be false either way.
  4. A published block never asserts a stock move without the measured-from-daily-closes wording,
     and never hard-codes a percentage in the profile, because a typed number drifts away from what
     actually happened while a computed one cannot.

    python tests/test_retail_profiles.py
"""
import glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
PROFILES = os.path.join(HERE, "retail_profiles")

REQUIRED = ("ticker", "company", "asset", "plain", "technical", "results", "events", "caveats")
VERDICTS = {"met", "missed", "contested", "note"}
BEGIN, END = "<!--DEEPDIVE:BEGIN-->", "<!--DEEPDIVE:END-->"
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
TODAY = __import__("datetime").datetime.now(
    __import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()


def _live_pdufas():
    if not os.path.exists(DATASET):
        return []
    m = re.search(r"export default (\[.*\])",
                  open(DATASET, encoding="utf-8", errors="replace").read(), re.S)
    rows = json.loads(m.group(1)) if m else []
    return [e for e in rows if e.get("type") == "PDUFA" and e.get("st") == "Upcoming"
            and e.get("dp") == "day" and e.get("d")]


LIVE = _live_pdufas()


def main():
    files = sorted(glob.glob(os.path.join(PROFILES, "*.json")))
    if not files:
        print("no retail profiles yet; nothing to check")
        sys.exit(0)

    ok = True
    print(f"checking {len(files)} retail profile(s)")

    for f in files:
        name = os.path.basename(f)
        try:
            p = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            ok = False
            print(f"  FAIL {name}: not valid JSON ({e})")
            continue

        missing = [x for x in REQUIRED if not p.get(x)]
        if missing:
            ok = False
            print(f"  FAIL {name}: missing {', '.join(missing)}")
            continue

        t = p["ticker"]
        for r in p["results"]:
            if r.get("verdict") not in VERDICTS:
                ok = False
                print(f"  FAIL {t}: result '{r.get('trial','?')}' has verdict "
                      f"{r.get('verdict')!r}; allowed: {sorted(VERDICTS)}")
            for field in ("trial", "plain", "technical", "source"):
                if not r.get(field):
                    ok = False
                    print(f"  FAIL {t}: result '{r.get('trial','?')}' missing {field}")
            if r.get("source") and not str(r["source"]).startswith("http"):
                ok = False
                print(f"  FAIL {t}: result source is not a URL: {r['source']}")

        for e in p["events"]:
            if len(e) != 3:
                ok = False
                print(f"  FAIL {t}: timeline entry is not (date, what, source): {e}")
                continue
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(e[0])):
                ok = False
                print(f"  FAIL {t}: timeline date not ISO: {e[0]}")
            if not str(e[2]).startswith("http"):
                ok = False
                print(f"  FAIL {t}: timeline entry has no source URL: {e[1][:50]}")

        # A hard-coded percentage in a reaction entry means somebody typed a market move instead of
        # letting the builder measure it. That is how a page slowly stops matching reality.
        for rr in (p.get("reactions") or []):
            if re.search(r"[-+]?\d+(\.\d+)?\s*%", str(rr.get("what", ""))):
                ok = False
                print(f"  FAIL {t}: reaction '{rr.get('what')}' hard-codes a percentage. "
                      f"Moves are measured from daily closes at build time, not typed.")

        # 2026-11-18 design red team: CAPR's dossier said "the PDUFA date of 22 August 2026 stands"
        # for three months after the FDA moved it to 22 November, four days before the decision.
        # A dossier whose status still names an expected decision must name the date the dataset
        # carries for that ticker's live PDUFA, and must not name a date already past.
        st = p.get("status") or {}
        if st.get("date") and "expected" in str(st.get("label", "")).lower():
            live = sorted(e["d"] for e in LIVE if str(e.get("t", "")).upper() == t.upper())
            if live and st["date"] not in live:
                ok = False
                print(f"  FAIL {t}: deep dive says the decision is expected {st['date']}, but the "
                      f"dataset's live PDUFA date is {', '.join(live)}. Update the profile's status, "
                      f"its caveats and its timeline, and set status_updated.")
            if st["date"] < TODAY:
                ok = False
                print(f"  FAIL {t}: deep dive still says a decision is expected on {st['date']}, "
                      f"which has passed")
            for cav in p.get("caveats") or []:
                for d in re.findall(r"\b(\d{1,2} (?:January|February|March|April|May|June|July|"
                                    r"August|September|October|November|December) \d{4}) stands", cav):
                    ok = False
                    print(f"  FAIL {t}: caveat says the date of {d} stands; the status says {st['date']}")

        page = os.path.join(SITE, "ticker", t, "index.html")
        if os.path.exists(page):
            doc = open(page, encoding="utf-8", errors="replace").read()
            if BEGIN in doc:
                blk = doc.split(BEGIN, 1)[1].split(END, 1)[0]
                if "not investment advice" not in blk.lower():
                    ok = False
                    print(f"  FAIL {t}: published deep dive is missing the advice disclaimer")
                if 'href="http' not in blk:
                    ok = False
                    print(f"  FAIL {t}: published deep dive cites no sources")
                if "noindex" in doc:
                    ok = False
                    print(f"  FAIL {t}: hub still noindexed despite carrying a full deep dive")
                print(f"  ok   {t}: {len(p['results'])} result(s), {len(p['events'])} timeline "
                      f"entries, block {len(blk):,} bytes")
            else:
                print(f"  note {t}: profile exists but /ticker/{t} carries no deep dive yet "
                      f"(run build_retail_pages.py)")
        else:
            print(f"  note {t}: /ticker/{t} does not exist yet")

    print("\n  PASS: retail profiles are complete and sourced" if ok else "\n  see failures above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
