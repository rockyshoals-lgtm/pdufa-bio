# 9 REALMS MIGRATION FILE — 2026-03-26
## For continuation in a new Cowork/Claude session

---

## 1. MCP SERVER STATUS & CONFIGURATION

### Server File
- **Path (Windows):** `C:\Users\dcmoo\Documents\Python\9realms\mcp_9realms_vnext.py`
- **Version:** v5.2.0
- **Engines embedded:** ODIN vNEXT v5 (25-feature Ridge) + GUNGNIR v27 (33-feature Ridge)
- **Tools:** `odin_score`, `gungnir_score`, `odin_rank`, `gungnir_rank`, `system_status`
- **Self-test:** ✅ PASSES as of 2026-03-26

### How to Run Self-Test
```cmd
"C:\Users\dcmoo\AppData\Local\Programs\Python\Python311\python.exe" "C:\Users\dcmoo\Documents\Python\9realms\mcp_9realms_vnext.py" --test
```

### How to Start MCP Server (for Cowork connector)
```cmd
"C:\Users\dcmoo\AppData\Local\Programs\Python\Python311\python.exe" "C:\Users\dcmoo\Documents\Python\9realms\mcp_9realms_vnext.py" --serve
```

### Cowork Connector Configuration (STILL NEEDS FIXING)
The connector exists but tools return "disabled" — the connector path was wrong. Update to:
- **Command:** `C:\Users\dcmoo\AppData\Local\Programs\Python\Python311\python.exe`
- **Arguments:** `C:\Users\dcmoo\Documents\Python\9realms\mcp_9realms_vnext.py --serve`
- **Status:** User needs to find Cowork connector settings and update the path. All 5 tools show "disabled" until this is fixed.

### Python Environment
- **Python 3.11:** `C:\Users\dcmoo\AppData\Local\Programs\Python\Python311\python.exe` (NOT on PATH)
- **FastMCP:** Confirmed installed under Python 3.11
- **Other Pythons on system:** 3.14 (`C:\Python314`), 3.13 (`C:\Program Files\Python313`), WindowsApps Python
- **GPU:** NVIDIA RTX 4070 (for training, not needed for MCP server)

---

## 2. CURRENT MODEL STATE

### ODIN v5 (PDUFA Scoring) — CHAMPION IN MCP SERVER
- **Architecture:** 25-feature L2 Ridge Logistic Regression (C=1.5, lbfgs)
- **Training:** 2,203 historical PDUFA events (2015–2024), cutoff 2025-01-01
- **Performance:** HO AUC 0.9007, WF AUC 0.8720, Brier 0.1210, Accuracy 83.5%
- **Tier System:** T1 (≥0.85), T2 (0.65–0.85), T3 (0.40–0.65), T4 (<0.40)
- **25 Features:** prior_crl_bin, btd_bin, pr_bin, ppm_flag_bin, sponsor_naive, sponsor_experienced, is_resub, ta_very_high, log_spa, surrogate, had_adcom_flag, spa_sweet, spa_mega, multi_crl, crl_rate_low, desig_rich, spa_3_5, surrogate_x_pr, is_nda, btd_and_priority, sweet_x_btd, experienced_x_btd, desig_count, era_post, ta_vh_x_experienced

### ODIN v6.1 — TRAINED BUT NOT YET IN MCP SERVER
- **Architecture:** 32-feature Ridge (C=15)
- **Performance:** Brier 0.1102 (+8.9% improvement over v5)
- **Status:** Weights trained in previous AFK GPU session. Need to embed into mcp_9realms_vnext.py
- **Key improvement:** 7 additional features over v5

### GUNGNIR v27 — IN MCP SERVER
- **Architecture:** 33-feature L2 Ridge (C=10.0)
- **Performance:** HO AUC 0.7529, Brier 0.2206
- **Leakage status:** CLEAN (zero post-readout features)

### GUNGNIR v29.0.0 — CHAMPION (NOT IN MCP SERVER)
- **Architecture:** 6-strategy ensemble (L2 Ridge + ElasticNet + P3 Specialist + Bayesian Shrinkage + Journey+CTGOV Specialist + CTGOV Specialist)
- **Meta-learner:** 75% Journey+CTGOV, 25% P3, temperature scaling T=1.15
- **Training:** 3,472 binary phase readout events, temporal split at 2025-01-01
- **Performance:** AUC 0.6439, Brier 0.2339
- **82 Features:** 50 base + 19 journey + 13 CTGOV (10 real + 3 interactions)
- **Key files:**
  - `gungnir_v29_deploy.json` — deploy config
  - `gungnir_v29_ctgov_train.py` — training pipeline
  - `ctgov_cache.json` — 1,981 drug/phase CTGOV API cache

