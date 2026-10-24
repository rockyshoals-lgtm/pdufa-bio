# Builder note: decision-timing census backfill (35 -> 36) and two Gazyva goal dates
**2026-10-24, work 12:30 Pacific onward = 15:30 Eastern = 19:30 UTC.** *RULE 1.*
*Facts only. Not investment advice.* Responds to "update the how many PDUFAs get decided early/on time/late with the ones we haven't added yet"; David chose "tracked rows first".

## 1. Who was missing, and why
The census counts a 2026 decision only when both the PDUFA goal day and the FDA's action day come from a document. 14 decided 2026 applications on our calendar had an FDA action day but no sourced day-precision goal (partner rows of one application counted once). Each sponsor's own releases and SEC filings were searched today:

| Application | FDA day | What the sponsor stated | Result |
|---|---|---|---|
| OTSKY centanafadine (SIMTRIYO) | Jul 24 (NDA 218145 letter) | Otsuka America, Jan 27, 2026: "PDUFA target action date is July 24, 2026" | **added, on the goal date** |
| PTGX/TAK rusfertide | Aug 28 | "August 2026" (month) | out |
| PFE/ROIV brepocitinib (LISRAYA) | Aug 27 | "third quarter of calendar year 2026" | out |
| TAK oveporexton (ORZEYFUL) | Aug 5 | "third quarter of this calendar year" | out |
| GSK Jemperli LARC | Oct 19 | "February 2027" (month) | out |
| AZN Truqap (CAPItello-281) | Jun 12 | no goal date | out |
| MRK enlicitide (Lipfendra) | Jul 15 | no goal date (the "September 21, 2026" PDUFA in Merck's Q4 2025 release is WINREVAIR's HYPERION sBLA, checked in the PDF) | out |
| LLY Inluriyo + Verzenio | Sep 18 | no goal date | out |
| LLY Jaypirca 1L CLL/SLL | Oct 2 | no goal date | out |
| NVS Rhapsido (SD) | Oct 6 | no goal date | out |
| RHHBY Gazyva (INS) | Sep 25 | priority review in May 2026, no goal date | out |
| BAYRY Hyrnuo 1L NSCLC | Sep 9 | priority-review release (May 18) states none | out |
| BAYRY Kerendia T1D-CKD | Sep 16 | priority-review release (May 21) states none | out |
| ABBV Juvmo (tavapadon) | Sep 25 | no goal date | out |
| LNTH (CRL, Jun 29) | none | CRL letters are not public, so no FDA record of the action day | out |

**Result: 36 decisions, 23 early, 12 on the goal date, 1 late** (was 35: 23/11/1). Every "out" row now carries its reason (`_d.census_note`), and /research/fda-decision-timing names all of them in "Left out because a date has no document behind it", including the month- and quarter-only rows that the list used to skip silently; partner rows of one application are named once (PFE/ROIV).

## 2. Found on the way: Gazyva had two goal dates we did not show
- **Primary membranous nephropathy**: Genentech, July 14, 2026: priority review, "expected to make a decision on approval by November 2026". This was on no surface of the site. New row `pdufa_rhhby_2026-11-30_pmn`, month precision, event page /pdufa/RHHBY-gazyva-pmn, on the slate.
- **Systemic lupus erythematosus**: Genentech, April 20, 2026: sBLA accepted, "The FDA is expected to make a decision on an approval by December 2026". The calendar showed this as "Q4 2026 (est.)" and `_calendar_unbacked_q4_rows.json` listed it as "no external source at all". It now has a dataset row (`pdufa_rhhby_2026-12-31_sle`, December 2026, on /pdufa/RHHBY-gazyva) and leaves that list; the ratchet baseline goes 9 -> 8.
`apply_1024_census_and_gazyva.py` (also places the month rows on /calendar, November and December by hand, as month rows always have been; ensure_calendar_rows.py handles day rows only).

Two builder bugs surfaced by the second Gazyva row, both fixed:
- `normalize_calendar_windows.py` gave a window row the label of the FIRST same-ticker row sharing any word, so the SLE row ("Gazyva: Systemic Lupus Erythematosus") took the new pMN row's "Nov 2026". It now picks the row sharing the most words.
- `build_pdufa_event_pages.py` ran a hand-assigned `event_slug` through the "already covered by a sibling page" test when the slug equalled the default one (RHHBY-gazyva), so the sibling RHHBY-gazyva-pmn page "covered" it and no page was written; a hand-assigned slug is now never covered, as its own comment always said. /pdufa/RHHBY-gazyva was rebuilt from the dataset row: "RHHBY PDUFA date: Gazyva, December 2026" (it said "Date not sourced"; its og.png kept).

## 3. Not done (the bigger pass David did not choose)
About 116 more 2026 decisions sit in the archive with no goal date at all, mostly big-pharma supplements whose sponsors never disclose one. Today's sample (13 of 14 large-sponsor applications had no day-precision goal) suggests most would stay out.
