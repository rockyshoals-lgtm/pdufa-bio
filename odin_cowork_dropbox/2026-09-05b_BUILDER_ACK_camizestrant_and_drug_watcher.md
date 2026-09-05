# Builder ack — strategy audit 09-05b actioned, and the new watcher found three more
*2026-09-05 (Pacific). Facts and build mechanics only, not investment advice.*

## Your P0, and what fell out of fixing it properly

Camizestrant is done: /fda-decision/AZN-2026-09-04 published from the FDA's own press
announcement, /drug/camizestrant now leads with "The FDA approved it on Sep 4, 2026,"
Etcamah is FIRST in alternateName (manually seeded; openFDA will confirm in ~9 days),
and the /decisions listing, API, ticker hub and snippets all propagated through the
established sync.

Then the drug-page watcher you specified went live, and its FIRST SWEEP found that
camizestrant was not one miss but four:

- **Rasonque (daraxonrasib), RVMD, approved Aug 26** — 6.5 months before the user fee
  deadline per FDA's own release, on an application that was never a dated event
  (goal never disclosed). We hold 8.43% citation share on this drug and the page said
  "under review" for ten days. Published, with the +112% T-120 run-up its chart shows.
- **LISRAYA (brepocitinib), approved Aug 27** — 34 days before the Sep 30 goal.
  Published on BOTH tickers (ROIV sponsor-parent, PFE originator/partner), and the
  two Sep 30 Upcoming events resolved to Decided through the sync.
- **Zanvastro (zilganersen), IONS, approved Sep 3** — 19 days before the Sep 22 goal.
  This one WAS an armed event; it sat inside openFDA's ~9-day feed lag, which is
  exactly the window the press-RSS source closes.

## The watcher (watch_drug_approvals.py, blocking in CI)

Keys on the DRUG-PAGE corpus (559 pages), not dated events. Three FDA surfaces:
press-release RSS with item BODIES fetched (camizestrant's headline named no drug;
the body did), the oncology approval-notifications page date-gated to the lookback
window (it is cumulative; the first sweep flagged temozolomide's historical entry
as news until gated), and one paged openFDA recent-AP range query instead of 559
per-drug calls. Supplement-class stoplist carried over from the event watcher, plus
openFDA's "MANUF (CMC)" spelling variant. A hit is a LEAD; verified non-events are
acked with reasons (tirzepatide and tislelizumab efficacy supplements were the
first two).

**Guard 61** (`test_drug_pages_state_approvals.py`): `_drug_approvals_confirmed.json`
is a hand-verified approvals ledger, grown at verify-time, and the guard asserts each
entry's RENDERED page states the approval and carries no pending phrasing. Proven
0 → planted 1 → healed 0 — and then it caught a real one the same hour: daraxonrasib's
manual under-review row survived the decision publish and kept "under review" prose
on the page until the guard refused it.

## Track A started (the sentence supply)

- **/calendar explainer block**: the five quotable paragraphs the Bing answer box is
  currently sourcing from five competitors — what a PDUFA date is, the 10/6-month
  clocks, the 3-month extension, "the FDA does not publish a calendar" with our
  sourcing sentence, and the early/on/late split (32 sourced 2026 decisions: 20
  early, 9 on, 3 late; largest margin 108 days). Numbers come from importing the
  timing page's own collect() — a first draft recounted from the raw dataset and got
  32 where the page said 29, which is precisely the two-surfaces disagreement this
  codebase keeps relearning; one source of rule now.
- **/fda-this-month**: the month's decisions as dated sentences (Pharmacy Times'
  shape, our data, rebuilt daily). Includes archive-only decisions with no dataset
  row, so camizestrant-class approvals appear the day they are published.
- Both wired into CI.

## Bookkeeping

62 guards green. Brand names seeded for all four approvals (RASONQUE, ZANVASTRO,
LISRAYA, ETCAMAH). Slate swept (3 decided events removed from the forward board).
Your §7 item 3 (MNKD/REPL/JAZZ/ZYME calendar links) turns out to be deeper than
links — MNKD and REPL rows are absent from /calendar entirely — so it stays on the
tracked calendar-pass task rather than getting a shallow patch. Tracks B items 3-4
(readout outcomes done previously; /company pages) and Track C hubs remain queued.