### GUNGNIR v30.1 — TRAINED BUT NOT IN MCP SERVER
- **Architecture:** 26-feature Ridge+Trees blend
- **Performance:** Brier 0.1008 (+56.9% improvement over v29)
- **Status:** Weights trained in previous AFK GPU session. Need to embed into MCP server.

### PRIORITY ACTION: Embed v6.1 (ODIN) and v30.1 (GUNGNIR) weights into mcp_9realms_vnext.py

---

## 3. TRACK RECORD & LEDGER STATUS

### Current Stats (as of 2026-03-26)
- **VERIFIED_OUTCOMES:** 63 entries (Apr 2025 → Mar 2026)
- **TIMESTAMPED_PREDICTIONS:** 15 TS + 4 CEWS = 21 entries
- **Win Rate All-Time:** 95.2% (60/63)
- **Win Rate 2026:** 95.2% (20/21, excluding 2 pending)
- **Misses All-Time:** 3 (FBIO Oct 2025, SNY/Tolebrutinib Dec 2025, PHAR Feb 2026)
- **Pending:** LNTH (delayed to Jun 29), RCKT/Kresladi (PDUFA Mar 28)

### Key Files Updated This Session
- `trackRecord.ts` — SHA-256: `3de07399abbdb6acda511c46113231a7db6436b3a0db221e6429cc82f2c9c215`
- `ODIN_v96_H1_2026_PREDICTIONS.csv` — SHA-256: `307c3e7f3fe2a1ab34209e5b097f6adeebe5adaeabff319e9527afd640171f15`, mtime: `2026-01-31T19:13:22Z`
- `odin_scoring_system.json` — 63 verified outcomes, 21 timestamped predictions

### Entries Added This Session
- SNY/Cablivi (Jan 5 approved), SNY/Cerezyme (Jan 12 approved), JNJ/Darzalex (Jan 27 approved)
- RCKT/RP-A501 Danon runup (Feb 20), REGN/Dupixent AFRS (Feb 24 approved), ETON/Desmoda (Feb 25 approved)
- LNTH delay (Mar 17 → Jun 29)
- Date corrections: GSK Mar 19→Mar 17, DNLI Mar 25→Mar 24 (per FDA.gov official dates)

### New SHA-256 Hashes Generated
| ID | Ticker | Hash |
|---|---|---|
| TS-011 | DNLI | `211969bf2f628483104fb408443ff168d2b4d811fd7c8e7de77dfc4b3d099d46` |
| TS-012 | BMRN | `ec300ce22cfe6ad4ba39dbbefeb6695b7f39b4ab1726c88e0cae60899db4b3fd` |
| TS-013 | ALDX | `c67c6d7746efbe66566b66e8e60bfda41a05c56dd1ecd0a9d3645e3e935f8801` |
| TS-014 | GSK | `beffc63a417bf74d0d277adb6d723fb7ce045b6d0731b3f0b95293db64acdbd3` |
| TS-015 | LNTH | `0640a33d90648088198b06625bd10677594e604474f78f571f61cf311e1143d2` |

---

## 4. KODIAK (KOD) WIN — NEEDS LOGGING

### What Happened (2026-03-26)
- **Drug:** Zenkuda (tarcocimab tedromer) — GLOW2 Phase 3
- **Indication:** Diabetic Retinopathy (DR)
- **Result:** BLOWOUT POSITIVE
  - Primary: 62.5% achieved ≥2-step DRSS improvement vs 3.3% sham (p<0.0001)
  - Secondary: 85% risk reduction in sight-threatening complications (p=0.0001)
  - Safety: 0% intraocular inflammation, no retinal vasculitis
  - Dosing: Only 5 injections over 48 weeks → 6-month dosing by end
  - GLP-1 robust: Efficacy maintained in concurrent GLP-1 users
- **Stock:** +19% surge
- **Regulatory:** Company accelerating BLA submission timeline

