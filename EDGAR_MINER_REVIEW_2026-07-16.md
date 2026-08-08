# edgar_miner.py review — 2026-07-16

**Verdict: yes, materially better — but for ACQUISITION, not extraction. Don't replace the
miner with it; replace the miner's SEC leg with it and keep the extraction.**

---

## 1. The finding that decides it: the SEC leg sees 4.4% of the corpus

`phase_readout_miner.sec_guidance_readouts()`:
```python
quota = max(30, max_docs // max(1, len(GUIDANCE_PHRASES)))   # 1500 // 26 = 57
```
Every phrase is hard-capped at **57 documents**. That is the wall of `57`s in the run log, and
~16 of the 26 phrases hit it exactly — i.e. they saturated and were silently truncated.

Measured against EDGAR FTS over the miner's own window (450d lookback, its 8 forms):

| phrase | true total | miner takes | missed |
|---|---:|---:|---:|
| topline results | 2,337 | 57 | 2,280 |
| topline data | 2,409 | 57 | 2,352 |
| results anticipated | 1,726 | 57 | 1,669 |
| conference call to discuss | 4,298 | 57 | 4,241 |
| data readout | 836 | 57 | 779 |
| data expected in | 696 | 57 | 639 |
| **10 phrases total** | **12,900** | **570** | **12,330** |

