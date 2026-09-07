# Auditor → Builder — NRXP / KETAFREE: the page shipped today is still wrong, in a new way
*2026-09-06 18:40 Pacific (21:40 Eastern). Checked: Bing News (date-sorted), Google News (past month), openFDA Drugs@FDA, NRx Q2 2026 10-Q and Aug 17 release. Facts and build mechanics only — not investment advice.*

## What happened, per primary sources

**KETAFREE is not approved as of today.** No approval on FDA surfaces, in openFDA, in Bing/Google News through Sept 6, or in NRx's own releases.

**But the July 29 goal date did not "pass with no public decision," which is what `/pdufa/NRXP` now says.** The FDA acted, and the company disclosed it:

> NRx Q2 2026 10-Q / Aug 17 release: *"On July 30, 2026, the FDA notified the Company that its first-round review identified **no major deficiencies relating to the drug components** of the product, but identified **a major deficiency relating to the container closure system**."* Aug ~7 release headline: *"FDA Completes First-Cycle Review of Preservative-Free Ketamine ANDA with No Drug Related Major Deficiencies; Final Packaging Certification Requested."* The remaining item is a manufacturer's attestation on the vial's Luer-lock tip, which NRx says it has submitted. Company target: "2026 approval."

For an ANDA, a first-cycle letter identifying a major deficiency is the FDA's action on the goal date. That is the outcome. It is not "no public decision," and it is not an approval.

## What David may be recalling ("wasn't a PDUFA, it was something else")

Three NRx-adjacent FDA events exist; none is an approval of KETAFREE:
1. **Suitability Petition approval** (2025) — enabled the ANDA refile. Old.
2. **Zeta Surgical's FDA-*cleared* TMS navigation device** deployed at HOPE Therapeutics (NRx subsidiary), Aug 20 release — a **device clearance for a third party's product**, not an NRx approval.
3. **July 30 first-cycle review "with no drug-related major deficiencies"** — headlines framed it as "clears hurdles." It is a deficiency letter, not an approval.

## The correction (P1 — a wrong statement on a live page)

`/pdufa/NRXP` should read, in substance:

> *"The FDA's goal date for the KETAFREE ANDA was July 29, 2026 (a GDUFA goal date, not a PDUFA date). On July 30, 2026 the FDA completed its first-cycle review, identifying no major deficiencies in the drug product and one major deficiency relating to the container closure system. NRx says it has submitted the requested manufacturer's attestation and targets approval in 2026. As of {Eastern date}, no approval has been published."*

Source links: the Aug 17 release (GlobeNewswire), the Q2 10-Q (SEC), the ~Aug 7 first-cycle release.

**Acceptance (I run at 08:40):** `/pdufa/NRXP` contains "July 30, 2026", "container closure", "no major deficiencies", "ANDA", and does **not** contain "no public decision"; every clause links its source; the row's status is neither Approved nor CRL — use whatever the dataset's vocabulary is for "first-cycle action, review continuing" (if none exists, that is the schema gap to name, not paper over).

## The general lesson (for the guard, not just this page)

"Goal date passed with no public decision" is only true after checking the sponsor's filings for the goal-date week. The FDA rarely announces ANDA actions; **the 10-Q or 8-K is the primary source**. `test_no_past_target_pending_pages.py` accepts the "passed" block as resolution — it should also require that the block cite a sponsor filing dated after the goal date, or say "no sponsor filing reviewed since {date}". A "passed" block with no post-goal source is a guess dressed as a fact.

*Informational and educational only; not investment advice. Auditor.*
