# Running the full pdufa.bio catalyst crawler

**What it does:** mines PRIMARY sources only — SEC EDGAR (8-K/6-K/10-Q, full-text), ClinicalTrials.gov,
FDA advisory-committee calendar, openFDA, FMP press/news — for every catalyst type, tags each row with
its source/URL/snippet/confidence, and writes a republishable `catalysts_public.csv`
(only rows we independently sourced, `redistribute==True`). BioPharmaCatalyst is used
only as an internal QA seed (never republished).

## NEW (v2): "get everything" — 3-layer universe so we stop missing names
1. **Layer 1 — auto-universe (`--auto-universe`):** each run rebuilds the ticker universe from the
   **full FMP healthcare screener** (biotech + pharma + device/dx ≈ 960 tickers), unioned with the
   static `pdufa_universe.txt` + device seed. No more static-list rot.
2. **Layer 2 — discovery (`--discover`):** runs SEC EDGAR full-text search for PDUFA/CRL/BLA across
   **ALL filers**, not just our universe — catches off-list and newly-filed names automatically.
3. **Layer 3 — closure:** any newly-discovered ticker is written to `catalysts_out/universe_effective.txt`.
   Feed that back as `--tickers` next run and the universe self-completes.
Plus a curated `bigpharma_pdufa_seed.csv` for foreign/mega-cap PDUFAs (RHHBY/BAYRY/ALPMY/LLY…) that
don't file clean US PRs and can't be auto-mined.

## Steps
1. Keep these in the same folder: `catalyst_crawler.py`, `pdufa_universe.txt`, `device_seed.csv`,
   `bigpharma_pdufa_seed.csv`, `fda_2026-06-19.xlsx`, and the run script.
2. **Windows:** double-click `run_crawler_full.bat` (it reads your keys from `Odin Perfection\.env_master`).
   **Mac/Linux:** `bash run_crawler_full.sh` (keys are set inside the script).
3. The command now includes **`--auto-universe --discover`**. Expect **~2–4 hours**
   (~960+ tickers × SEC full-text + CT.gov + the all-filer discovery pass, politely throttled).
   It's resumable-ish; if it dies, just re-run.
4. When it finishes, send me **`catalysts_out/catalysts_public.csv`** and I'll fold the refreshed,
   fuller catalyst set into the live site + regenerate the SEO pages.

## What you get (in `catalysts_out/`)
- `catalysts_public.csv` — republishable catalysts with provenance (the product feed).
- `catalysts_primary.csv` — full set incl. lower-confidence guidance dates.
- `universe_effective.txt` — every ticker that produced a catalyst (the self-completing universe).
- `qa_diff.json` + `coverage_gaps.csv` — PDUFA **recall vs BPC** (target 90%+) and any names still missed.

## Notes
- SEC requires the `--ua` contact header (already set to your email).
- No BPC data is republished — only primary-sourced rows. That's what keeps the content original.
- `bigpharma_pdufa_seed.csv` is hand-editable; add `source_url` for each foreign PDUFA before
  republishing for full provenance (rows ship `redistribute=True` like the device seed).
- Re-run weekly (or nightly). After the first run, point `--tickers` at `universe_effective.txt`
  to carry forward everything discovery found.
