# -*- coding: utf-8 -*-
"""build_readout_forward.py -- the estimated-readouts table on /readouts, rebuilt from the dataset every run.

WHY THIS EXISTS (red team 2026-11-26). The month-by-month table of ClinicalTrials.gov estimates below the
company-guided list had no builder: it was written once by build_category_calendars.py from an old crawler CSV
and only ever pruned since. Measured on 2026-11-26 it carried 159 estimate rows, and 52 of them were wrong:
31 had no row in the dataset at all (trials since dropped, companies since acquired), 21 showed a different
month from the one the dataset now holds (IOVA "Nov 2026" for a trial the registry moved to Nov 2027). It also
carried 22 company "H2 2026 / Q4 2026" rows lifted from 2024-25 SEC exhibits that nobody re-checked; on
2026-11-26 five of the ten we checked had already read out and four had slipped into 2027. Its footer said
"728 upcoming readouts" while the lede said 195 and the FAQ 477. Nothing on the page was lying on purpose; the
table simply had no owner.

WHAT IT DOES. Every forward Estimated readout row in the dataset (window month >= this month, by the row's
event date `d`, which is the truth per build_readout_results.py) that links a ClinicalTrials.gov record is
rendered under its month, in the same row shape the page has always used. The text after the drug name is the
trial's own condition list from the registry, and each row says which NCT record it is and that record's status
as the registry gives it. Rows with no trial record are not published here: an "estimate" with nothing to
estimate from is not a date. Company-guided dates live in the table above (build_guided_readouts.py), so the
old exhibit rows are not carried over.

REGISTRY FACTS. _readout_registry_cache.json holds status, primary completion, conditions and interventions per
NCT. Each run re-reads the registry for the NCTs it needs (ClinicalTrials.gov v2 API, no key); a failed fetch
keeps the last good entry. It never sets a date, an outcome or a status on a dataset row: the dates come from the
dataset, which refresh_readout_registry.py keeps equal to the registry.

    python build_readout_forward.py [--offline] [--dry-run]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
PAGE = os.path.join(SITE, "readouts", "index.html")
CACHE = os.path.join(HERE, "_readout_registry_cache.json")
API = ("https://clinicaltrials.gov/api/v2/studies/{nct}?fields=protocolSection.statusModule,"
       "protocolSection.conditionsModule,protocolSection.armsInterventionsModule")
UA = "pdufa.bio readout builder"

BEGIN, END = "<!--FWDEST:BEGIN-->", "<!--FWDEST:END-->"
AFTER, BEFORE = "<!--/readout-results-->", "<!--HUBFAQ:BEGIN-->"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
MON3 = [m[:3] for m in MONTHS]
STATUS_WORDS = {
    "RECRUITING": "recruiting", "ACTIVE_NOT_RECRUITING": "active, not recruiting",
    "NOT_YET_RECRUITING": "not yet recruiting", "ENROLLING_BY_INVITATION": "enrolling by invitation",
    "COMPLETED": "completed", "TERMINATED": "terminated", "SUSPENDED": "suspended",
    "WITHDRAWN": "withdrawn", "UNKNOWN": "status unknown",
}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def today():
    """The calendar date in New York: /readouts is a US-market page and every other builder uses ET."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:  # noqa: BLE001
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def load_rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return rows


def nct_of(r):
    raw = (r.get("_d") or {}).get("nct_id")
    n = raw.get("nct") if isinstance(raw, dict) else raw
    n = str(n or "").strip().upper()
    return n if re.match(r"^NCT\d{8}$", n) else ""


def forward_rows(rows, td=None):
    """Forward Estimated readouts that link a trial record: the exact set the table publishes (the guard
    tests/test_readout_forward_matches_dataset.py recomputes it with this function)."""
    cur = (td or today()).strftime("%Y-%m")
    out = []
    for r in rows:
        if r.get("type") != "Readout" or str(r.get("st") or "") != "Estimated" or not r.get("t"):
            continue
        ym = str(r.get("d") or "")[:7]
        if not re.match(r"^\d{4}-\d{2}$", ym) or ym < cur:
            continue
        out.append(r)
    out.sort(key=lambda r: (str(r.get("d")), str(r.get("t")), str(r.get("id"))))
    return [r for r in out if nct_of(r)], [r for r in out if not nct_of(r)]


