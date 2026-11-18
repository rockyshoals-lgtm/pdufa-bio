# -*- coding: utf-8 -*-
"""CI guard: an open PDUFA row must not name a drug the FDA's own records already show approved since.

WHY (red team 2026-11-17)
The FDA usually acts EARLY (neladalkib: 10 days before its Nov 27 goal, on Nov 17, 2026). The site
learns about an action from watchers and from our decision pages; test_decided_not_upcoming asserts
the pages and the dataset agree. Neither looks at the FDA's records directly, so an approval that no
watcher heard about (no press release, a quiet sNDA strength approval) leaves the row counting down
to a goal date that has already been decided -- the worst error a PDUFA tracker can publish.

The rebuild already caches two FDA records every day:
  * _fda_novel_approvals.json  -- CDER's Novel Drug Approvals list (brand, ingredient, date);
  * _orange_book/products.txt  -- the Orange Book, every approved NDA product with its approval date.

THE INVARIANT. For every Upcoming / Under review PDUFA row, no FDA record approved AFTER the row's
own source date (and on or before today) may match the row's drug by brand name or by active
ingredient. ANDA (generic) products are ignored. A match is either a decision to record (resolve
the row through the usual decision path) or a different product with the same name: then add
{id, appl_no, why} to _fda_record_ack.json so it never fires again for that application.

    python tests/test_open_goal_not_in_fda_record.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
NOVEL = os.path.join(HERE, "_fda_novel_approvals.json")
OB = os.path.join(HERE, "_orange_book", "products.txt")
ACK = os.path.join(HERE, "_fda_record_ack.json")

# words too generic to identify a drug on their own
STOP = set("""tablet tablets capsule capsules oral film injection solution suspension cream ointment gel
extended release delayed sodium hydrochloride acid phosphate sulfate acetate chloride citrate
inhalation intravenous subcutaneous ophthalmic topical system kit powder lower doses formulation
therapy combination with plus and the for phase""".split())


def eastern_today():
    try:
        from site_dates import eastern_today as et
        return et()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def words(s):
    return {w for w in re.findall(r"[a-z][a-z\-]{4,}", (s or "").lower()) if w not in STOP}


def row_terms(r):
    d = r.get("_d") or {}
    name = r.get("name") or ""
    # the drug part of the name, before any " - indication" / "(TRIAL)" tail
    drug = re.split(r"\s+-\s+|\(\s*[A-Z0-9\-]{3,}\s*\)", name)[0]
    t = words(drug)
    for k in ("brand", "generic", "drug"):
        t |= words(str(d.get(k) or ""))
    return t


def row_source_date(r):
    d = r.get("_d") or {}
    m = re.search(r"(20\d\d-\d\d-\d\d)", str(d.get("source") or ""))
    if m:
        return dt.date.fromisoformat(m.group(1))
    for h in reversed(d.get("date_history") or []):
        v = h.get("changed") or h.get("date")
        if v and re.match(r"\d{4}-\d{2}-\d{2}", v):
            return dt.date.fromisoformat(v[:10])
    return None


def fda_records():
    recs = []
    if os.path.exists(NOVEL):
        for x in json.load(io.open(NOVEL, encoding="utf-8")).get("rows", []):
            try:
                recs.append({"appl_no": "novel:" + x["brand"], "date": dt.date.fromisoformat(x["date"]),
                             "terms": words(x.get("brand")) | words(x.get("ingredient")),
                             "what": f"FDA Novel Drug Approvals: {x['brand']} ({x.get('ingredient')}) {x['date']}"})
            except Exception:
                pass
    if os.path.exists(OB):
        for line in io.open(OB, encoding="utf-8", errors="replace").read().splitlines()[1:]:
            f = line.split("~")
            if len(f) < 10 or f[5] != "N":
                continue
            try:
                d = dt.datetime.strptime(f[9], "%b %d, %Y").date()
            except Exception:
                continue
            recs.append({"appl_no": f[6], "date": d, "terms": words(f[2]) | words(f[0].split(";")[0]),
                         "what": f"Orange Book NDA {f[6]} {f[2]} ({f[0]}) approved {f[9]}"})
    return recs


def check(rows, recs, today, acks):
    fails = []
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("st") not in ("Upcoming", "Under review"):
            continue
        since = row_source_date(r)
        terms = row_terms(r)
        if not since or not terms:
            continue
        for x in recs:
            if not (since < x["date"] <= today):
                continue
            hit = terms & x["terms"]
            if not hit:
                continue
            if (r["id"], x["appl_no"]) in acks:
                continue
            fails.append(f"{r['id']} [{r['t']}] {r['name']!r} (source {since}): {x['what']} -- matched {sorted(hit)}")
    return fails


def load_acks():
    if not os.path.exists(ACK):
        return set()
    j = json.load(io.open(ACK, encoding="utf-8"))
    return {(a["id"], str(a["appl_no"])) for a in j.get("acks", []) if (a.get("why") or "").strip()}


def self_test():
    t = dt.date(2026, 11, 18)
    rows = [{"id": "x", "t": "X", "type": "PDUFA", "st": "Upcoming", "name": "Zorbatinib - lung cancer",
             "_d": {"source": "X 8-K 2026-08-01"}}]
    recs = [{"appl_no": "999", "date": dt.date(2026, 11, 10), "terms": words("ZORBATINIB"), "what": "planted"}]
    old = [{"appl_no": "998", "date": dt.date(2026, 7, 1), "terms": words("ZORBATINIB"), "what": "before source"}]
    ok = len(check(rows, recs, t, set())) == 1 and not check(rows, old, t, set()) \
        and not check(rows, recs, t, {("x", "999")})
    if not ok:
        print("SELF-TEST FAILED: the planted approval was not caught (or a pre-source one was)")
    return ok


def main():
    if not self_test():
        return 1
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    fails = check(rows, fda_records(), eastern_today(), load_acks())
    if fails:
        print(f"FAIL: {len(fails)} open PDUFA row(s) match an FDA approval recorded after the row's source "
              f"(record the decision, or ack a different product in _fda_record_ack.json):")
        for f in fails[:40]:
            print("   " + f)
        return 1
    print("OK -- no open PDUFA row names a drug the FDA's records show approved since the row's source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
