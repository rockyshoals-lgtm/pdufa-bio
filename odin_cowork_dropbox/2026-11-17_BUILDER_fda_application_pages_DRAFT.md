# Builder note: per-application pages (/fda-application/nda-NNNNNN), DRAFT for David's review
**2026-11-17, written ~2:30 PM Pacific.** *RULE 1: commit times UTC, page dates Eastern.*
*Facts only. Not investment advice.* Status: on branch `claude/project-thread-rflrnu`, pull request open, NOT merged.

## What it is
One page per FDA application (NDA) that joins every name a drug is searched by: brand, ingredient,
development code names, FDA applicant of record, today's owner and ticker, and earlier owners or
partners. First set: 16 NDAs approved or tracked on pdufa.bio. Index at `/fda-application`.

## Where each fact comes from
| Fact | Source | Typed by hand? |
|---|---|---|
| Application number, brand, ingredient, applicant of record, products, approval dates | FDA Orange Book data files (`_orange_book/products.txt`, refreshed by `fetch_orange_book.py`) | Never |
| Code names | Company release or SEC filing, verbatim quote naming code AND drug | `_fda_applications.json` |
| Owner today + ticker | Company release or filing, verbatim quote containing the ticker | `_fda_applications.json` |
| Earlier owner / licensor / partner | Primary document, verbatim quote; fixed role phrase, no free text | `_fda_applications.json` |

## Files
- `fda_applications_lib.py`: the rules (domains, quotes, roles), shared by builder and guard.
- `build_fda_application_pages.py`: builds the pages; drops any mapping that fails a rule and prints why.
- `link_application_pages.py`: one marked line on each matching `/drug` page linking its application page.
- `tests/test_fda_application_pages.py`: guard. `PLANT_UNSOURCED_MAPPING=1` must fail (it does).
- Workflow: one step right after "Drug schema + alternateName" (Orange Book is fetched earlier in the run).

## Fail-closed rules
- Orange Book applicant changes from `applicant_verified`: owner, ticker and history are withheld, the page says so, CI keeps running.
- Application leaves the Orange Book: page withheld.
- Source that is not FDA, EDGAR, a newswire or the company's own domain; quote without the value; undated document; any TODO: mapping dropped and the guard fails.

## Things a reviewer should know
- JIDEYTRO (NDA 220185): FDA applicant is still NUVALENT INC, owner is GSK (acquisition completed 2026-07-15, GSK 6-K).
- MIMRYLO (NDA 220605): FDA applicant is TAKEDA PHARMACEUTICALS AMERICA INC; Protagonist (PTGX) licensed it to Takeda.
- LISRAYA (NDA 220106): applicant PRIOVANT THERAPEUTICS INC (Roivant subsidiary; Roivant 71%, Pfizer 24% as of June 30, 2026, per Roivant's 8-K exhibit dated 2026-08-28).
- IGALMI (NDA 215390): sold by BioXcel to Teva on 2026-10-26 (BioXcel 8-K, 2026-10-30); BioXcel's ticker is shown as "ticker at the time: BTAI", the symbol on that 8-K.
- Not in this set: BLAs (not in the Orange Book; each would need an FDA letter as anchor), and owners whose US ticker is an OTC ADR no company document states (Otsuka SIMTRIYO, Bayer HYRNUO).
- Dropped code names: CVL-751 (only in a protocol on ClinicalTrials.gov), AKCEA-APOCIII-LRx (undated page), REVTORPYK (no code name in any primary source found).
