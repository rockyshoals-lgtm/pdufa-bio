# -*- coding: utf-8 -*-
"""sync_screener_data.py -- /screener renders from the dataset, not from a July snapshot.

Red team 2026-11-01: /screener's table is drawn client-side from an inline `const DATA=[...]`, and that array had
not changed since the site's first commit (2026-07-25). 395 rows, 31 of them "Upcoming" with dates already past
(AGIO on Nov 1 after the goal moved to Feb 2027, IGALMI under BioXcel after the sale to Teva, decided approvals
still listed as pending). No step in the workflow ever rewrote it.

This rewrites DATA from api/v1/dataset.mjs every run: same keys the page's JS reads (t, d, name, type, ta, cap, st,
url), names cut at 50 characters as before, rows from 150 days back onward. Idempotent.

Design red team 2026-11-18 (change 1, date precision). The page printed every row's `d` as a day. For 202 estimated
and 236 guided readouts that day is a storage key, not a date anyone stated: "Q4 2026" was shown as 2026-12-31 and a
month as its 15th. Decided PDUFAs stayed under their goal date with a check mark, so a CRL (SMMT) showed a tick and
an approval from September showed as a December catalyst. Now, through site_windows (the one owner of window labels):
  * a row whose stored precision is month, quarter or year carries `w`, its label ("Nov 2026", "Q4 2026", "2026",
    plus " (est.)" when st is Estimated), and `e`, the window's last day, so the From filter keeps an open window;
  * a day-precision row is untouched: an exact day a source gives is printed as that day;
  * a decided PDUFA is placed on the FDA's action date (_d.fda_action_date) with its outcome (oc), so the page marks
    approvals and complete response letters differently and never lists a decided application as upcoming. Only
    when no FDA date is on record does it fall back to the announcement date (dcd), marked "announced".

    python sync_screener_data.py [--dry-run]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "screener", "index.html")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
sys.path.insert(0, HERE)
try:
    from site_dates import eastern_today
except Exception:  # noqa: BLE001
    eastern_today = dt.date.today
from site_windows import is_day, window_label, window_span  # noqa: E402


def date_text(r):
    """What a row prints as its date (also build_screener_rows.py's table): a stated day as that day, a month /
    quarter / year as its window ("Nov 2026", "Q4 2026", "2026"), "Not announced" when the sponsor states no goal
    date, and " (est.)" on pdufa.bio's own estimates."""
    lab = window_label(r)                     # a day row's label is its day; not-announced wins over precision
    return lab + (" (est.)" if r.get("st") == "Estimated" else "")


def screener_row(r):
    """The DATA entry for one dataset row (also used by tests/test_date_precision.py).

    Keys the page reads: t d name type ta cap st url, plus
      w   the printed date when it differs from d (window label, "Not announced", " (est.)");
      s/e the window's first / last day when they differ from d, so From and To filter on the whole window;
      oc  the recorded outcome of a decided PDUFA;
      a   1 when no FDA action date is on record and the row sits on the sponsor's announcement day (dcd);
      ar  the therapeutic area the dropdown filters on (ta folded onto one spelling; "Not classified" when empty)."""
    d = str(r.get("d") or "")
    out = {"t": r.get("t") or "", "d": d, "name": str(r.get("name") or "")[:50], "type": r.get("type"),
           "ta": r.get("ta") or "", "cap": r.get("cap") or "", "st": r.get("st") or "",
           "url": r.get("url") or f"/ticker/{r.get('t')}"}
    out["ar"] = area(out["ta"])
    # change 9: 456 readouts (and two decided PDUFAs) linked straight off-site, to the registry or a press release, while
    # every other row opened its page here. Each now opens the site's own page, which links the same source one click on.
    if str(out["url"]).startswith("http") and out["t"]:
        out["url"] = on_site(r, out)
    decided = r.get("type") == "PDUFA" and r.get("st") == "Decided"
    if decided and r.get("oc"):
        out["oc"] = str(r.get("oc"))
    day = decision_day(r)
    if decided and day:
        out["d"], announced = day
        if announced:
            out["a"] = 1                     # no FDA action date on record: the day the sponsor announced it
        return out
    w = date_text(r)
    if w != d:
        out["w"] = w
    s, e = window_span(r)
    if s and s != d:
        out["s"] = s
    if e and e != d:
        out["e"] = e
    return out


# 2026-11-18 (design red team, change 9): the area dropdown was typed in by hand. 8 of its 23 areas matched no row,
# 102 rows sat in areas it did not offer (Dermatology, Respiratory, Endocrinology, ...), 117 had no area, and spelling
# twins split one area in two (Cardiology / Cardiovascular, Rare disease / Rare Disease). Each row now carries `ar`, its
# area folded onto one name, and the dropdown is written from the rows themselves, so every option
# finds rows and every row can be found. The row still prints its own label (`ta`).
# Order matters: the first pattern that matches wins. Red team: patterns are anchored on word starts, so "Bronchiectasis"
# is not oncology, "Adrenal" not nephrology, "Drug delivery" not hepatology, "Plasma" not neurology, and a rare
# metabolic disease is a rare disease.
AREA_FOLD = [
    (r"\bonc|\bcancer|\btumou?r|\bleuk(?:a)?emi|\blymphom|\bmyelom|\bcarcinom|\bsarcom", "Oncology"),
    (r"\brare\b", "Rare disease"),
    (r"^hae?matolog", "Hematology"),
    (r"\bcardio|\bheart\b", "Cardiovascular"),
    (r"\bcns\b|\bneuro|\balzheimer|\bepilep|\bmultiple sclerosis|\bparkinson|\bpsychiat|\bmigraine|\bdmd\b|\bsma\b",
     "Neurology / CNS"),
    (r"\bdiabet|\bmetabol|\bobesity|\bendocrin", "Metabolic / endocrine"),
    (r"\bhepat|\bliver\b|\bmash\b|\bnash\b|\bgastro|^gi\b", "Gastroenterology / hepatology"),
    (r"\binfect|\bvaccin|\bantivir|\bantibiot", "Infectious disease"),
    (r"\bimmunolog|\ballerg|\brheumat", "Immunology / rheumatology"),
    (r"\bophthalm|\bocular\b|\bretina", "Ophthalmology"),
    (r"\brespir|\bpulmon|\blung\b", "Respiratory"),
    (r"\bmusculo|\bbone\b", "Musculoskeletal"),
    (r"\bnephro|\brenal\b|\bkidney", "Nephrology"),
    (r"\bdermat|\bskin\b", "Dermatology"),
]
NO_AREA = "Not classified"


def area(ta):
    """One filter name for a row's therapeutic-area label. Unknown labels keep their own name, capitalised."""
    t = str(ta or "").strip()
    if not t:
        return NO_AREA
    low = t.lower()
    if low in ("other",) or "investing" in low or low.startswith("gene and cell"):
        return "Other"
    for pat, name in AREA_FOLD:
        if re.search(pat, low):
            return name
    return t[:1].upper() + t[1:]


def one_spelling(rows):
    """Labels no pattern knows keep their own name; two spellings of one ("Women's Health", "Women's health") take the
    commoner, so the dropdown never offers the same area twice."""
    from collections import Counter
    c = Counter(r["ar"] for r in rows)
    best = {}
    for k in sorted(c, key=lambda k: (-c[k], k)):
        best.setdefault(re.sub(r"\s+", " ", k).strip().lower(), k)
    for r in rows:
        r["ar"] = best[re.sub(r"\s+", " ", r["ar"]).strip().lower()]


def on_site(r, out):
    """The site's own page for a row whose source is off-site: the decision page, the PDUFA page, else the company hub
    (at its readout list for a readout). The page links the source."""
    t = out["t"]
    if out["type"] == "Readout":
        return f"/ticker/{t}#readouts"
    if out["type"] == "PDUFA":
        for day in (r.get("dcd"), (r.get("_d") or {}).get("fda_action_date") if isinstance(r.get("_d"), dict) else None,
                    r.get("d")):
            if day and os.path.exists(os.path.join(SITE, "fda-decision", f"{t}-{str(day)[:10]}", "index.html")):
                return f"/fda-decision/{t}-{str(day)[:10]}"
        if os.path.exists(os.path.join(SITE, "pdufa", t, "index.html")):
            return f"/pdufa/{t}"
    if os.path.exists(os.path.join(SITE, "ticker", t, "index.html")):
        return f"/ticker/{t}"
    return out["url"]                   # no page here (a conference code): the source is the only page there is


def area_options(rows):
    """The dropdown's <option>s, built from the rows: largest area first, "Other" and "Not classified" last. No counts
    in the labels: the page filters from today by default, so a count over every row would promise rows it hides."""
    from collections import Counter
    c = Counter(r["ar"] for r in rows)
    order = sorted(c, key=lambda k: (k in ("Other", NO_AREA), k == NO_AREA, -c[k], k))
    esc = lambda x: x.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return '<option value="">All areas</option>' + "".join(
        f'<option value="{esc(k)}">{esc(k)}</option>' for k in order)


def decision_day(r):
    """(day, announced) for a decided PDUFA, or None. The day is the FDA's action date (_d.fda_action_date, from
    sync_fda_action_dates.py). `dcd` is NOT that date: it is the /decisions URL date, set from the sponsor's
    announcement (SMMT's CRL is dated 2026-11-13 by the FDA, announced 2026-11-15). Only when no FDA date is on
    record does the row fall back to `dcd`, marked as the announcement day."""
    if not (r.get("type") == "PDUFA" and r.get("st") == "Decided"):
        return None
    meta = r.get("_d") if isinstance(r.get("_d"), dict) else {}
    fda = str(meta.get("fda_action_date") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fda):
        return fda, False
    dcd = str(r.get("dcd") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dcd):
        return dcd, True
    return None


def sort_key(row):
    """Window end (a day row's own day), exact days before windows that end the same day, then ticker. Sorting by
    the storage day put "Nov 2026 (est.)" rows (stored on the 15th) ahead of Nov 16-30 exact days."""
    return (row.get("e") or row["d"], 1 if row.get("s") else 0, row["t"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    floor = (eastern_today() - dt.timedelta(days=150)).isoformat()
    out = []
    for r in rows:
        if not r.get("d") or r.get("type") not in ("PDUFA", "Readout", "Conference", "AdComm"):
            continue
        row = screener_row(r)
        if max(row["d"], row.get("e", "")) < floor:
            continue
        out.append(row)
    out.sort(key=sort_key)
    one_spelling(out)
    doc = io.open(PAGE, encoding="utf-8").read()
    m = re.search(r"const DATA=(\[.*?\]);\s*\nconst q=", doc, re.S)
    if not m:
        print("::warning::/screener: const DATA not found; nothing written")
        return 0
    new = doc[:m.start(1)] + json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + doc[m.end(1):]
    new = re.sub(r'(<select id="ta"[^>]*>).*?(</select>)', lambda mm: mm.group(1) + area_options(out) + mm.group(2),
                 new, count=1, flags=re.S)
    new = new.replace("(!ta||e.ta===ta)", "(!ta||e.ar===ta)")
    if new != doc and not a.dry_run:
        io.open(PAGE, "w", encoding="utf-8").write(new)
    print(f"/screener DATA: {len(out)} row(s) from the dataset (from {floor})" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
