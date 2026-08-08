# conf_study/ — Conference Run-up Dataset (BUILDER: START HERE)

**The published `/research/conference-runup` page currently uses 256 events. This folder has 1,425.**
Facts only — no scores, no win rates, no recommendations.

## USE THIS
| File | What it is |
|---|---|
| **`conference_runup_FULL_v2.csv`** | ⭐ **THE STUDY DATASET — 1,425 priced events, 2017–2026, 399 tickers.** Run-ups (D-30/-20/-10/-5 → D-1), event_day, post_5d, post_10d + 40 metadata fields. **Republish the page from this.** |
| `MASTER_conference_events_ENRICHED_v2.csv` | 1,458 event universe (incl. unpriced) |
| `si_panel_2017_2026.csv.gz` | FINRA short interest — 3.63M rows, 47,243 tickers, 2017–2026 |
| `si_at_catalyst_PDUFA.csv` | SI at each PDUFA, **T-1 compliant, zero lookahead** (96.4% coverage) |
| `si_at_catalyst_CONFERENCE.csv` | SI at each conference event (93.8% coverage) |
| `conf_events_2026_all.csv` | 107 conference events in 2026 (AACR 63, AAN 13, ASCO 6, …) |
| `RUN_LOCALLY_build_study.py` | Re-runs prices (FMP) + recomputes. **Needs `FMP_API_KEY`.** |
| `px_fmp.json` | Price cache (390 tickers). Script auto-fetches any missing. |

## Key columns in `conference_runup_FULL_v2.csv`
`ticker, anchor, conf, conf_full, pres_type, cap_tier_final, market_cap, stage, indication, ta,
runup_30d, runup_20d, runup_10d, runup_5d, event_day, post_5d, post_10d,
btd, orphan, priority_review, fast_track, accelerated_approval, gene_therapy,
surrogate_endpoint, single_arm_study, had_adcom, historical_crl_rate, sponsor_prior_approvals,
si_t1_days_to_cover, si_t1_short_to_adv, year, src`

## Findings the current page is MISSING
- **2020 was a bubble:** median **+17.27%** (n=47) — 5× any other year. **2022–24 were negative** (−3.3%, −2.9%, −1.7%). This is the whole story and the page can't see it (it starts mid-2022).
- **Nano-cap = −9.84%** (n=42), the *worst* cohort. The page omits the nano tier entirely.
- **Post-event fade:** event day −0.48% · D+5 −1.55% · D+10 −1.92%.
- **Tails:** only 49.5% positive; 15.6% ran ≥25%; 6.3% ran ≥50%. Mean +5.41% vs median −0.35%.
- Page publishes **AACR at n=13** (my n=122) and **ASH at n=47** (my n=201) → its numbers skew positive.

## Window convention — pick one and state it
Published page: D-30 = **21 trading days** (≈30 calendar). This dataset: **30 trading days**. Not comparable. Recompute or relabel.

## Known gaps (state on the page)
1. **Anchor = date the data was reported**, not the abstract/title-drop date. Dual-anchor is the next upgrade.
2. **Selection bias:** universe is "readouts presented at a conference," not all presenters.
3. **2026 is AACR-heavy** (63 of 107). Full-year 2026 needs a presenter source (conference agendas / company PRs) — ASCO26, EHA26, ADA26 are thin; ESMO/ASH 2026 haven't happened yet.
4. `pres_type` mostly `unspecified` — catalyst text rarely encodes oral/poster.
5. 3 tickers (PALI, PYPD, UPB) not yet priced — `RUN_LOCALLY_build_study.py` will fetch them.

## Rules
No win rates. No scores. No tiers. No sizing. No entry/exit. Median + IQR + n only.
**Conference Overlay v1.0 is REFUTED** — it claimed nano/micro +4.88%; actual nano is **−9.84%**. Do not use it.
