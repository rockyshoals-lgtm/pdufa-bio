# Builder response to Red Team Pass 8 · 2026-06-26

Most fixes were in the **page generator** (`build_seo_pages.py`), so I fixed them at the source and regenerated — durable, not a one-off patch. All verified live on the apex via Chrome.

## ✅ SHIPPED THIS PASS (live + verified)
**#2 Condition mis-categorization (P0 — credibility).** `classify_ta` now (a) checks an **ophthalmology** bucket *first* (ophthalmic/macular/retina/uveitis/glaucoma/intravitreal…), and (b) only buckets "diabet" as metabolic when there's no eye/kidney/nerve context, and (c) reads the **drug name** too (so "SBI-100 Ophthalmic Emulsion" is caught by "ophthalmic"). Result: `/condition/obesity-metabolic` now has **zero** eye-drug rows (verified), and there's a new correct **`/condition/ophthalmology`** page (9 condition pages now).

**#1 On-site internal links (P0).** Hub rows now link to the on-site **`/pdufa/[TICKER]`** page when one exists (existence-checked against the deploy folder), instead of straight to SEC/CT.gov, and the internal links drop `rel=nofollow`. PDUFA rows funnel internally (verified `/pdufa/LLY`, `/pdufa/MNKD`, `/pdufa/NVO`). *Caveat:* readout rows whose ticker has **no** detail page still fall back to CT.gov — closing that fully needs per-readout `/readout/[id]` pages (backlog, below).

**#3 Dynamic condition titles.** Title now matches content: "FDA Decisions & Readouts" only when both exist, else "FDA Decisions" or "Clinical-Trial Readouts" (obesity now correctly reads "…Clinical-Trial Readouts").

**#4 Title double-escape.** `&mdash;` in the month-page `<title>`/desc was being escaped by `esc()` into `&amp;mdash;`. Switched to a real "—" — verified `<title>September 2026 FDA PDUFA decisions — FDA Calendar`.

**#6 Condition JSON-LD.** Condition pages now carry **`ItemList` + `FAQPage`** schema (verified).

**#7 "· nan" bug.** Removed the leaked NaN status (`</a> · nan</b>`) across **25** per-event pages (`/pdufa/*`, `/fda-decision/*`) — verified gone on `/pdufa/VNDA`.

**#8 "disease disease".** Fixed the condition nouns + template (was "obesity and metabolic **disease** … in {noun} **disease**"); zero occurrences now.

**Bonus:** regenerated all month/condition/coverage/wedge pages, so they carry the unified Coverage+Pricing nav and the freshest CSV.

## 🟠 BUILDER BACKLOG (bigger than this pass)
- **#1 readout rows fully on-site** — needs per-readout `/readout/[id]` detail pages (none exist today). PDUFA rows are on-site now; readouts are the remaining leak.
- **#3 obesity missing PDUFAs (CagriSema, tirzepatide)** — those aren't in the metabolic bucket in the current `catalysts_public.csv` (a crawl/indication-label gap, not a generator bug). Title no longer over-claims; adding the events is a data fix.
- **#5 month-page data ≠ main `/calendar`** — the month pages regenerate from the newer `catalysts_public.csv`; `/calendar` (`calendar.html`) is built by a separate older pipeline. Reconciling to one source is a `/calendar`-generator change (this is also where the **VRDN / GSK-tebipenem calendar dupes** live — the homepage tape is already deduped).
- **Workstream C — per-event depth** (the long-tail unlock): story block (UNCY's June-2025 CRL→resubmission thesis, cash runway, plain-English indication), fresh-dated charts, related-event links, **email capture**, `Event`/OG schema. Still the biggest growth item; a dedicated build.
- **Plain-English indication layer**; **group the 11-item nav into ~4 dropdowns** (P2).

## 🔴 OWNER
- **GSC Removals** on the worst lingering old-ODIN URLs + keep requesting indexing on the new pages. (Our pages remain zero-ODIN/zero-rating-schema.)
- 410 vs 404 for dead ODIN slugs is moot now — they 301 to the wedge page (better than 410 for equity).

**Bottom line:** the new hub pages now do their job — eye-drops are out of "Obesity," PDUFA rows feed your own `/pdufa/` pages, titles/schema are clean, and the "· nan" is gone. The remaining gaps are **data-pipeline** (one source of truth for `/calendar`, the missing obesity PDUFAs, per-readout pages) and the **per-event depth feature (C)** — the two things that need a dedicated build rather than a fix-pass.
