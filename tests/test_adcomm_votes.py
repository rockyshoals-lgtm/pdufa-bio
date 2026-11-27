"""Guard for /adcomm/votes (build_adcomm_votes.py): every vote count and FDA action carries a primary source,
counts are whole numbers, at most one overall question per meeting, curated notes carry no research jargon,
and the built page shows every card's vote source. PLANT=1 makes it fail on purpose."""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "adcomm_votes_sourced.json")
PAGE = os.path.join(HERE, "pdufa_site_src", "adcomm", "votes", "index.html")
JUNK = re.compile(r"snippet|per search|not read|rate.?limit|\bTODO\b|\bpass \d\b|agent|could not be re-read", re.I)
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    bad = []
    d = json.load(io.open(DATA, encoding="utf-8"))
    rows = [m for m in d["meetings"] if m.get("kind") == "product_vote" and m.get("questions")]
    if len(rows) < 10:
        bad.append(f"only {len(rows)} product votes")
    # A Federal Register amendment notice repeats its meeting; one meeting, one card.
    seen = {}
    for m in rows:
        app = m.get("application") or ""
        key = (m.get("meeting_date"), m.get("product")) if app.startswith("Emergency") else (m.get("meeting_date"), app)
        if key in seen:
            bad.append(f"{key}: duplicate meeting record")
        seen[key] = 1
        ns = [q.get("n") for q in m.get("questions") or []]
        if len(ns) != len(set(ns)):
            bad.append(f'{m.get("meeting_date")} {m.get("product")}: repeated question number')
    for m in rows:
        k = f'{m.get("meeting_date")} {m.get("product")}'
        if not ISO.match(m.get("meeting_date") or ""):
            bad.append(f"{k}: meeting date")
        if not str(m.get("vote_source_url", "")).startswith("http") or not m.get("vote_source_quote"):
            bad.append(f"{k}: vote source or quote missing")
        if m.get("vote_source_type") not in ("fda", "sponsor"):
            bad.append(f"{k}: vote_source_type")
        ov = [q for q in m["questions"] if q.get("is_overall")]
        if len(ov) > 1:
            bad.append(f"{k}: {len(ov)} overall questions")
        for q in m["questions"]:
            for f in ("yes", "no", "abstain"):
                # 2026-11-27: abstain may be None when the source gives yes and no only (most sponsor
                # releases, and the Janssen booster minutes). None renders "n/s"; a 0 we did not read is a
                # made-up fact, so the importer must never fill it in.
                if f == "abstain" and q.get(f) is None:
                    continue
                if not isinstance(q.get(f), int) or q[f] < 0 or q[f] > 40:
                    bad.append(f"{k} Q{q.get('n')}: {f}={q.get(f)!r}")
            if (m.get("vote_source_type") == "sponsor" and q.get("abstain") == 0
                    and not re.search(r"abstain|abstention|unanim", m.get("vote_source_quote") or "", re.I)):
                # 2026-11-27: four live cards showed 0 abstentions that the sponsor's release never stated.
                # A sponsor's "voted 12 to 1" says nothing about abstentions; record None ("n/s").
                bad.append(f"{k} Q{q.get('n')}: abstain=0 but the sponsor quote never mentions abstentions")
            if not (q.get("text") or "").strip():
                bad.append(f"{k} Q{q.get('n')}: no text")
        a = m.get("fda_action")
        if a not in ("approved", "crl", "withdrawn", "pending", "other"):
            bad.append(f"{k}: fda_action {a!r}")
        if a in ("approved", "crl"):
            if m.get("fda_action_date") is None and m.get("fda_action_date_note"):
                pass  # the source confirms the action but not its date (tanezumab's CRL); the note says so
            elif not ISO.match(m.get("fda_action_date") or "") or m["fda_action_date"] < m["meeting_date"]:
                bad.append(f"{k}: action date {m.get('fda_action_date')!r}")
            if not str(m.get("action_source_url", "")).startswith("http") or not m.get("action_quote"):
                bad.append(f"{k}: action source or quote missing")
        if a == "other" and not m.get("action_label"):
            bad.append(f"{k}: 'other' action needs action_label")
        if JUNK.search(m.get("public_note") or ""):
            bad.append(f"{k}: research words in public_note")
    if os.path.exists(PAGE):
        page = io.open(PAGE, encoding="utf-8").read()
        for m in rows:
            if m.get("vote_source_url") and m["vote_source_url"].replace("&", "&amp;") not in page:
                bad.append(f'page lacks vote source {m["vote_source_url"]}')
        if "not investment advice" not in page.lower():
            bad.append("page lacks the disclaimer")
    if os.environ.get("PLANT") == "1":
        bad.append("planted failure")
    for b in bad:
        print("FAIL", b)
    print(f"test_adcomm_votes: {len(rows)} product votes, {len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