### Our Historical Data on KOD
- KOD has **mixed history** in our phase_events.json:
  - DAZZLE (wAMD Phase 2/3) — MISSED primary endpoint (2022)
  - GLEAM/GLIMMER (DME Phase 3) — MISSED primary endpoints (2023)
  - BEACON (RVO Phase 3) — MET primary endpoint, non-inferior to aflibercept (2022)
  - DAYLIGHT (wAMD Phase 3) — MET primary endpoint (2023)
  - GLOW2 interim (DR Phase 3) — MET superiority endpoint at AAO (2023)
- KOD was flagged in AIprompts.txt as a Q1 2026 catalyst to track
- Our catalyst scanner showed `NO_DATA` for KOD on Jan 29, 2026 — meaning we identified it but hadn't scored it yet

### Post-Mortem: What Went Right
1. **Drug journey signal:** Tarcocimab had a POSITIVE Phase 3 GLOW2 interim (2023) + positive BEACON + positive DAYLIGHT. Gungnir's drug journey features (positive streak ≥2) would have flagged this as high-confidence
2. **Superiority design vs sham:** Much easier bar than active-comparator studies (where KOD failed in DAZZLE/GLEAM)
3. **Second Phase 3 in same indication:** GLOW2 is the SECOND registrational DR trial — first one (GLOW1) already showed superiority in 2025

### Post-Mortem: What We Need to Improve
1. **GAP:** KOD wasn't in our prediction log despite being flagged as a catalyst. The catalyst scanner returned NO_DATA. We need to close the loop between "identified catalyst" and "scored prediction."
2. **Gungnir should have scored this:** tarcocimab had 3+ positive Phase 3s already (BEACON, DAYLIGHT, GLOW1), plus interim GLOW2 data was already positive. Gungnir's drug journey module would have given high confidence.
3. **BLA-path signal:** The company had already announced BLA acceleration plans — this is a forward-looking signal that Allfather should capture.

---

## 5. ALLFATHER SPECIFICATION (USER'S FULL SPEC)

The user created a comprehensive specification for a "Penultimate" orchestration engine called Allfather. Key points:

### Architecture
- Fuse best-of-breed components from ALL historical Odin (v1–v6) and Gungnir (v1–v30) iterations
- Combine into unified `Allfather_Odin` and `Allfather_Gungnir` models
- Include HINT architecture as secondary opinion (GNN + GRAM + BERT multi-modal graph)
- Use Indeed MCP for forward-looking job-momentum signals
- Use ClinicalTrials.gov MCP for real trial design features
- Use FinBrain MCP for real OHLCV/technicals/sentiment

### Constraints
- **REAL DATA ONLY** — no synthetic/simulated data, drop features that can't be populated
- **T-1 compliance** — all features from ≤ D-1, use existing backtest T-1 scripts
- **GPU acceleration** — RTX 4070, PyTorch/CuPy, dynamic RAM scaling with pynvml
- **10-minute monitoring loop** — check Brier, tweak hyperparams, add new signals
- **Leakage verification** — run gungnir_t1_compliant_vX.py after every training run

### Workflow
1. Lock ODIN v6.1 + GUNGNIR v30.1 as cornerstone
2. Scan all iterations, extract best features/architectures/calibrations
3. Build `Allfather.py` with everything fused
4. Run 10-minute tuning loop until Brier ceiling (or 4 hours)
5. Generate predictions for all upcoming PDUFA (180 days) + Phase readouts (12 months)
6. Cross-reference with pdufa.bio history
7. Post-mortem on any 2026 misses

### Deliverables
- `Allfather.py` — cornerstone orchestration script
- `Allfather_Odin_Penultimate.pt` + `Allfather_Gungnir_Penultimate.pt` — final weights
- `PENULTIMATE_prediction_log.csv` — forward predictions
- `2026_postmortem_*.md` — one per missed event
- `allfather_final_summary.json` — best scores + roadmap