**Coverage: 4.4%.** And *which* 57 you get is arbitrary — whatever EDGAR returns first. This is
not a tuning knob; it is the ceiling on the entire SEC leg. The quota itself was a fix (it
replaced a worse bug where phrase #1 ate the whole budget and 25 phrases never ran) — but it
converted total starvation into uniform truncation.

`edgar_miner._fts_pages()` has no quota: it paginates to exhaustion and **recursively splits the
date window** when a window saturates EDGAR's 10k cap. That is the right shape.

## 2. What else it does better

- **SIC-scoped universe.** `build_universe()` enumerates every filer under a SIC — including
  delisted/defunct ones, so no survivorship bias. The current miner goes CT.gov `sponsor` name →
  fuzzy `resolve_ticker()`, which fails on every name variant. SIC is an identity, not a guess.
- **EX-99.* exhibit discovery.** `company_jobs()` parses `{accn}-index.htm` and pulls the
  press-release exhibits off 8-K/6-K. That is where readout language actually lives.
- **Disk cache + resumable** (`.scanned` keyed by a phrase hash). **This is the honing loop.**
  Today, re-running with a new phrase re-downloads everything. With a cache you iterate regexes
  offline at zero API cost. You cannot tune what costs 40 minutes per attempt.
- **Local regex** (`scan`). FTS can only ask "does this exact string appear". It cannot ask "is a
  readout verb NEAR a date" — which is the actual question.
- **Correct rate limiting.** Thread-safe global limiter, 6 rps under SEC's 10.

## 3. Verified live, not assumed

- `efts.sec.gov/LATEST/search-index` → HTTP 200; `_source` **does** contain `sics` (`['2834']`),
  so the SIC filter in `cmd_fts` works. This was the one assumption that could have silently
  dropped every row.
- `browse-edgar?action=getcompany&SIC=2836` → HTTP 200, `tableFile2` parses, 100 rows/page.
- FTS returns **100 hits per page**, so `_fts_pages`' `frm += len(hits)` paginates correctly.
- `fts --sic-preset biotech --phrase "topline data"` over 2 weeks → 19 in-industry hits, 1 request.

## 4. What it does NOT do — why it is not a drop-in

It finds **phrase hits with context**. It has no idea what a readout is. The current miner's real
value is the extraction layer on top:
`milestone_of()` · `trial_name()` · `period_bounds()` · `is_catalyst()` · imminence tiering ·
`enrich_from_filings()` · the NON_CATALYST / PK scrub.

**Use edgar_miner as the acquisition front-end; feed `hits.csv` into that extraction.**

## 5. SIC codes (filled in)

Measured 2026-07-16: of 100 8-Ks containing "topline data" YTD, five SICs cover **96**.

| SIC | industry | share |
|---|---|---:|
| 2834 | Pharmaceutical Preparations | 57% |
| 2836 | Biological Products | 29% |
| 2833 | Medicinal Chemicals & Botanicals | 5% |
| 2835 | In Vitro & In Vivo Diagnostics | 3% |
| 8731 | Commercial Physical & Biological Research | 2% |

Wired in as `--sic-preset biotech` (also `pharma` = 2834+2836 ≈ 86%, and `life-sciences` which
adds 3841/3826/3845 for devices). A preset beats retyping codes: a forgotten code is a silent
coverage hole, and silent holes are the recurring failure mode here.

## 6. Keywords (filled in) — two files, because the two modes are different tools

- **`readout_phrases_fts.txt`** — exact fragments only (`fts` rejects `re:`).
  Governed by the **adjacency rule**: EDGAR only matches quoted words that are ADJACENT, so
  `"to report topline"` does NOT match *"to Report 36-Week Topline Results"*. Long, natural,
  precise-feeling phrases match almost nothing. Short universal fragments find the DOCUMENT; the
  regex finds the DATE.
- **`readout_phrases_scan.txt`** — regex, for `scan`. Four labelled classes:
  A committed window · B exact day · C **clock-starters** (enrollment complete / LPLV / database
  lock — the current miner ignores these entirely, and they are datable and early) ·
  D **negative controls** (long-term follow-up, already-reported, met/missed) — don't delete
  these; a D hit on the same document as an A/B hit means the A/B hit is probably not upcoming.

**Backtracking warning is load-bearing.** `scan` has no `PR_TEXT_CAP` — it searches the FULL
document. The miner's `PR_SCHED` chained `[^.]{0,150}?` and burned **649 CPU-seconds** on one
40 KB filing, then died silently. Every pattern in the scan file bounds its gaps, uses `[^.]` to
stay inside a sentence, and chains at most two.

## 7. Honest limits — what more EDGAR will NOT buy you

From the fresh run (n=158 sec_edgar rows):

| | |
|---|---|
| `date_precision = day` | **0 of 158** |
| quarter/half | 158 |
| `imminence = PAST` | **105 of 158 (66%)** |
| `confidence` | all 0.7, uniform |

**SEC full-text yields exactly zero exact days, and better phrases will not change that.** A
scheduling PR ("we will report topline on July 13") is usually not material enough to furnish as
an 8-K exhibit, so it never enters EDGAR — it goes over the newswire. That is a structural fact,
not a coverage gap. Exact days come from the FMP newswire leg (median T-3, n=4/205 tickers) or
conference schedules (~T-99).

What fixing the 57-cap *does* buy: far more **company_guidance** rows — the committed windows
CT.gov's estimate cannot give you. Today only 53 of 310 workbook rows (17%) are company-stated;
the other 257 are CT.gov guesses. That ratio is the thing worth moving.

Also: 66% of SEC rows are PAST (stale guidance whose window already closed). `--imminent-days`
does not catch them — its test is `days_to_readout <= N` and a PAST row's value is negative, so
it passes. `build_readout_xlsx.py` now drops them at build. **Better to filter at the source.**

## 8. Recommended next step (not yet done)

1. `python edgar_miner.py universe --sic-preset biotech` → cache the filer list.
2. `python edgar_miner.py scan --universe out/universe_*.csv --phrases readout_phrases_scan.txt
   --forms 8-K 6-K 10-Q --years 1.5` → builds the local doc cache + `hits.csv`.
   First run is slow; every later run is free.
3. Write `hits.csv` → the miner's existing `milestone_of()`/`period_bounds()` extraction, emitting
   the same schema, and drop PAST at the source.
4. Measure: `date_precision=day` count and company-stated share vs today's 0 and 17%.
   **Those two numbers are the scoreboard.** Everything else is motion.
