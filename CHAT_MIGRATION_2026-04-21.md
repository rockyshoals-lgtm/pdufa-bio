# 9Realms Chat Migration — Form 4 Saturation Test

**Date:** 2026-04-21
**Purpose:** Resume Form 4 historical insider time-series Kaizen in a new (smaller) chat.
**Context budget:** This file is the complete hand-off. New chat should read this, then execute Step A.

---

## TL;DR — what is running and why

Executing **Priority #1 / B1 — Form 4 historical insider time series 2015-2026** as the decisive test of the 9-NULL saturation thesis across ODIN v14, Gungnir v46, and BIFROST Explosion v5.6 honest bars.

Nine consecutive honest-Kaizen NULLs make Form 4 the single highest-probability orthogonal signal family remaining. If F4 also NULLs on all three engines, local-to-T-1 feature engineering is declared saturated and the roadmap pivots to new event types / new data sources only.

Directive from user that still applies: "start on the improvements, start at 1, be relentless."

---

## Current Stage 4 state (2026-04-21 ~13:00 PDT)

- **Parser PID:** 122 (relaunched this session with `python3 -u` for unbuffered stdout)
- **Tickers on disk:** 167 of 449
- **Last checkpoint `_progress.json`:** 80 tickers, 7,307 filings, 3.92 filings/s, ETA ~141 min (stale — actual on-disk is 167)
- **`_summary.json`:** NOT yet written (Stage 4 not complete)
- **Log:** `form4_parse.log` — now unbuffered, should start producing output within ~30s of launch
- **Parser died twice.** It is fully resume-safe (scans `form4_parsed/` at startup, skips completed tickers). If it dies again, just relaunch — no data loss.

Relaunch command (idempotent):
```
cd /sessions/confident-serene-ptolemy
nohup python3 -u build_form4_parse.py > form4_parse.log 2>&1 &
```

---

## Key paths

- **Workspace (F4 artifacts):** `/sessions/confident-serene-ptolemy`
- **Base (persistent 3-engine artifacts):** `/sessions/confident-serene-ptolemy/mnt/9realms`
- **Stage 4 parser:** `/sessions/confident-serene-ptolemy/build_form4_parse.py`
- **Stage 4 output dir:** `/sessions/confident-serene-ptolemy/form4_parsed/` (per-ticker JSONs + `_progress.json` + eventual `_summary.json`)
- **Stage 5 feature builder:** `/sessions/confident-serene-ptolemy/build_form4_features.py`
- **Stage 5 output:** `/sessions/confident-serene-ptolemy/form4_event_features.csv`
- **Stage 6a ODIN eval:** `/sessions/confident-serene-ptolemy/mnt/9realms/form4_odin_honest_eval.py`
- **Stage 6b Gungnir eval:** `/sessions/confident-serene-ptolemy/mnt/9realms/form4_gungnir_honest_eval.py`
- **Stage 6c BIFROST Explosion eval:** `/sessions/confident-serene-ptolemy/mnt/9realms/form4_bifrost_explosion_honest_eval.py`
- **Result JSONs (Stage 6 outputs):** `/sessions/confident-serene-ptolemy/form4_*_honest_results.json`

---

## Step A — FIRST ACTION on resume (copy-paste)

```
cat /sessions/confident-serene-ptolemy/form4_parsed/_progress.json
ls /sessions/confident-serene-ptolemy/form4_parsed/*.json | wc -l
ls /sessions/confident-serene-ptolemy/form4_parsed/_summary.json 2>&1
pgrep -af build_form4_parse || echo "parser not running"
tail -20 /sessions/confident-serene-ptolemy/form4_parse.log
```

Interpretation:
- If `_summary.json` exists → Stage 4 done, go to Step C.
- If parser is running and ticker count is increasing → wait. Check again in 15-30 min.
- If parser not running AND `_summary.json` missing → relaunch (Step B).

## Step B — Relaunch Stage 4 (if dead)

