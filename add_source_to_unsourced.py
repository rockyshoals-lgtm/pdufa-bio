# -*- coding: utf-8 -*-
"""add_source_to_unsourced.py -- the older asserted-outcome pages get their evidence shown.

Second backlog from the 2026-08-12 verification sweep: 116 decision pages assert an outcome in
their Key facts (they predate both the price-only tier and the provenance discipline) but link
no document at all -- 'asserted, no source shown' in the /decisions provenance bars. Where
verify_decisions.py found the primary source, this inserts it as a linked row in the Key facts
card. Where the evidence DISAGREES with the asserted outcome, the page is left alone and the
case is printed for human review -- an asserted page is someone's past claim, and overturning a
claim needs a human reading the document, not a regex.

    python add_source_to_unsourced.py [--dry-run]
"""
import argparse, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
RES_P = os.path.join(HERE, "_decision_verification.json")
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    res = json.load(open(RES_P, encoding="utf-8"))["results"]

    added = review = 0
    for slug, r in sorted(res.items()):
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        if "price-only" in doc or "outcome unverified" in doc:
            continue                      # price tier is handled by the upgrade script
        if re.search(r'href="https?://(?!www\.pdufa\.bio)', doc):
            continue                      # already links an external source
        ev = r.get("evidence")
        if r["status"] not in ("verified_approved", "verified_crl") or not ev:
            if r["status"] == "conflicting_evidence_needs_human_review":
                review += 1
                print(f"  ?? human review: {slug} (asserted vs evidence conflict)")
            continue
        # evidence must AGREE with what the page asserts
        asserted = re.search(r"<span>Outcome</span><b[^>]*>([^<]+)</b>", doc)
        oc = (asserted.group(1).strip().lower() if asserted else "")
        agrees = (("approv" in oc and r["status"] == "verified_approved")
                  or (("crl" in oc or "complete response" in oc)
                      and r["status"] == "verified_crl"))
        if not agrees:
            review += 1
            print(f"  ?? human review: {slug} asserts '{oc[:30]}', evidence says "
                  f"{r['status']}")
            continue
        row = (f'<div class="kv"><span>Primary source</span><b>'
               f'<a href="{html.escape(ev["source_url"], quote=True)}" '
               f'rel="nofollow noopener">{html.escape(ev["source_label"][:80])}</a>'
               f'</b></div>')
        doc2 = re.sub(r'(<span>Outcome</span><b[^>]*>[^<]+</b></div>)', r"\1" + row,
                      doc, count=1)
        if doc2 != doc:
            if not a.dry_run:
                open(p, "w", encoding="utf-8").write(doc2)
            added += 1

    print(f"\nsource rows added: {added}; flagged for human review: {review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