def fetch(nct):
    req = urllib.request.Request(API.format(nct=nct), headers={"User-Agent": UA})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    ps = d.get("protocolSection") or {}
    st = ps.get("statusModule") or {}
    pc = st.get("primaryCompletionDateStruct") or {}
    return {
        "status": st.get("overallStatus"),
        "pcd": pc.get("date"),
        "conditions": list((ps.get("conditionsModule") or {}).get("conditions") or [])[:3],
        "interventions": [i.get("name") for i in ((ps.get("armsInterventionsModule") or {})
                                                   .get("interventions") or []) if i.get("name")][:4],
    }


def refresh_cache(ncts, offline):
    try:
        cache = json.load(open(CACHE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cache = {"_note": "", "trials": {}}
    trials = cache.setdefault("trials", {})
    ok = fail = 0
    if not offline:
        for n in ncts:
            got = fetch(n)
            if got and got.get("status"):
                got["checked"] = today().isoformat()
                trials[n] = got
                ok += 1
            else:
                fail += 1
            time.sleep(0.25)
        if ok:
            cache["checked"] = today().isoformat()
    print(f"registry: {ok} re-read, {fail} failed (kept last good entry), "
          f"{sum(1 for n in ncts if n not in trials)} with no entry")
    return cache


def condition_text(c):
    conds = [x.strip() for x in (c or {}).get("conditions") or [] if str(x).strip()]
    return ", ".join(conds[:2])


def render(fwd, cache, n_unsourced):
    trials = cache.get("trials") or {}
    by_month = {}
    for r in fwd:
        by_month.setdefault(str(r["d"])[:7], []).append(r)
    parts = [BEGIN]
    for ym in sorted(by_month):
        y, m = int(ym[:4]), int(ym[5:7])
        parts.append(f'<div class="mhead">{MONTHS[m - 1]} {y}</div><div class="grid">')
        for r in by_month[ym]:
            n = nct_of(r)
            c = trials.get(n) or {}
            cond = condition_text(c)
            name = re.sub(r"\s+", " ", str(r.get("name") or "")).strip()
            desc = esc(name[:120]) + (f": {esc(cond[:110])}" if cond else "")
            st = STATUS_WORDS.get(str(c.get("status") or ""), "")
            src = f"{n}" + (f", registry status {st}" if st else "")
            parts.append(
                f'<a class="row" href="https://clinicaltrials.gov/study/{n}" rel="nofollow">'
                f'<div class="t">{esc(r["t"])} &middot; {MON3[m - 1]} {y} (est.)</div>'
                f'<div class="d">{desc} <span style="color:#94a9c9">&middot; {esc(src)}</span></div></a>')
        parts.append("</div>")
    n = len(fwd)
    first = min(by_month) if by_month else None
    note = (f"{n} estimated readout{'s' if n != 1 else ''} in this table"
            + (f", from {MONTHS[int(first[5:7]) - 1]} {first[:4]}" if first else "")
            + ". Each date is the primary-completion month that ClinicalTrials.gov gives for the linked trial "
              "record, which sponsors move; it is when the trial is expected to finish collecting its main "
              "data, not an announced readout date, and a company may report later or never. Dates a company "
              "has stated itself are in the company-guided table above.")
    if n_unsourced:
        note += (f" {n_unsourced} further estimate{'s' if n_unsourced != 1 else ''} with no trial record on "
                 f"file {'are' if n_unsourced != 1 else 'is'} not shown.")
    parts.append(f'<div class="note" style="margin-top:18px">{note}</div>')
    parts.append(END)
    return "".join(parts)


def inject(doc, block):
    if BEGIN in doc and END in doc:
        a = doc.index(BEGIN)
        b = doc.index(END) + len(END)
        return doc[:a] + block + doc[b:]
    a, b = doc.find(AFTER), doc.find(BEFORE)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("build_readout_forward: anchors not found on /readouts; page left alone")
    a += len(AFTER)
    return doc[:a] + block + doc[b:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="do not re-read the registry; use the cache")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = load_rows()
    fwd, unsourced = forward_rows(rows)
    cache = refresh_cache(sorted({nct_of(r) for r in fwd}), a.offline or a.dry_run)
    block = render(fwd, cache, len(unsourced))
    doc = io.open(PAGE, encoding="utf-8").read()
    new = inject(doc, block)
    # the per-month counts, so the run log shows what changed
    print(f"/readouts estimated table: {len(fwd)} rows, {len(unsourced)} with no trial record left out")
    if a.dry_run:
        print("DRY RUN -- nothing written.")
        return 0
    if new != doc:
        io.open(PAGE, "w", encoding="utf-8", newline="").write(new)
        print("wrote", os.path.relpath(PAGE, HERE))
    if not a.offline:
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        open(CACHE, "a", encoding="utf-8").write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
