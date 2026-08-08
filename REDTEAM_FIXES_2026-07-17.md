# Red-team backlog — fixes applied 2026-07-17

Against `_MASTER_BACKLOG.md` (2026-07-13). Verified on the Windows filesystem, not the sandbox
mount (the mount serves a stale view of job-written files — see note at bottom).

## DONE — data integrity (P0) + guards

### P0-0 / P0-1 — conference CSV truncation (715 → 224) FIXED at the source
The canonical `conference_presentations_history.csv` was truncated to 224 rows / 11 conferences.
Root cause traced precisely: `safe_to_csv()` wrote without `QUOTE_ALL`, so an embedded newline in
a press-release `snippet` split one logical row across two physical lines. The next crawl's merge
does `_old = pd.read_csv(_cp)` → the unterminated field truncates the read → `concat + dedup +
rewrite` bakes the loss in permanently. One bad snippet, and the file shrinks on every subsequent
run.

Three-part fix in `catalyst_crawler.py`:
1. **`safe_to_csv` hardened** — `quoting=csv.QUOTE_ALL` + strip `\r\n` from every object cell
   before writing. A field can now never span a physical line; round-trip-safe by construction.
2. **Shrink-guard on the conference merge** — if a rebuild would drop >5% of rows or lose any
   conference vs what is on disk, it REFUSES to overwrite, keeps the good file, and writes a
   `.rejected_<ts>.csv` for review. History only grows; a crawl that returns less must fail loudly.
   Good writes snapshot a `.prev.csv` regression baseline.
3. **Restored** the complete 715-row / 39-conference / 240-ticker file from the
   `pre_rebuild_20260712_160021` backup, re-written through the hardened path. Round-trip re-read:
   715 rows, 0 ragged. Truncated file kept as `.truncated_224_2026-07-17.csv` for forensics.

### P0-2 — fabrication guard: already shipped, verified
`tests/test_no_fabricated_conferences.py` already enforces the year-wins / future-cue / past-tense
rules, ragged-row detection, dedup, and junk-label checks, and reads the canonical file. Passes on
the restored 715 rows: 0 fabrications, 0 dupes, 0 junk, 0 ragged.

### NEW CI guards (block deploy)
- **`tests/test_crawler_no_regression.py`** — the P0-0 backstop. Fails if rows/conferences/tickers
  collapse >5% vs the `.prev.csv` baseline. "Data can be corrected, never silently reduced."
- **`tests/test_seo_invariants.py`** (SEO-1) — fails if any public `<title>` or social/description
  meta ADVERTISES `ODIN | AI score | approval probability | win rate | TIER_1 | "NN% approval
  rate"`. Negation-aware: "No approval probabilities" (the brand promise) and "Odin Catalyst LLC"
  (the company) pass; "ODIN Scores" and "TIER_1 … 93.6% approval rate" (the exact stale-index
  offenders) fail. Verified with injected positive/negative controls.
- **`tests/test_si_display_cap.py`** (P1-2) — fails if any page renders raw days-to-cover >60
  without "very illiquid" context.

### P1-1 — unified-panel dupes: already fixed
`conf_study/UNIFIED_catalyst_panel.csv` now has 0 duplicates on (ticker, date, catalyst_type).
Was 202 on 07-13; resolved since. No action needed.

### P1-2 — SI display cap: NOT a live defect (guarded for when it becomes one)
app.html renders zero short interest and the data feed exposes no per-ticker DTC. The only SI
surface, `/research/short-interest-fda`, already excludes DTC>60 and shows sane medians (2.2–6.8
days). The new guard enforces the cap the moment per-ticker DTC renders (i.e. when P1-5 ships),
rather than after "4,200 days to cover" is public.

## NOT DONE — and why

- **P0-3 — DO NOT rebuild `/research/conference-runup` from EDGAR.** This is a "don't", not a task.
  EDGAR recall on large-caps is 38% (a poster is immaterial to Merck, no 8-K), and rebuilding would
  strip half the large-caps and move the headline for sampling reasons. Left alone, correctly. The
  real fix (multi-source EDGAR + PR + abstract DBs, publish recall per tier) is a build, not a patch.
- **P0-4 — CLAUDE.md still mandates leaked ODIN v14.** OWNER ACTION: I don't edit the global
  CLAUDE.md. It should replace the ODIN block with v19-PRUNE and mark v14 KNOWN LEAKED. The MCP
  already flags it; the doc lags.
- **P0-5 / P1-4 — ODIN & BIFROST retrains** (capped `prior_crl_count`; T-1 SI panel). Real retrains
  on real pipelines — their own session, not a same-turn change.
- **SEO-1 indexing — request re-index** for `/`, `/calendar`, the legacy 301s + 3 research pages in
  Search Console. OWNER ACTION (no API access here). The live pages are already clean; this evicts
  the stale index. The new `test_seo_invariants` guard keeps them clean going forward.
- **P1-3 — `/ticker/{TICKER}` hubs** (~400 pages). The biggest SEO lever, but a substantial build;
  flagged for a dedicated effort, not folded into a fixes pass.
- **P2 items** — mostly publish/polish or owner keys (Stripe price IDs, RESEND_API_KEY). Not blocking.

## Files
- `catalyst_crawler.py` (hardened; `.bak_2026-07-17`)
- `catalysts_out/conference_presentations_history.csv` (restored 715 rows, QUOTE_ALL)
- `catalysts_out/conference_presentations_history.prev.csv` (regression baseline)
- `tests/test_crawler_no_regression.py`, `tests/test_seo_invariants.py`, `tests/test_si_display_cap.py` (new)

## Environment note
The sandbox mount serves a STALE view of files written by the Windows daily job / crawler (it
showed a truncated price cache earlier this session). All state above was verified via PowerShell
on the real filesystem. Anything the daily job touches must be read from Windows, not the mount.
