# Catalyst Gap Scan — 2026-05-18

**Source file:** `historical_2026-05-18.xlsx` (3,542 rows, Jan 2 2025 → May 15 2026)
**Predictions universe:** master prediction log (`ODIN_MASTER_PREDICTION_LOG_v3_2026-05-01.md`) + 26 JSON amendments (001–028)
**Scan basis:** Coverage gaps + stale dates + outcome reconciliation + model version freshness
**Real data only:** all inputs verified, no fabrication, mismatches surfaced rather than smoothed (Amendment 027)

---

## VERIFIED FACTS

- File holds **3,542 catalysts** across 17 months. After Amendment 028 panel-integrity dedupe rules, **76** are ANDAs (excluded from binary-catalyst comparisons) and **2,405** are trade-relevant.
- Our master prediction log + 26 amendments names **40 unique tickers** under **22 V-IDs**. This is a curated forward-decision ledger, not a backtest universe — it is correct that most of the file is not in it.
- Raw coverage: 8.4% of trade-relevant file catalysts overlap a logged prediction. **This number is not the headline** — it just confirms the log is selective. The real findings are below.

---

## INFERRED INTERPRETATION — THE FOUR FINDINGS THAT MATTER

### Finding 1 — TIER A: PDUFA dates in forward picks are STALE (CMPX-class drift)

The `runup_predictor` module ran on **2026-04-29** and produced V-030 through V-046 with PDUFA dates that, when checked against the catalyst file *and* the Friday pre-flight verifications, disagree with reality on multiple picks. This is exactly the type of drift the Friday Rule-0 sweep is designed to catch — but it lives inside our own log, not in the outside world.

| V-ID | Ticker | Log says | Reality (file + pre-flight) | Drift | Action |
|---|---|---|---|---|---|
| V-030 | MNKD | PDUFA 2026-05-08 | Afrezza pediatric sBLA PDUFA **2026-05-29** | +21d | UPDATE date |
| V-031 | CING | PDUFA 2026-05-10 | NDA filed 2025-08-06; per pre-flight PDUFA **2026-05-31** | +21d | UPDATE date |
| V-032 | TLX | PDUFA 2026-05-14 | File shows only NDA resubmission 2026-03-16 (TLX101-Px) — no 5/14 PDUFA | wrong date entirely | INVESTIGATE / drop or re-verify with company IR |
| V-033 | ARVN | PDUFA 2026-05-15 | **Approved 2026-05-01** (Amendment 006 captured this — 35 days early) | -14d | already amended ✓ |
| V-034 | NUVL | PDUFA 2026-05-21 | NDA only **submitted 2026-04-07** — PDUFA cannot land 6 weeks later (typically 6-12mo) | impossibly early | INVESTIGATE (likely runup_predictor pulled wrong date) |
| V-035 | ABEO | PDUFA 2026-05-22 | UX111 BLA resubmitted 2026-01-30; Class 1 + 4-mo = May possible | plausible | VERIFY with company IR |
| V-036 | RARE | PDUFA 2026-05-22 | Same UX111 program as ABEO | plausible | VERIFY (joint with ABEO) |
| V-037 | ACHV | PDUFA 2026-05-30 | Per pre-flight, PDUFA **2026-06-20**; company self-disclosed CRL expected | +21d + adverse | UPDATE date + sizing BLOCK |
| V-038 | PTGX | PDUFA 2026-06-02 | File last events 2026-03-30 — no June PDUFA evident | uncertain | VERIFY |
| V-039 | UNCY | PDUFA 2026-06-06 | NDA resubmitted 2025-12-29; per pre-flight PDUFA **2026-06-27 or 06-29** | +21–23d | UPDATE date |
| V-040 | IRD | PDUFA 2026-06-19 | Not in file (likely UTHR Group or different ticker) | unverifiable | INVESTIGATE ticker |
| V-041 | MNKD2 | PDUFA 2026-07-05 | "MNKD2" is not a real ticker — placeholder for second MNKD program | placeholder | RESOLVE to real ticker or drop |
| V-042 | NRXP | PDUFA 2026-07-08 | Not in catalyst file | unverifiable | INVESTIGATE |
| V-043 | VNDA | PDUFA 2026-08-14 | File last VNDA event 2026-02-20 — no Aug PDUFA evident | uncertain | VERIFY |
| V-044 | MLYS | PDUFA 2026-08-24 | Not in catalyst file | unverifiable | INVESTIGATE |
| V-045 | COGT | PDUFA 2026-09-01 | Not in catalyst file | unverifiable | INVESTIGATE |
| V-046 | INO | PDUFA 2026-10-09 | Not in catalyst file | unverifiable | INVESTIGATE |

