# pdufa.bio — Crawler audit: how to match BPC's coverage · 2026-06-27

Audited `catalyst_crawler.py` (1,327 lines) + the last run in `catalysts_out/` against your own `bpc_internal.csv`. **Good news: it's a fill-in task, not a rewrite.** The crawler is genuinely well-built (3-layer universe, SEC+CT.gov+FMP+FDA sources, provenance per row, a built-in BPC recall QA-diff). The coverage gap is **narrow, well-understood, and your own output already contains the fix.**

## TL;DR
- You **already beat BPC on readouts** (your crawl: **1,000** PhaseReadouts vs BPC's ~444 data-readout rows). Don't spend effort there.
- You **lose only on PDUFAs / "Regulatory Decisions"** — recall **46.3%** (31 of ~67). And the misses are almost entirely **mega-cap / foreign pharma**.
- Root cause: the auto-miner needs a clean SEC 8-K or FMP press release that contains a trigger phrase ("PDUFA goal date" / "target action date") **next to a parseable date**. Small/mid-caps file exactly that (you catch 50 via SEC+FMP). **Mega-caps and foreign ADRs (AZN, NVO, NVS, RHHBY, BAYRY, TAK, GSK, LLY, MRK, PFE, GILD, BMY, BIIB, REGN, VRTX, IONS…) bury the date in a 10-Q/earnings pipeline table or a foreign 6-K and never trip the regex.**
- The file built to backfill exactly these — `bigpharma_pdufa_seed.csv` — **has only 4 rows** (RHHBY, BAYRY, ALPMY, LLY). It's wired in and works; it's just empty.
- **And the crawler already tells you exactly what it's missing:** `catalysts_out/coverage_gaps.csv` has **40 rows** with ticker + date + drug + indication for the missed regulatory decisions — it just never feeds them back. Close that loop and you're at BPC parity.

## The data (from your own last run, Jun 24)
| Metric | Value |
|---|---|
| Total catalysts | 1,158 |
| PhaseReadouts | 1,000 (you beat BPC here) |
| **PDUFAs found** | **59** (54 unique tickers) |
| PDUFA sources | sec_edgar **39** · fmp_press **11** · curated seed **7** · colist 2 |
| **PDUFA recall vs BPC** | **0.463** |
| BPC "Regulatory Decision" rows | 73 |
| `bigpharma_pdufa_seed.csv` | **4 rows** |
| `coverage_gaps.csv` (missed, with drug+date) | **40 rows, pre-filled** |

The misses (`qa_diff.json → pdufa_only → in_bpc_not_primary`) read like the mega-cap leaderboard: ABBV, ABEO, AZN×2, BAYRY, BIIB, BMY, GH, GILD, GSK, IONS, IRD, **LLY, MRK×3, MRNA, NVO×3, NVS, PFE×2, PTGX×2, REGN×2, RHHBY, ROIV, TAK×2, VRTX**. These are the **highest-search-volume tickers on the board** — the worst possible names to miss for both SEO and product.

## Root cause (confirmed in code)
- `CATALYST_RULES` PDUFA rule (line ~85) + `_PRESS_PDUFA` (line ~423) require a trigger phrase adjacent to a `DAY`/`QH` date in an 8-K/6-K or FMP news item. Solid for clean filers — structurally blind to mega-caps that don't issue a standalone "PDUFA date" PR.
- `bigpharma_pdufa_seed.csv` is loaded (line 1231, via `load_device_seed`) and ships `redistribute=True` — but it's 4 rows, so it backfills ~4 of ~36 needed.
- The recall metric (`qa_diff`, line 287) keys on `ticker:YYYY-MM`, so a precision mismatch (you have `LLY:2026`, BPC has `LLY:2026-12`) counts as a miss even when it's the same catalyst — so **true recall is a touch higher than 46%, but the mega-cap gap is real.**

## The fix (prioritized)

**1. [Biggest win, ~1–2 hrs] Expand `bigpharma_pdufa_seed.csv` from 4 → ~40 rows.** Your `coverage_gaps.csv` already has ticker+date+drug+indication for the 40 missed names — it's a pre-filled worksheet. For each, add a `source_url` (the company PR or FDA/Drugs@FDA link) so it can ship `redistribute=True` with provenance, then append to the seed. **This single step takes PDUFA recall from 46% → ~90%+** and puts every mega-cap headline (LLY, NVO, MRK, PFE, AZN, VRTX…) on the calendar. Make it a maintained file; re-curate the diff each run.

**2. [Close the loop — make it self-completing] Auto-emit seed candidates.** At the end of each run, write `qa_diff → in_bpc_not_primary` (PDUFA only) to `catalysts_out/seed_candidates.csv` (ticker, date, drug, indication pulled from `coverage_gaps.csv`). Then the weekly job is: open that file, paste a `source_url` per row, append to the seed. Over 2–3 runs the seed converges to BPC parity and stays there.

**3. [Structural recall — so you stop depending on the seed] Add two mega-cap-aware sources:**
   - **Earnings-call transcript + 10-Q narrative mining.** Mega-caps disclose PDUFA dates in pipeline sections of earnings materials, not standalone 8-Ks. FMP has transcripts (`/earning_call_transcript`) and you already pull 10-Q; run `_PRESS_PDUFA` over transcript + 10-Q body text for in-universe mega-caps. This catches LLY/MRK/PFE/BMY/GILD/REGN/IONS/VRTX without manual curation.
   - **Foreign IR/PR feeds for ADRs.** AZN/NVO/NVS/RHHBY/BAYRY/TAK/GSK announce via foreign press + 6-K with varied phrasing. Add their investor-relations RSS (or broaden the `fmp_news_catalysts` query) and loosen the date-proximity window for these tickers.

**4. [Metric hygiene] Match on `ticker+drug` (or `ticker+quarter`), not `ticker:YYYY-MM`,** in `qa_diff` so date-precision differences don't deflate recall or pollute the gap list. Also normalize BPC "Regulatory Decision" → your "PDUFA" when comparing.

**5. [Don't over-invest] You already beat BPC on readouts (1,000 vs 444).** If anything, *trim* the readout noise (healthy-volunteer Phase-1 PK studies dilute the signal — see earlier `/readouts` notes) rather than chase more.

## One-line answer to "how do we match BPC?"
Your crawler already matches/beats BPC everywhere **except mega-cap PDUFAs**, and it already outputs the exact list it's missing (`coverage_gaps.csv`, 40 rows, pre-filled). **Paste those into `bigpharma_pdufa_seed.csv` with a source link → ~90% recall today; add transcript/10-Q mining → self-completing parity.** It's curation + a feedback loop, not a new crawler.

*— Red Team Pass 16 (crawler vs BPC coverage audit).*
