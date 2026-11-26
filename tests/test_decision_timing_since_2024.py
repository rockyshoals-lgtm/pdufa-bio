# -*- coding: utf-8 -*-
"""/research/fda-decision-timing/since-2024 recounted from its sources with independent code.

The 2024-2025 rows come from decision_timing_2024_2025.json; the 2026 rows must be exactly the rows the 2026 page
counts (build_early_decisions.collect). The page's headline, year table and late-CRL sentence are recomputed here.
"""
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
PAGE = os.path.join(HERE, "pdufa_site_src", "research", "fda-decision-timing", "since-2024", "index.html")
DATA = os.path.join(HERE, "decision_timing_2024_2025.json")


def _text():
    d = io.open(PAGE, encoding="utf-8").read()
    d = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", d)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", d)))


def _rows():
    from build_early_decisions import collect
    doc = json.load(io.open(DATA, encoding="utf-8"))
    out = []
    for a in doc["actions"]:
        if a.get("excluded"):
            continue
        g, ad = dt.date.fromisoformat(a["goal_in_effect"]), dt.date.fromisoformat(a["action_date"])
        out.append(((ad - g).days, a["outcome"], a["origin"], ad.year, a.get("goal_source_type") or "sponsor"))
    for r in collect(2026):
        out.append((r["delta"], r["outcome"], "calendar_2026", 2026, "sponsor"))
    return doc, out


def test_every_counted_row_has_two_dated_sources():
    doc = json.load(io.open(DATA, encoding="utf-8"))
    for a in doc["actions"]:
        if a.get("excluded"):
            continue
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", a["goal_in_effect"]), a["cid"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", a["action_date"]), a["cid"]
        assert a["action_date"][:4] in ("2024", "2025"), a["cid"]
        gu = a.get("goal_extended_url") if a.get("extended") else a.get("goal_original_url")
        assert (gu or "").startswith("http"), f"{a['cid']}: no goal source"
        assert (a.get("action_url") or "").startswith("http"), f"{a['cid']}: no action source"
        assert a.get("action_basis") in ("fda_record", "sponsor_states_day"), \
            f"{a['cid']}: an announcement day is not an action day"
        assert a["outcome"] in ("Approved", "CRL", "Split"), a["cid"]


def test_one_fda_action_one_row():
    doc = json.load(io.open(DATA, encoding="utf-8"))
    seen = set()
    for a in doc["actions"]:
        m = re.findall(r"\d{6}", str(a.get("application") or ""))
        key = (m[0] if m else a["cid"], a["action_date"])
        assert key not in seen, f"duplicate FDA action {key}"
        seen.add(key)


def test_candidates_reconcile():
    doc = json.load(io.open(DATA, encoding="utf-8"))
    cand = doc["candidates"]["tracked"] + doc["candidates"]["crl_letter"]
    members = sum(len(a["members"]) for a in doc["actions"])
    assert members + len(doc["excluded_rows"]) == cand


def test_headline_and_years_match_recount():
    doc, rows = _rows()
    t = _text()
    n = len(rows)
    e = sum(1 for d, *_ in rows if d < 0)
    o = sum(1 for d, *_ in rows if d == 0)
    l_ = sum(1 for d, *_ in rows if d > 0)
    assert re.search(rf"Of {n} FDA decisions dated January 1, 2024 through .*?, {e} came before the PDUFA goal date, "
                     rf"{o} on it and {l_} after it", t)
    for y in (2024, 2025):
        ys = [r for r in rows if r[3] == y]
        ye = sum(1 for d, *_ in ys if d < 0)
        yo = sum(1 for d, *_ in ys if d == 0)
        yl = sum(1 for d, *_ in ys if d > 0)
        assert re.search(rf"\b{y} {len(ys)} {ye} \(\d+%\) {yo} \(\d+%\) {yl} \(\d+%\)", t), y


