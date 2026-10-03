# -*- coding: utf-8 -*-
"""sync_archive_fda_dates.py -- FDA action dates for archive decision pages that have no dataset row.

Audit 2026-10-03, item 2.1: the fact-first sentence says "was approved by the FDA on {date}" only when
the FDA's own record dates the action. sync_fda_action_dates.py covers the API rows; ~80 approved
decision pages come from the decisions archive and carry only the announcement day. This asks
Drugs@FDA (openFDA) for each, and records a date ONLY when it is unambiguous:

  * an application whose brand or generic matches the page's drug (ANDAs never match);
  * exactly ONE decision-class AP submission (ORIG, or a supplement whose class is not labeling /
    manufacturing / REMS / packaging) in the 24 days around the page date (-20 .. +3), so a brand
    with several supplements in flight never gets one of them by proximity;
  * and that one submission dated 0 to 4 days BEFORE the announcement (or the same day).

Anything else is recorded with its reason and the page keeps the announcement wording. CBER products
(vaccines, gene and cell therapies) are not in Drugs@FDA and stay unmatched. Writes
_fda_action_archive.json; re-checks unmatched pages at most weekly. Facts only.

    python sync_archive_fda_dates.py [--force]
"""
import argparse
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from drug_names import clean_drug_name  # noqa: E402
from watch_fda_approvals import is_decision_submission  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(HERE, "_fda_action_archive.json")
API = "https://api.fda.gov/drug/drugsfda.json"
STOP = {"injection", "tablets", "tablet", "capsules", "solution", "extended", "release", "nasal", "spray",
        "inhalation", "aerosol", "generic", "oral", "subcutaneous", "intravenous", "fixed", "dose"}


def terms(name):
    n = clean_drug_name(name)
    out = []
    lead = re.match(r"\s*([A-Za-z][A-Za-z0-9-]{3,})", n)
    if lead and lead.group(1).lower() not in STOP:
        out.append(lead.group(1))
    for par in re.findall(r"\(([^)]+)\)", n):
        w = re.match(r"\s*([A-Za-z][a-z-]{4,})", par)
        if w and w.group(1).lower() not in STOP and w.group(1) not in out:
            out.append(w.group(1))
    return out[:2]


def query(term):
    t = urllib.parse.quote(f'"{term.upper()}"')
    url = f"{API}?search=openfda.brand_name:{t}+OR+openfda.generic_name:{t}+OR+products.brand_name:{t}&limit=20"
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return json.load(r).get("results", [])
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    have = {(r["t"], r.get("dcd")) for r in rows if (r.get("_d") or {}).get("fda_action_date")}
    cache = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    today = dt.date.today()
    found = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, day = m.group(1), m.group(2)
        if (tk, day) in have:
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if 'class="ban ap"' not in doc:
            continue
        ent = cache.get(slug) or {}
        if ent.get("date") and not a.force:
            found += 1
            continue
        if ent.get("checked") and not a.force and (today - dt.date.fromisoformat(ent["checked"])).days < 7:
            skipped += 1
            continue
        k = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", doc)
        name = html.unescape(k.group(1)) if k else ""
        if not name:
            t = re.search(r"<title>(.*?)</title>", doc, re.S)
            name = html.unescape(re.split(r"\s+(?:Approved|FDA Approval|Approval Announced)\b", t.group(1))[0]) if t else ""
        pd_ = dt.date.fromisoformat(day)
        cands = {}
        for term in terms(name):
            for res in query(term):
                appl = str(res.get("application_number", ""))
                for s in res.get("submissions", []) or []:
                    if not is_decision_submission(appl, s):
                        continue
                    sd = str(s.get("submission_status_date", ""))
                    if not re.match(r"^\d{8}$", sd):
                        continue
                    d = dt.date(int(sd[:4]), int(sd[4:6]), int(sd[6:8]))
                    if -20 <= (d - pd_).days <= 3:
                        letter = next((x.get("url") for x in s.get("application_docs", []) or []
                                       if x.get("type") == "Letter"), None)
                        cands[(appl, s.get("submission_type"), s.get("submission_number"))] = (d, letter, s.get("submission_class_code"))
            time.sleep(0.25)
        rec = {"checked": today.isoformat(), "name": name, "terms": terms(name)}
        if len(cands) == 1:
            (appl, st, sn), (d, letter, cls) = next(iter(cands.items()))
            if 0 <= (pd_ - d).days <= 4:
                appl_fmt = re.sub(r"^(NDA|BLA)(\d+)$", r"\1 \2", appl)
                rec.update({"date": d.isoformat(), "record": f"{appl_fmt} {st}-{sn}", "class": cls,
                            "letter": letter,
                            "source_url": (letter or f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?"
                                                     f"event=overview.process&ApplNo={appl[-6:]}")})
                found += 1
            else:
                rec["reason"] = f"one decision-class approval ({appl} {st}-{sn}) but dated {d}, outside 0-4 days before {day}"
        elif not cands:
            rec["reason"] = "no decision-class Drugs@FDA approval near this date (CBER product, or not yet posted)"
        else:
            rec["reason"] = f"{len(cands)} decision-class approvals within -20..+3 days: ambiguous, not assigned"
        cache[slug] = rec
        print(f"  {slug}: {rec.get('date') or '-'} {rec.get('record') or rec.get('reason')}")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"archive FDA dates: {found} archive page(s) dated by Drugs@FDA; {skipped} skipped (checked this week)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
