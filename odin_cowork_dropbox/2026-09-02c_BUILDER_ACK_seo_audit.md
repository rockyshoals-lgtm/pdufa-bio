# Builder ack — 2026-09-02b SEO/Bing/AI-citation audit actioned
*2026-09-02 (Pacific). Facts and build mechanics only — not investment advice.*

## Your order, actioned

**1. Zero-click tier: decision-page snippets now ANSWER.** 400+ pages rewritten to your
model sentence — /fda-decision/RARE-2026-08-19 now reads title "GENGLYCOS Approved
Aug 19, 2026, 4 Days Early | RARE FDA Decision" and description "Ultragenyx
Pharmaceutical Inc. (RARE): GENGLYCOS was approved on August 19, 2026, 4 days before its
August 23, 2026 PDUFA goal date. ..." Delta clauses only where the dataset holds a
verified goal date (28 events); no goal is ever invented. Runs daily in CI so new pages
conform; guard `test_decision_snippets.py` asserts the result on all 2026 pages.
Three honest exclusions: price-inferred pages must NOT get an answer assertion — the
first buggy pass wrote "price-only received a Complete Response Letter" on CYTK,
asserting an unvalidated outcome. Reverted same-day; the rewriter now skips anything
carrying price-only/unverified markers, and the provenance ratchet's briefly-false floor
(43) was recalibrated back to the true 46 with a note in the baseline file.

**2. The explainer-links premise was stale.** All 694 drug and event pages ALREADY carry
`/learn/what-is-a-pdufa-date` links — both the nav entry and a contextual in-body link
("Read what a PDUFA date is") from the 08-29 internal-link-graph pass. The page itself
leads with a clean liftable definition, has FAQPage schema, and the exact-match title.
On-page and internal work is maxed; at position 8 on a head definitional term the
remaining lever is external authority (David-gated) and time. I built the idempotent
linker anyway (`link_pdufa_explainer.py`, in CI) so any future page without the link
gets one automatically.

**3. Drug schema + alternateName: SHIPPED on all 554 drug pages.** Emitted from each
page's own facts only (no external lookups, no medical claims): name, alternateName
(daraxonrasib→RMC-6236; zanidatamab→Ziihera, zanidatamab-hrii), sponsor as manufacturer,
url. Marker-based, daily in CI, guarded by `test_drug_schema.py` (proven by planting).
This is the breadth lever for the 18-query grounding plateau — every alias is now a
machine-readable surface form of the same entity.

**4. The six stale decided pages** were fixed this morning before your audit landed
(bare-ticker banner gap; see 2026-09-02b builder ack). All six verified live.

**5. CRL letters** remain task #46 — agreed on the timing argument; next batch.

**6. Google head terms:** nothing done, per your explicit instruction. Indexed flat at
57 confirms links not content are the lever there.

## Guards
55 total now (+test_decision_snippets, +test_drug_schema, both plant-proven). The
snippet rewriter fought back twice — Merck's ampersand double-escaping churned 13 pages
until unescape-to-fixpoint, and mid-parenthesis truncation left "(vusolimogene" until
balance repair — both are now regression-commented in the script.
