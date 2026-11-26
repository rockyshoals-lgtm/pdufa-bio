# -*- coding: utf-8 -*-
"""One source of the conference run-up facts every public surface quotes.

Red team 2026-09-06d: the numbers go on every /conference/* page, the /conferences lede,
the /research card and the study page. Four surfaces hand-typing the same figures is how
"256 presentations" and "Mean price path … 1,754" went stale on /research while the study
said 1,425 and 1,845. So every surface imports THIS and never types a number.

Sources: _conference_runup_stats.json (medians, n, pct_up; tiers are point-in-time
`cap_tier_pit`) and conf_study/conference_runup_PUBLISHED.csv (the 1,425 rows, for the
quartiles and tail shares the JSON does not carry). Tier membership here is `cap_tier_pit`
to match the JSON -- the CSV also carries a stale `cap_tier_final` column that gives
different n (306 vs 666 for nano+micro+small); do not mix them.

Vocabulary rule: everything returned here is a measurement. No caller may attach a verb.
"""
import csv
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STATS = os.path.join(HERE, "_conference_runup_stats.json")
CSVF = os.path.join(HERE, "conf_study", "conference_runup_PUBLISHED.csv")
TIER_COL = "cap_tier_pit"

# Red team 2026-11-26: the old wording ("anchored on the meeting start date") was false. Each row's
# anchor is the day that row was recorded in our catalyst history: the abstract release for some
# meetings (37 of 90 ASCO 2024 rows sit on the abstract-release days), the presentation day for others (ASH
# 2024 rows sit on the meeting days). anchor_audit() counts the rows that sit far from their meeting.
ANCHOR_CAVEAT = ("anchored on the date our catalyst history records for each row: the abstract "
                 "release for some rows, the presentation day for others (even within one meeting), "
                 "and for some rows a date outside the named meeting")
FAR_DAYS = 14
SELECTION_CAVEAT = ("Companies choose what to present; part of any difference between "
                    "presenters and non-presenters is that choice.")
NOT_FORECAST = "This measures what happened; it is not a forecast for any company."


def _q(vals, p):
    vals = sorted(vals)
    if not vals:
        return None
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return round(vals[f] + (vals[c] - vals[f]) * (k - f), 2)


def _fmt(x):
    """Signed percent with the minus sign as a real minus, never a hyphen."""
    if x is None:
        return "n/a"
    s = f"{x:+.2f}%".replace("+", "+").replace("-", "−")
    return s if abs(x) >= 0.005 else "0.00%"


def load():
    stats = json.load(io.open(STATS, encoding="utf-8"))
    rows = list(csv.DictReader(io.open(CSVF, encoding="utf-8-sig", errors="replace")))
    out = {"n": stats["_events"], "overall": stats["overall"], "by_cap": stats["by_cap"],
           "by_conference": stats.get("by_conference", {}),
           "quartiles": {}, "tails": {}, "fmt": _fmt,
           "anchor_caveat": ANCHOR_CAVEAT, "selection_caveat": SELECTION_CAVEAT,
           "not_forecast": NOT_FORECAST}
    for col in ("runup_30d", "runup_20d", "runup_10d", "runup_5d", "event_day",
                "post_5d", "post_10d"):
        v = [float(r[col]) for r in rows if r.get(col) not in ("", None)]
        out["quartiles"][col] = {"n": len(v), "p25": _q(v, .25), "p50": _q(v, .5),
                                 "p75": _q(v, .75)}
    small = [float(r["runup_30d"]) for r in rows
             if r.get(TIER_COL) in ("nano", "micro", "small") and r.get("runup_30d")]
    if small:
        out["tails"]["small_caps_30d"] = {
            "n": len(small),
            "pct_up_25": round(sum(1 for x in small if x >= 25) / len(small) * 100, 1),
            "pct_down_25": round(sum(1 for x in small if x <= -25) / len(small) * 100, 1)}
    return out


def anchor_audit(rows=None):
    """Among rows in meeting-year groups of 3 or more (conf, year), the rows whose anchor sits more
    than FAR_DAYS from that group's median anchor (the row itself included in the median); and the
    rows with no meeting name. A flag, not a verdict: real abstract-release rows (ASH posts abstracts
    about five weeks early) can sit that far too. Computed from the CSV, never typed."""
    import datetime as _dt
    import statistics as _st
    if rows is None:
        rows = list(csv.DictReader(io.open(CSVF, encoding="utf-8-sig", errors="replace")))
    groups = {}
    for r in rows:
        try:
            d = _dt.date.fromisoformat(str(r.get("anchor", ""))[:10])
        except ValueError:
            continue
        groups.setdefault((r.get("conf", ""), str(r.get("year", ""))), []).append(d)
    far = checked = 0
    for (conf, _y), ds in groups.items():
        if conf == "UNKNOWN" or len(ds) < 3:
            continue
        checked += len(ds)
        mid = _dt.date.fromordinal(int(_st.median(x.toordinal() for x in ds)))
        far += sum(1 for x in ds if abs((x - mid).days) > FAR_DAYS)
    unknown = sum(1 for r in rows if r.get("conf") == "UNKNOWN")
    named = len({r.get("conf") for r in rows if r.get("conf") and r.get("conf") != "UNKNOWN"})
    return {"far": far, "checked": checked, "unknown": unknown, "named_meetings": named, "far_days": FAR_DAYS,
            "n": len(rows)}


def audit_sentence(a=None):
    a = a or anchor_audit()
    return (f"Of the {a['checked']:,} rows in meeting-years with three or more rows, "
            f"{a['far']:,} sit more than {a['far_days']} days from that group's median date; "
            f"that flags rows dated to another meeting, but also some genuine abstract-release "
            f"rows, and where most of a group sits off its meeting it flags the on-meeting rows "
            f"instead, so it is a flag count, not a count of misdated rows. The "
            f"{a['n'] - a['checked'] - a['unknown']:,} rows in smaller meeting-years are not "
            f"checked. {a['unknown']:,} rows carry no meeting name. All of these rows are counted "
            f"in the headline figures until they are re-checked against their sources.")


def block_sentence(f):
    """The one paragraph for every conference page. Numbers from the data, never typed."""
    o, bc, q = f["overall"], f["by_cap"], f["quartiles"]["runup_30d"]
    return (
        f"Across {f['n']:,} presentations at major medical meetings from 2017 to 2026, the "
        f"median presenting company's stock moved <b>{_fmt(o['runup_30d']['median'])}</b> in "
        f"the 30 trading days before its anchor day "
        f"({o['runup_30d']['pct_up']}% rose) and "
        f"<b>{_fmt(o['post_5d']['median'])}</b> in the 5 trading days after "
        f"({o['post_5d']['pct_up']}% rose). Small caps: {_fmt(bc['small']['runup_30d']['median'])} "
        f"before (n={bc['small']['runup_30d']['n']}); nano caps: "
        f"{_fmt(bc['nano']['runup_30d']['median'])} (n={bc['nano']['runup_30d']['n']}). The "
        f"middle half of all presenters ranged from {_fmt(q['p25'])} to {_fmt(q['p75'])}. "
        f"The study is {ANCHOR_CAVEAT}. {NOT_FORECAST}")


if __name__ == "__main__":
    f = load()
    print(block_sentence(f))
    print(f["tails"])