**Headline:** the runup_predictor batch on 2026-04-29 hard-coded dates that have not been re-verified. At least **5 of 17 forward picks** have demonstrably stale dates (+14 to +23 days). Per Amendment 027 (Real Data Only) and the catalyst_date_verifier_v1 tool shipped in v39.1, these should be re-verified BEFORE any sizing or entry.

### Finding 2 — TIER A (formal): two past predictions have no closing amendment

| V-ID | Ticker | Predicted catalyst | Status |
|---|---|---|---|
| V-030 | MNKD | PDUFA 2026-05-08 (stale — actually 5/29 per Finding 1) | OPEN_NO_AMENDMENT — date wrong, real catalyst still future |
| V-032 | TLX | PDUFA 2026-05-14 (no matching event in file) | OPEN_NO_AMENDMENT — needs investigation, possibly never had a real 5/14 PDUFA |

ALXO V-028 has Amendment 004 closing it (correctly attributed). CABA V-029 has Amendment 001 closing it. ARVN V-033 has Amendments 006 + 007. LNTH has Amendment 010. CRDF, CING, UNCY have no V-IDs yet in the canonical log (they are in memory and trade ledger but not formally amended into the log).

### Finding 3 — TIER B: one real date-drift, already addressed

The only stale prediction date detected against an actual file event is **ARVN V-033 (predicted 2026-05-15, approved 2026-05-01)**. This is the +35-day-early VEPPANU approval already captured by Amendment 006 (the v29 re-score) and Amendment 007 (pre-approval evidence). No new action needed.

### Finding 4 — TIER C: 173 high-priority 2026 H1 catalysts never tracked (audit signal)

Of the **173 high-priority untracked catalysts** in 2026 H1 (PDUFA, Phase 3 readout, Approval, CRL, AdCom — actionable, price ≥ $1):

- **Phase 3 readouts** dominate — most are big-pharma Phase 3 reads (AZN, NVO, LLY, REGN, BIIB, PFE, ROG-ADR) that the framework correctly skips because of size class (large-cap absorbers per BIFROST v4 size tiers).
- **Small/mid-cap Phase 3 reads we never scored**: URGN (UTOPIA, 5/15), CELC (VIKTORIA-1, 5/1 — small-cap, this is the kind of pick worth backtesting), CYTK (ACACIA-HCM, 5/5), CAPR (HOPE-3, 4/22 — already in CAPR concentrated-regime position thesis), NTLA (HAELO, 4/27), BLTE (DRAGON, 4/27), RZLT (sunRIZE, 5/1), DRTS (REGAIN, 5/11), DARE (Ovaprene, 5/12), BBIO (CALIBRATE, 5/12), VTGN (PALISADE-3, 5/12).
- **CRLs we never tracked** (model training signal): GRCE (GTX-104, 4/23), ABBV (TrenibotE, 4/23).
- **Approvals we never tracked but should mine for analog data**: SPRY (neffy age extension, 5/15), ONC (BEQALZI, 5/13), ARGX (VYVGART seronegative, 5/8), ADMA (ASCENIV pediatric, 5/4), REGN (Otarmeni, 4/23), REGN (DUPIXENT CSU pediatric, 4/22), AXSM (AUVELITY agitation, 4/30).

These should be ingested into the training panel for the next ODIN kaizen (v38.2+) and Gungnir kaizen — many are Phase 3 reads with confirmed outcomes which is exactly the supervised signal we want. **Full list of 682 2025+ entries in the xlsx (sheet C_FullPeriod_HighPrio_Gaps).**

---

## UNRESOLVED GAPS

1. **MNKD V-030, CING V-031, ACHV V-037, UNCY V-039 dates need updating in the master log itself** — Friday pre-flight has the correct dates but the log file `ODIN_MASTER_PREDICTION_LOG_v3_2026-05-01.md` still shows the stale ones. Memory references the correct dates but the canonical log does not. **Recommend: append Amendment 029 with the date corrections.**

2. **TLX V-032, NUVL V-034, PTGX V-038, IRD V-040, MNKD2 V-041, NRXP V-042, VNDA V-043, MLYS V-044, COGT V-045, INO V-046** — none of these have catalyst-file events matching their predicted PDUFA dates. The catalyst file is the most authoritative source for past events; for future PDUFAs the only authority is FDA action letters + company IR. Each of these needs the **catalyst_date_verifier_v1.py** workflow run (FDA EDGAR + company IR + Google news) to confirm whether the date is real, was always wrong, or has drifted.

