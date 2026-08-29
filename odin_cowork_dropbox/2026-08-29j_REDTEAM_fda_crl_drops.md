# Red team: the two FDA CRL letter drops
**2026-08-29 · builder red team, requested by David before any ingestion · all claims verified against the PDFs themselves**
*Facts and historical statistics only — not investment advice.*

---

## VERDICT: usable, valuable, and NOT fully current — ingest with the rules below

The two folders are the FDA's own CRL transparency releases, and they are genuine:
every sampled letter carries FDA letterhead, an application number (STN), a dated
COMPLETE RESPONSE header and an addressee block. A machine index of all 364 letters is
written to `_crl_letter_index.json` (built by `crl_letter_indexer.py`).

| Set | Files | Distinct applications | Letter dates | What it is |
|---|---:|---:|---|---|
| `unapproved_CRLs (1)` | 148 | ~107 | 2020-08-03 → **2026-08-07** | CRLs for still-pending/withdrawn applications (the 89-letter batch + real-time releases) |
| `approved_CRLs (2)` | 216 | ~200 | 2020–2024 era | CRLs for products **later approved** (the July 2025 "radical transparency" batch, OtherActionLtrs packages) |

Zero application-number overlap between the sets, which is exactly what the FDA's two
release tracks predict. 3 of 364 letters extract almost no text (scanned; OCR needed).

## Currency — David's concern, and he was right to have it

1. **The newest letter is 2026-08-07.** Three weeks behind today.
2. **The FDA HALTED publication on ~2026-07-10 after a citizen petition, then resumed
   with a 14-letter batch** — the drop is consistent with the post-unpause state, but the
   halt means published letters lag issued letters by an unknown amount.
3. **A letter we should have is missing:** Lantheus's LNTH-2501 CRL (announced
   2026-06-26) is nowhere in the drop, while two OTHER sponsors' Ga-68 edotreotide
   letters ARE (Evergreen Theragnostics 06-26, ITM Solucin 08-07). Absence of a letter
   is publication lag, never evidence against the CRL.

## The finding that makes this worth ingesting

**Cross-matching the 2026 letters against our own CRL archive shows the FDA letter date
runs 1–3 days BEFORE the announcement date we record:**

| Ours | We record (announcement) | FDA letter | Delta |
|---|---|---|---|
| ACHV cytisinicline (NDA 218995) | 2026-06-22 (+2 vs goal) | **2026-06-20** | letter ON the goal date |
| UNCY OLC (NDA 218607) | 2026-06-30 (+1 vs goal) | **2026-06-29** | letter ON the goal date |
| AQST Anaphylm (NDA 219870) | 2026-02-02 | **2026-01-30** | −3 |
| CAPR deramiocel (BLA 125842) | 2025-07-11 | **2025-07-09** | −2 |
| RGNX (BLA 125840) | 2026-02-08/09 | **2026-02-07** | −1/−2 |
| REPL RP1 (BLA 125827) | 2025-07-22 | both letters present (2025-07-21, **2026-04-10**) | −1 |

Consequence for the decision-timing study (n=27): the two "late" CRLs (ACHV +2, UNCY +1)
were actually ON-date FDA actions announced late. With letter dates, the "after" bucket
shrinks and the page's claim gets *more* precise — but ONLY if we state which date we use.
**Rule: the site's decision date stays the announcement date (what a trader could act on);
the letter date is published alongside it as "FDA letter dated X", each linked to its PDF.**
Two dates, both true, both sourced, never conflated.

## What else is in here

- **Capricor's deramiocel CRL letter itself** — the primary document for the most-watched
  extended PDUFA on the board.
- **Both Replimune letters** (2025 CRL + a 2026-04-10 letter) — the RP1 story with receipts.
- **Deficiency text** (facility inspections, CMC, labeling-only) — feeds the CRL-reason
  features ODIN v13/v14 built proxies for, now with primary text.
- The approved set = **CRL → later-approval pairs**: the "what happens after a CRL"
  dataset (recovery time, resubmission class) with letters at both ends.

## 🔴 Blockers found — resolve before ingestion

1. **Possible untracked CORT CRL:** NDA 219398 letter dated **2026-01-28**, relacorilant
   (Cushing's/hypertension study text visible). Our archive holds CORT CRL 2025-12-31
   (hypercortisolism, NDA presumably different). A second application's CRL a month later
   is NOT in our decisions archive. Verify against Corcept's filings before adding — and
   if real, it enters the archive, the timing page and the calendar.
2. **Never join on drug name.** Ga-68 edotreotide has THREE sponsors in this drop alone.
   Join on application number + addressee company; drug name is a display field.
3. **Application numbers are not yet in our archive** — the join table
   (`_crl_letter_index.json`: app#, letter date, company, file) must be reviewed
   per-row against our decision pages before any link renders; ~10 rows, one sitting.

## Rules of engagement (ingestion, when approved)

- Letters are attached to EXISTING decision pages as "FDA letter (PDF), dated X" — the
  letter never creates a decision row by itself except via the verified CORT resolution.
- Absence of a letter is stated as "not yet published by the FDA" — the halt makes
  absence meaningless.
- The 3 unreadable PDFs get OCR'd or flagged, never silently skipped.
- Refresh path: the FDA now releases in real time (post-unpause); a periodic re-pull
  belongs in the weekly loop, not a one-off.

*Not investment advice. All statements verified against the PDF contents on 2026-08-29.*