### Key Paths on Windows
- Workspace: `C:\Users\dcmoo\Documents\Python\9realms\`
- Models: `C:\Users\dcmoo\Documents\Python\9realms\models\`
- Logs: `C:\Users\dcmoo\Documents\Python\9realms\logs\`
- Backtest: `C:\Users\dcmoo\Documents\Python\9realms\backtest\`
- Configs: `C:\Users\dcmoo\Documents\Python\9realms\configs\`

### NOTE FOR NEXT SESSION
The Allfather spec should be run on the user's Windows machine (RTX 4070 GPU). The Cowork VM can build the script but cannot do GPU training. Strategy: build Allfather.py in Cowork, user runs it locally.

---

## 6. KEY DATA FILES

### Prediction Sources
| File | Description | SHA-256 / Timestamp |
|---|---|---|
| `ODIN_v96_H1_2026_PREDICTIONS.csv` | 24 H1 2026 PDUFA predictions | Created 2026-01-31T19:13:22Z |
| `ODIN_2026_CSV_DATABASE.csv` | Earliest 2026 predictions | Created 2026-01-14T08:26:28Z |
| `odin_prediction_log.json` | Historical prediction log | Created 2025-12-27T20:45:05Z |
| `predictions.csv` | Full prediction database | Created 2026-01-31T00:10:43Z |

### Model Weights & Configs
| File | Description |
|---|---|
| `mcp_9realms_vnext.py` | MCP server with embedded v5/v27 weights |
| `gungnir_v29_deploy.json` | v29.0.0 CTGOV deploy config (CHAMPION) |
| `gungnir_v29_ctgov_train.py` | v29.0.0 training pipeline |
| `ctgov_cache.json` | 1,981 drug/phase CTGOV API cache |
| `enriched_gungnir_dataset.csv` | 2,022 phase readout events |
| `ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv` | 2,203-event ODIN training set |

### Track Record
| File | Description |
|---|---|
| `trackRecord.ts` | Mobile/pdufa.bio source — 63 outcomes + 21 timestamped predictions |
| `odin_scoring_system.json` | Master JSON — scoring algorithm + outcomes + predictions |
| `ODIN_VERIFIED_LEDGER_CONSOLIDATED_v4.json` | Hashed ledger chain (36 wins) |

---

## 7. CONNECTED MCPs AVAILABLE

The following MCPs are confirmed connected in Cowork and should be leveraged:
- **ClinicalTrials.gov** (`clinicaltrialsgov`) — study search, trend analysis, compare studies
- **FinBrain** (`finbrain`) — news sentiment, insider transactions, analyst ratings, options put/call, LinkedIn metrics, Senate/House trades
- **Perplexity** (`perplexity`) — ask, reason, research, search
- **Drug/Compound Search** (ChEMBL-style) — compound search, drug search, ADMET, bioactivity, mechanism, target
- **Clinical Trials Search** (alt) — trial details, endpoint analysis, sponsor search, investigator search
- **Google Calendar** — scheduling
- **Claude in Chrome** — browser automation
- **PDF Tools** — fill, extract, analyze PDFs

---

## 8. UPCOMING CATALYSTS TO WATCH

### PDUFA Events (from v96 predictions, next 90 days)
| Ticker | Drug | PDUFA | ODIN Score | Tier |
|---|---|---|---|---|
| RCKT | Kresladi (marnetegragene) | Mar 28 | 95.9% | T1 STRONG LONG |
| LNTH | LNTH-2501 (Ga-68 edotreotide) | Jun 29 (delayed from Mar 29) | 96.0% | T1 (PENDING) |
| DNLI | ✅ AVLAYAH approved Mar 24 | Done | 96.9% | T1 WIN |
| ORCA | Orca-T (allo-HSCT) | Apr 6 | 95.1% | T1 STRONG LONG |
| BMY | Opdivo (cHL frontline sBLA) | Apr 8 | 99.0% | T1 STRONG LONG |
| TVTX | Filspari (FSGS) | Apr 13 (delayed from Jan 13) | 78.7% | T5 AVOID |
| SNY | Sarclisa (1L myeloma) | Apr 23 | 99.0% | T1 STRONG LONG |
| ARGX | Vyvgart (seroneg gMG) | May 10 | 99.0% | T1 STRONG LONG |
| VRDN | Veligrotug (TED) | Jun 30 | 87.1% | T3 CAUTIOUS |

---

## 9. RULES (ALWAYS ENFORCE)
- ODIN v5 is the ONLY PDUFA scoring model (until v6.1 is embedded). Never fall back to v4.
- GUNGNIR v29.0.0 is the ONLY phase readout scoring model (until v30.1 is embedded). Never fall back to v28.x, v27, v26, or v25 (leaked).
- All investment content must include disclaimers (informational/educational, not investment advice).
- Current date context: March 2026.
- All prediction timestamps must use PREDICTION date, not outcome date.
- SHA-256 hashes use canonical JSON (sorted keys, no whitespace).