```
cd /sessions/confident-serene-ptolemy
nohup python3 -u build_form4_parse.py > form4_parse.log 2>&1 &
sleep 5
pgrep -af build_form4_parse
tail -10 /sessions/confident-serene-ptolemy/form4_parse.log
```

The parser is resume-safe: it builds the `todo` list as `tickers_needed - tickers_already_in_form4_parsed`. Relaunching is always safe.

SEC rate-limit compliance locked in script: UA="9Realms Research rockyshoals@gmail.com", RATE_LIMIT_S=0.11 (~9 req/s under the 10 req/s cap).

## Step C — Run Stages 5 → 6a → 6b → 6c (once `_summary.json` exists)

```
# Stage 5 — engineer 20-25 event features
cd /sessions/confident-serene-ptolemy
python3 build_form4_features.py

# Stage 6a — Form 4 x ODIN v14 honest eval
cd /sessions/confident-serene-ptolemy/mnt/9realms
python3 form4_odin_honest_eval.py

# Stage 6b — Form 4 x Gungnir v46 honest eval
python3 form4_gungnir_honest_eval.py

# Stage 6c — Form 4 x BIFROST Explosion v5.6 honest eval
python3 form4_bifrost_explosion_honest_eval.py
```

Each Stage 6 run produces a JSON result file in `/sessions/confident-serene-ptolemy/` with methodology, C sweep, greedy log, final val/test AUCs, bootstrap 95% CIs, and verdict.

## Step D — Stage 7 findings memo + CLAUDE.md update

Write `Form4_Three_Engine_Findings.docx` (use docx skill). Update `CLAUDE.md` with:
- Per-engine verdict (PROMOTE / FLAT / REGRESSION)
- NULL count update (currently 9 → 10/11/12 if all three NULL)
- Saturation thesis status (CONFIRMED or BROKEN)
- Next-priority signal families in roadmap

---

## Honest 3-way split (locked across all three engines)

- **ODIN / Gungnir:** Timestamp-based. train ≤ 2022-12-31 / val 2023-01-01 to 2024-12-31 / test ≥ 2025-01-01
- **BIFROST Explosion:** String-year. train year ≤ "2023" / val == "2024" / test year ≥ "2025"
- **Target:** `big_move = 1.0 if abs(post_1d) > 25 else 0.0` (for Explosion); native outcome labels for ODIN/Gungnir
- **Selection discipline:** val-only greedy forward, gate Δval_AUC ≥ +0.002, MAX_ROUNDS=10. Test touched ONCE. Bootstrap 95% CI n_boot=2000, seed=42, percentile.

## Deployed honest bars (what F4 must beat)

- **ODIN v14 honest test AUC:** 0.8995 (under val-only C selection, deployed C=0.10 leaked → honest winner C=0.01)
- **Gungnir v46 honest test AUC:** 0.7841 (3-way split), honest Final HO 0.7551
- **BIFROST Explosion v5.6 honest bar:** 0.8861 (v5.5 deployed 0.9487 leaked by +626 bp)

BIFROST Stage 6c verdict rule (from `form4_bifrost_explosion_honest_eval.py`):
```
if final_test_auc > V56_HONEST_BAR + 0.002 AND p_lift_gt_0 >= 0.975:
    PROMOTE
elif final_test_auc > V56_HONEST_BAR - 0.005:
    FLAT (v5.5 stays deployed)
else:
    REGRESSION (v5.5 stays deployed)
```

V56_HONEST_BAR = 0.8861. GATE for greedy = +0.002. C_SWEEP = [0.005, 0.01, 0.03, 0.05, 0.10, 0.25].

BIFROST baseline is FIXED V58_FINAL_60 (57 V54_BASE + v58_abs_runup_7d + v58_vol_ratio_log + v58_drawdown_x_small). Baseline is NOT pruned — F4 candidates are added on top via greedy forward. Ridge-only architecture wins (confirmed in v5.8).

---

## Context — the 9-NULL saturation pattern