3. **No prediction record has parseable ODIN/Gungnir version in its description text** (all 131 prediction rows returned NaN on version extraction). Predictions inherit the production version at the time of prediction — but we have no per-prediction audit trail of which model version generated which V-ID score. This makes "re-score with current champion" impossible to scope without manual reconstruction. **Recommend: every new V-ID amendment include explicit `odin_version`, `gungnir_version`, `bifrost_version` fields.**

4. **CAPR is not in the master log V-ID universe** — but the Concentrated Regime amendment (031, in memory) allocates 50% of the $75K account to CAPR. This is a major risk-bearing position with no entry in the canonical prediction log. **Recommend: open V-047 for CAPR with full prediction provenance.**

5. **UNCY is also a position but not in the canonical V-ID universe** at the right date — V-039 has the wrong PDUFA date and no closing/opening amendment. **Recommend: amend V-039 with corrected date 2026-06-27 (or 06-29, depending on FDA's actual assignment) + open position entry.**

---

## RED-TEAM OBJECTIONS

1. **ANDA classification is heuristic** — I excluded 76 rows via regex on "ANDA" / "generic" / "biosimilar." Could be miscalibrated either way. Spot-check before merging into any training panel. (Amendment 028 calls for the `catalyst_panel_validator_v1.py` to enforce this — that tool should be the canonical filter.)

2. **The "8.4% coverage" stat is misleading** if read as a quality metric — the log is selective by design. The actionable framings are TIER A (stale picks) and TIER C (untracked high-priority events that could enrich training).

3. **Some "forward open" V-IDs may already be effectively dead** — the runup_predictor batch on 2026-04-29 generated picks that have since been overridden by Discipline Layer, Concentrated Regime (031), and Pre-Investment Discovery rules (e.g., ACHV V-037 should be BLOCK per self-disclosed CRL + warrant overhang). The log doesn't reflect these overrides. **Recommend: bulk-amend with status updates (KILLED / SUPERSEDED / VERIFIED) for every still-future V-ID.**

4. **Drift detection cutoff of 7 days is arbitrary.** ±3 days might catch more real drift; ±14 might miss CMPX-class (CMPX was a *same-day* surprise so any date-drift cutoff misses it). The protective measure for CMPX-class is the Friday Rule-0 sweep itself, not this gap scan.

5. **File ends 2026-05-15 (3 days behind today).** Any catalysts that landed between 5/15 and 5/18 will appear as gaps in this scan even though they are simply outside the file's window. None of the high-priority 5/16–5/18 events are in our prediction log so this is not a TIER A issue, but worth flagging.

---

## CONCLUSION + RECOMMENDED ACTIONS

| Priority | Action | Cost | Why |
|---|---|---|---|
| HIGH | Run `catalyst_date_verifier_v1.py` on V-030, V-031, V-032, V-034, V-037, V-038, V-039, V-040, V-041–V-046 | 30 min | At least 5 of 17 forward picks have demonstrably wrong dates; risk = entering positions sized for a PDUFA that's not actually happening |
| HIGH | Amendment 029 — bulk date corrections for V-030/031/032/034/037/039 | 15 min | The canonical log needs to match Friday pre-flight reality |
| HIGH | Open V-047 for CAPR with full provenance | 10 min | 50% of $75K account is in CAPR per Amendment 031 — must be in canonical log |
| MED | Update V-039 with current UNCY position + verified date | 5 min | Position is open; log doesn't reflect it |
| MED | Add `odin_version` / `gungnir_version` / `bifrost_version` fields to every new V-ID | ongoing | Enables future re-score audits |
| LOW | Ingest TIER C (173 actionable 2026 H1 catalysts) into next kaizen training panel | 1-2 hrs | Free supervised signal for v38.2+ and Gungnir kaizen |
| LOW | Mark dead V-IDs (KILLED / SUPERSEDED) so log reflects current truth | 20 min | Removes ambiguity about whether V-046 INO Oct PDUFA is still a live pick |

**Bottom line:** The scan found real problems, but the highest-leverage one is internal — our own forward picks have stale dates that the catalyst file would have caught at the time. The Friday pre-flight catches new external drift; this gap scan would have caught our own runup_predictor batch errors *on April 29 when they were created*. Consider running it monthly going forward — not just on demand.

---

## Files written to /Odin Perfection/

- `catalyst_gap_report_2026-05-18.md` (this report)
- `catalyst_gap_report_2026-05-18.xlsx` (5 tabs: Summary, A_Need_Closing, ForwardOpen_Picks, B_Date_Drift, C_2026H1_HighPrio_Gaps, C_FullPeriod_HighPrio_Gaps)
- `forward_watchlist_missed_2026-05-18.csv` (TIER C actionable list for ingestion into next kaizen — note: file is historical, so this is a backtest-candidate list, not forward picks)
