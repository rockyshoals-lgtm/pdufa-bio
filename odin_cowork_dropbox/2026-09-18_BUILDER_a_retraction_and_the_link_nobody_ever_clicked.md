# Builder, 09-18: a retraction, today's approval, and the nav link nobody ever clicked
**2026-09-18, written 19:10 Pacific = 22:10 Eastern = 2026-09-19 02:10 UTC.** *Per RULE 1 every time here carries its zone. Facts and build mechanics only; not investment advice.*

No audit today, so this is a currency pass plus the re-application of the 09-15 batch that a fast-forward reverted. It turned up one thing I got wrong and three the suite had never looked at. **91 guards pass, 0 fail. Live and verified at commit `b6baf259d`.**

---

## 1. The retraction, first, because I raised the alarm

Working the decided rows I noticed that **every one of the nine rows in the published "landed on the goal date" bucket had a goal date identical to its decision date**, and eight carried no `source_url`. I wrote it up as a probable P0: the bucket looked like an artefact of filling the goal date from the action date, which is the defect the 09-15 audit's item 8 and my own task #32 had been circling.

**I was wrong for seven of the nine, and I want that on the record before anything else.** EDGAR has each sponsor stating exactly that day in its own filing, and the FDA acted on it:

| | goal date the sponsor published | where |
|---|---|---|
| ARQT | June 29, 2026 | Arcutis 10-Q 2026-05-06: *"a Prescription Drug User Fee Act (PDUFA) target action date assigned for June 29, 2026"* |
| VERA | July 7, 2026 | Vera 8-K 2026-02-26: *"granted priority review to BLA for atacicept with Prescription Drug User Fee Act (PDUFA) date of July 7, 2026"* |
| MRNA | August 5, 2026 | Moderna 8-K 2026-07-31: *"The U.S. FDA has assigned a PDUFA date for mRNA-1010 of August 5, 2026"* |
| LNTH | August 13, 2026 | Lantheus 8-K 2025-11-06: *"The FDA has set a PDUFA target action date of August 13, 2026"* |
| JAZZ / ZYME | August 25, 2026 | Jazz 8-K 2026-05-07: *"PDUFA target action date of August 25, 2026"* (Jazz holds the BLA; Zymeworks licensed zanidatamab to Jazz) |
| GILD | August 27, 2026 | Gilead 8-K 2026-05-07: *"a Prescription Drug User Fee Act (PDUFA) target action date of August 27, 2026"* |

Each quote is now on the row as `goal_source_quote` with its URL, so the next person does not have to take my word for it. A run of seven on-the-day decisions is not a smell; it is what the PDUFA system does when a review completes cleanly.

**Two were real, and they are a different shape from what I guessed.** Not "the goal was overwritten" but "there was never a goal date to hold":

- **MRK 2026-07-16, Lipfendra (enlicitide).** Merck has never published a PDUFA date for it. The Q2 10-Q says only *"In July 2026, the FDA approved Lipfendra tablets"*; the Q1 10-Q covers the EU review; the 8-K of 2026-02-03 records a **priority review voucher under the CNPV pilot**, a pathway that need not carry a conventional goal date. Our July 16 was the action date wearing a goal date's field.
- **OTSKY 2026-07-24, centanafadine.** Otsuka files nothing EDGAR-searchable for it and openFDA holds no record under that generic name. Nothing to link.

Both keep their approval, which is sourced. Both are marked `goal_unsourced`, and **`build_early_decisions.py` now gates on goal provenance rather than precision alone** — the third time this year that "the date looks like a day" has turned out to be the wrong test.

**The published statistic moves from 30 / 18 early / 9 on the day / 3 late to 28 / 18 / 7 / 3, median 1.5 → 2.5 days before.** Restated on all three surfaces and verified live on each.

---

## 2. Today's approval

**The FDA approved imlunestrant (Inluriyo) with abemaciclib (Verzenio) today**, for ER-positive, HER2-negative, ESR1-mutated advanced or metastatic breast cancer, on EMBER-3. Read from the FDA's own notification before anything was written: *"On September 18, 2026, the Food and Drug Administration approved imlunestrant (Inluriyo) in combination with abemaciclib (Verzenio)..."*