Honest-Kaizen NULL count (chronological):
1. BIFROST Explosion v5.7 — non-linear transforms
2. BIFROST Explosion v5.8 — architecture sweep + 37 local features
3. BIFROST Explosion v5.9 — ORATS historical options panel (128 candidates)
4. Gungnir v47 — backward elimination honest rebuild
5. ODIN v17 — HINT trial-success prior
6. Smart Money Phase 3 — 13F god tier features on ODIN (10 funds, 1233/2223 events)
7. SI × ODIN — historical short interest time series
8. SI × Gungnir — same SI panel, Gungnir target
9. Smart Money Q2 pre-screen

Form 4 is the **10th test** and — per the locked plan — the single remaining orthogonal signal family with non-trivial expected info value before declaring local-feature saturation complete.

---

## Champion models (DO NOT FALL BACK)

- **ODIN v14** (51 features, C=0.10 deployed / C=0.01 honest, HO AUC 0.9363 inflated / 0.8995 honest)
- **Gungnir v46** (126 features, meta 90/10 Ridge/XGB, C=0.02, 500 trees, WF AUC 0.8135 inflated / Test 0.7841 honest)
- **BIFROST v4.0** runup timing/sizing (Sharpe 5.45, Kelly sizing, triple-ensemble magnitude)
- **BIFROST Explosion v5.5** (65 features, LR AUC 0.9487 inflated / 0.8861 v5.6 honest bar)

Deployed scores are ordinally valid, absolutely optimistic. Rank, don't calibrate.

---

## Active Q2 2026 portfolio (context for any trade-side questions)

- **GRCE** — PDUFA Apr 23, nano $47.9M, LOTTO options pick ($5 May-15, ≤1% sizing)
- **WHWK** — AACR Apr 17-22, Phase 1/2 oncology, equity only (spread 192% untradeable)
- **CRDF** — AACR Apr 17-22, Phase 2, HINT 0.6733 NEUT+ corroborative
- **CABA** — AAN Apr 20 oral RESET-MG + H1 RESET-SLE/SSc + EULAR Jun 3-6, Phase 2 neuro, equity
- **ALXO** — ESMO Breast May 7, Phase 2 breast onc, equity (OI 30 untradeable)

---

## Locked trading rules (as of April 2026)

- **BIFROST Options v1.3:** SKIP ODIN tier (edge inverts 21 pp). Don't buy cheap IV (Q1 is worst). OI sweet spot 100-499. Two live edges: CORE (Phase 1/2 positive readout, ATM T-14→T-1) and LOTTO (micro/nano PDUFA + OI≥50 + spread≤30, size ≤1%).
- **PDUFA equity:** NEW conditional rule — hold approvals through post_1d when ODIN ≥ T2 (no sell-the-news). T-60→T-7 preferred window (+3 pp significant AP-CR divergence); T-25 only for Large × T4 (+6.42 pp, 98.1% sig).
- **T-60 Runup Gap Predictor v2.0:** gating filter for T-60 entries. Require Q3+ AND ODIN ≥ T2 AND ch_scorable=1. Q4 full, Q3 half, Q1/Q2 skip.
- **CRL Q4 danger zone:** cut position if event runs +5-12% into T-1 AND ODIN flags CRL risk (71.6% crash rate).
- **Cap stack:** total multiplicative boost ≤ +25%. Never stack ODIN tier with BIFROST Options.

---

## Expected timing

- Stage 4 completion: ~140 min of actual runtime after relaunch (ETA will shift based on future deaths/restarts)
- Stages 5 + 6a + 6b + 6c: ~10-20 min total once Stage 4 done
- Stage 7 memo: ~30 min

---

## Style notes for new chat

- User preference: "Ask clarifying questions so you know exactly what to do." — BUT an explicit "relentless" directive is active for this workstream, so don't ask before executing Stages 5/6/7 once Stage 4 completes.
- Keep responses short. No preamble. Natural prose over bullets when possible.
- Current date: 2026-04-21.

---

END OF MIGRATION FILE