def test_late_crl_sentence_uses_outcome_blind_rows_only():
    _, rows = _rows()
    t = _text()
    # a goal read only from an FDA review is available only for approvals, so those rows stay out of the CRL table
    blind = [r for r in rows if r[2] in ("tracked", "calendar_2026") and r[4] not in ("fda_review", "fda_letter")]
    late = [r for r in blind if r[0] > 0]
    late_crl = sum(1 for r in late if r[1] == "CRL")
    assert f"({len(blind)} decisions), {late_crl} of the {len(late)} late decisions ended in a complete response" in t


def test_no_advice_or_causal_language():
    d = io.open(PAGE, encoding="utf-8").read()
    d = d[d.index("<h1"):d.index("<footer")]             # the study text, not the site's legal footer
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>", " ", d)))).lower()
    for bad in ("will be approved", "likely to", "probability of approval", "we expect", "buy ", "sell "):
        assert bad not in t, bad
    assert "does not claim that timing causes an outcome" in t


def test_goal_source_published_before_action():
    """A goal date is only a goal date if a document stated it before the FDA acted."""
    doc = json.load(io.open(DATA, encoding="utf-8"))
    for a in doc["actions"]:
        if a.get("excluded") or a.get("goal_source_type") in ("fda_review", "fda_letter"):
            continue                                   # the FDA's own record of the goal is not a forecast
        for k in ("goal_original_doc_date", "goal_extended_doc_date"):
            v = a.get(k) or ""
            if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                assert v <= a["action_date"], f"{a['cid']}: {k} {v} is after the action {a['action_date']}"


def test_no_candidate_counted_twice():
    doc = json.load(io.open(DATA, encoding="utf-8"))
    members = [m for a in doc["actions"] for m in a["members"]]
    assert len(members) == len(set(members)), "a candidate sits in two actions"
    left_out = {r["cid"] for r in doc["excluded_rows"]}
    both = left_out & set(members)
    assert not both, f"in an action and in excluded_rows: {sorted(both)}"


def test_linked_csv_exists_and_is_not_gitignored():
    d = io.open(PAGE, encoding="utf-8").read()
    links = set(re.findall(r'href="(/research/fda-decision-timing/since-2024/[^"]+\.csv)"', d))
    assert links, "the page links no CSV"
    for l_ in links:
        f = os.path.join(HERE, "pdufa_site_src", l_.lstrip("/"))
        assert os.path.exists(f), f"linked CSV missing: {l_}"
        gi = io.open(os.path.join(HERE, ".gitignore"), encoding="utf-8").read()
        assert "!pdufa_site_src/research/fda-decision-timing/since-2024/*.csv" in gi, \
            "*.csv in .gitignore would keep the download out of git (404 live)"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fails = []
    for t in tests:
        try:
            t()
        except AssertionError as e:
            fails.append(f"{t.__name__}: {str(e)[:300]}")
    if fails:
        print(f"FAIL test_decision_timing_since_2024: {len(fails)} problem(s); fix: "
              f"python build_decision_timing_since_2024.py")
        for f in fails:
            print("  " + f)
        return 1
    print(f"PASS test_decision_timing_since_2024: {len(tests)} checks, page recounted from its sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def test_fda_goal_sources_are_fda_documents():
    """Pass 4: a goal taken from the FDA's review or letter must link the FDA's own document."""
    doc = json.load(io.open(DATA, encoding="utf-8"))
    n = 0
    for a in doc["actions"]:
        if a.get("excluded") or a.get("goal_source_type") not in ("fda_review", "fda_letter"):
            continue
        n += 1
        gu = (a.get("goal_extended_url") if a.get("extended") else a.get("goal_original_url")) or ""
        assert re.match(r"^https://(www\.|download\.open\.)?(accessdata\.)?fda\.gov/", gu), f"{a['cid']}: {gu}"
        assert a.get("red_team"), f"{a['cid']}: an FDA-review goal must be re-read at source before it counts"
    assert n >= 30