We never carried a goal date for the supplement and Lilly never published one, so the row records the action date, is marked `goal_unsourced`, and is **excluded from the timing statistic** under the rule written an hour earlier. It reached the decision page, `/decisions`, `/drug/inluriyo`, `/fda-this-month` and the calendar. The reconciler had flagged it as "unverifiable by name", which is how I found it — that advisory earned itself today.

openFDA still shows only the original 2025-09-25 approval for NDA 218881; efficacy supplements lag there by days, so the FDA notification is the source.

---

## 3. Three things the suite had never looked at

**a. The nav's "Pro" link has 404ed on every page since the beginning.** `("/pricing", "Pro")` is in `rebuild_nav.py`, it renders on **954 pages**, and `pdufa_site_src/pricing/index.html` has never existed in this repository's history. /developers carries the tier table under the heading "Tiers" and states **$10/mo or $100/yr** in its own copy, plus two more body links to `/pricing/credits` and `/pricing?ref=developers` that also 404. Every one now points at `/developers#tiers`. **I invented no price and removed none** — whether a real /pricing page should exist, and what it says, is yours. The nav freeze file records the change and why, since that guard exists to make nav changes deliberate and it did its job.

**b. 108 pages linked /pdufa/* pages that were never built** (`/pdufa/LNTH-lnth-2501` on 27 pages, `/pdufa/AZN-truqap` on 25, and 19 more targets), and seven dataset rows did the same with bare `/pdufa/{TICKER}`. All moved to the ticker hub, which exists and carries those events.

**c. /decisions/approvals linked five decision pages that do not exist, and showed the wrong date for each** — the goal date, not the action date:

    AZN  shown 2026-06-30  Truqap    real page AZN-2026-06-12
    GSK  shown 2026-06-18  Utebzi    real page GSK-2026-06-17
    SPRO shown 2026-06-18  Utebzi    real page SPRO-2026-06-17
    VRDN shown 2026-06-29  Lumvoa    real page VRDN-2026-06-26
    VRDN shown 2026-06-30  Lumvoa    a SECOND row for the same approval

Links and visible dates corrected, duplicate row removed. Each target was opened and its title read first.

**New guard: `tests/test_no_dead_internal_links.py`** — every internal href on all 1,404 indexable pages must resolve to a built page. It is at zero, and the repair runs in CI before the sitemap so nothing dead is ever submitted.

---

## 4. One I introduced, and caught

Adding the LLY row made `/drug/inluriyo` say **"3 FDA decisions on record"** over two links. The page is fed by the dataset *and* by the decisions archive, and when a decided row's goal date equals its action date both sources yield the same event. It was not new: **six pages were already double-counting**, including `/drug/zanidatamab`, which says 4 over 2 and holds the only 100%-citation-share grounding query on the property. Deduped on the decision href, with the count moved after the check. **New guard: `tests/test_drug_page_decision_count.py`**, proved 0 → planted 1 → 0 on both the duplicate-row and inflated-count branches.

---

## 5. Re-applied, and the state of sourcing

The 09-15 batch that the fast-forward reverted is back: the EDGAR source pass (22 rows), Roche ×4 + GSK bepirovirsen + REGN + the NUVL→GSK acquisition across every surface. **Upcoming PDUFA rows carrying `source_url`: 15 of 49 → 43 of 48 live.** The five that remain are the known unbacked set (ABBV tavapadon, AZN Ultomiris, BAYRY Kerendia, NVO CagriSema, NVO Mim8) — the ones no filing supports even at month precision, still ratcheted, still awaiting your ruling on downgrade-or-withdraw.

---

## 6. Open, and what I could not settle

**TLX101-Px (Pixclara) has been "awaiting" for seven days** — goal date 2026-09-11, no decision. I checked openFDA (no record under the brand or the generic), the FDA press feeds and the oncology approval notifications (nothing), and our own watchers (0 unreviewed). Telix's newsroom and ASX announcements return **403 to a non-browser client**, so I could not read them and I am not going to infer anything from silence. The site says "awaiting a decision", which is the honest state. If you can open their newsroom in a browser, that is the one gap.

**RARE UX111 decides tomorrow, 2026-09-19** — sourced to Ultragenyx's 8-K, the next dated event on the board.

CI is green on all eight runs since 09-16. Carried: the 9 unbacked window pages, 22 readout leads, the TA back-fill, the openFDA pass over the 36 decided rows, and the 13 Estimated readouts whose registry re-sync moved them into the past.
