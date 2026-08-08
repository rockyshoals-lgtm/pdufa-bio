# ODIN v37.6 — Calibration Upgrades Patch (Drop-in Spec)
Generated: 2026-01-03 (America/Los_Angeles)

This file is **copy/paste-ready** and designed to be dropped into the ODIN repo as:
`docs/ODIN_v37_6_calibration_upgrades_patch.md`

It implements **Brier-lowering upgrades** without violating ODIN’s core rules:
- **Pre-event only (no leakage)**
- **Append-only immutable logging**
- **Core logic stays deterministic; learning only via calibration overlays**
- **Always prefer the most recent forecast (version precedence ladder)**

---

## 0) Why this patch exists
ODIN’s Brier is dominated by two failure modes:

1) **Overconfidence when evidence is incomplete**  
2) **Mixing heterogeneous event types into one probability stream**

This patch fixes both by:
- splitting ODIN into **separate probability heads** per event type (PDUFA / AdCom / Phase Readout / M&A)
- applying **segment-specific calibration** (isotonic/beta)
- adding **data-completeness shrinkage** (probabilities shrink toward 0.50 if we’re missing key inputs)
- enforcing **Europa Shield uncertainty caps** unless CMC is explicitly GREEN
- adding **year + review-type priors** with shrinkage
- recording calibrations as versioned artifacts (append-only)

---

## 1) Mandatory architecture change: “Multi-Head ODIN”
### 1.1 Heads (separate probability streams)
Implement these four heads:

- **HEAD_PDUFA**: Approval vs CRL (binary)
- **HEAD_ADCOM**: Vote direction AND post-vote approval mapping (binary outcome = approval/non-approval)
- **HEAD_PHASE**: Phase 2/3 topline success (binary = success/fail)
- **HEAD_MA**: M&A event probability in a defined window (binary = deal announced / not announced)

### 1.2 Never mix heads in calibration
Compute and report:
- Brier per head
- Accuracy per head
- Overall “portfolio Brier” = weighted average by head importance (weights explicit)

Suggested default weights:
- PDUFA 0.50
- Phase readouts 0.30
- AdCom 0.15
- M&A 0.05

---

## 2) Data schema upgrades (pre-decision only)
### 2.1 Structured fields (must be logged per head)
Each event must store these fields at **prediction time**:

Common:
- `event_id`
- `ticker`, `company`, `asset`, `indication`
- `event_type` (PDUFA/ADCOM/PHASE2/PHASE3/MA)
- `catalyst_date`
- `forecast_timestamp_utc`
- `asof_cutoff_utc` (snapshot cutoff; everything used must be <= this)
- `sources[]` (URLs or doc refs)
- `data_completeness` (0–1)
- `feature_vector` (f ∈ R^D; fixed dimensionality per head)

PDUFA-specific:
- `review_type` (STANDARD/PRIORITY)
- `designations` (BTD/FT/Orphan/RMAT/AA)
- `prior_crl` (0/1)
- `prior_crl_type` (CMC/EFFICACY/SAFETY/UNKNOWN)
- `resub_class` (CLASS_1/CLASS_2/NONE/UNKNOWN)
- **Europa Shield flags** (see §3)

AdCom-specific:
- `adcom_yes_pct` (0–100) OR UNKNOWN
- `adcom_topic_risk` (safety/efficacy/cmc)
- `adcom_scheduled_date`

Phase readout:
- `trial_phase` (2/3)
- `endpoint_type` (hard/surrogate/subjective)
- `prior_signal_strength` (0–1)
- `trial_design_quality` (0–1)

M&A:
- `strategic_fit_score` (0–1)
- `deal_rumor_evidence` (0–1)
- `poison_pill_removed` (0/1)
- `banker_hired` (0/1)

---

## 3) Europa Shield uncertainty caps (CMC hard gate)
### 3.1 The key concept
Brier explodes when ODIN outputs 0.85+ for PDUFAs where **CMC is actually unknown**.

Fix:
- define `europa_status` ∈ {GREEN, YELLOW, RED, UNKNOWN}
- apply **caps** unless GREEN

### 3.2 Status rules (pre-decision only)
- **GREEN**: Public evidence of clean inspection / low-risk manufacturing (e.g., NAI; no recent WL; identified DS/DP sites)
- **YELLOW**: No red flag but incomplete site mapping OR inspection status unknown
- **RED**: Public red flags (WL/OAI/serious 483 trends/known unresolved issues)
- **UNKNOWN**: not enough data to classify

### 3.3 Caps (immutable calibration overlay rule)
In HEAD_PDUFA, after base score:

- if europa_status == UNKNOWN: `poa = min(poa, 0.78)`
- if europa_status == YELLOW: `poa = min(poa, 0.72)`
- if europa_status == RED: `poa = min(poa, 0.55)`

Rationale:
- Caps prevent overconfidence when the biggest failure mode is hidden CMC.

---

## 4) Data completeness shrinkage (the fastest Brier reducer)
### 4.1 Compute data_completeness
Define completeness as a weighted coverage of required fields per head.

Example for PDUFA (weights sum to 1):
- clinical evidence present: 0.25
- safety summary present: 0.15
- regulatory designations present: 0.10
- CMC mapping present: 0.25
- FDA tone/communications present: 0.15
- commercial hiring signal present: 0.10

### 4.2 Apply shrinkage in logit space
Let `p_raw` be the deterministic head probability before calibration.

Convert to logits:
- `logit = ln(p/(1-p))`

Shrink:
- `logit_adj = logit * (0.35 + 0.65 * data_completeness)`

Then:
- `p_shrunk = sigmoid(logit_adj)`

Interpretation:
- If completeness is low, probabilities move toward 0.50.
- If completeness is high, ODIN can still express strong conviction.

---

## 5) Priors: year-aware + review-type aware (with shrinkage)
### 5.1 Priors must be separate by head
For PDUFA head, build priors by:
- year (2015…2026)
- review type (PRIORITY vs STANDARD)
- modality bucket (SMALL_MOL / BIOLOGIC / CGT)
- therapeutic area bucket (ONC / RARE / CNS / OTHER)

### 5.2 Shrinkage to avoid overfitting small slices
Let:
- `p_slice = approvals_slice / total_slice`
- `p_global = approvals_global / total_global`
- `k = 50` (shrinkage strength)

Then:
- `p_prior = (approvals_slice + k*p_global) / (total_slice + k)`

This preserves drift (year effects) without letting low-N slices go insane.

---

## 6) Calibration: per head, per segment
### 6.1 Calibrator selection
- If resolved N >= 200 in segment: **isotonic regression**
- If 50 <= N < 200: **beta calibration** (logit linear)
- If N < 50: **no re-fit**; use the prior blend only

### 6.2 Strict gates
No calibration update unless:
- N_resolved >= MIN_N (default 50 per segment per head)
- and predictions were logged pre-outcome (timestamp gate)

### 6.3 Output contract
Every prediction must store:
- `poa_raw`
- `poa_shrunk`
- `poa_calibrated`
- `calibration_id` (or NONE)
- `segment_id` used
- `europa_status` + cap applied (if any)

---

## 7) AdCom mapping: piecewise monotone baseline (then calibrate)
Instead of linear treatment of AdCom vote %, use a monotone mapping:

Let `y = yes_pct` (0–100). Define baseline `p_vote_to_approval`:

- y >= 70: 0.97
- 50 <= y < 70: 0.90
- 40 <= y < 50: 0.55
- y < 40: 0.20

Then apply:
- completeness shrinkage
- segment calibrator

This preserves the known asymmetry: positive votes are highly predictive; negative votes are not deterministic.

---

## 8) Forecast precedence ladder (already adopted)
ODIN must always select canonical forecasts for scoring as:
1) Most recent eligible forecast timestamp (<= outcome date/time)
2) Tiebreak by model precedence (newest model wins)

Precedence order:
v37.6 → v37 → v36 → v35 → v34 → v33 → v32 → v28 → v26 → v14 → v6 → UNKNOWN

This prevents “old logic” from polluting scorecards.

---

## 9) What changes in code (implementation checklist)
### 9.1 Create calibrator modules
Add:
- `calibration/isotonic.py`
- `calibration/beta_calibration.py`
- `calibration/priors.py`
- `calibration/segments.py`
- `calibration/completeness.py`

### 9.2 Add head router
Add:
- `engine/head_router.py` that chooses head + segment_id

### 9.3 Add immutable calibration registry
Append-only JSONL:
- `ledgers/calibration_registry.jsonl`
Each entry:
- `calibration_id`
- `head`
- `segment_id`
- `trained_on_window`
- `n`
- calibrator parameters
- `created_utc`
- `code_hash`

### 9.4 Add metrics reporting
Write:
- Brier/accuracy per head
- coverage exclusions
- calibration reliability buckets (ECE)
- and store outputs to `reports/`

---

## 10) Minimal pseudocode (drop-in)
```python
def odin_predict(event):
    head = route_head(event)
    segment_id = compute_segment_id(event, head)
    completeness = compute_completeness(event, head)
    p_raw = head_deterministic_score(event)              # immutable core / v37 hybrid logic
    p_raw = apply_europa_caps(p_raw, event)              # §3
    p_shrunk = shrink_logit(p_raw, completeness)         # §4
    p_prior = get_shrunk_prior(head, segment_id, event)  # §5
    p_blend = blend(p_prior, p_shrunk, w=0.35)           # configurable per head
    p_cal = apply_calibrator(head, segment_id, p_blend)  # §6
    log_forecast(event, head, segment_id, p_raw, p_shrunk, p_cal, completeness)
    return p_cal
```

---

## 11) Acceptance tests (so we know Brier actually drops)
Run these after implementation:

1) **No-leakage audit**: verify `asof_cutoff_utc` <= all source timestamps
2) **Coverage report**: how many events excluded due to missing pre-decision data
3) **Holdout**: last 20% of timeline (time-split) is never used to fit calibrators
4) **Compare Brier**:
   - v37.6 baseline vs v37.6 + this patch
   - report delta per head

Success criterion:
- **Brier improves** in HEAD_PDUFA and HEAD_ADCOM without degrading calibration error (ECE).

---

## 12) What to store in the repo
- This patch file (docs/)
- Calibrator registry JSONL (append-only)
- Generated metrics reports
- A fixed `SEGMENT_SCHEMA_VERSION` string in code so calibrations are reproducible

---

### END
If you want the next artifact: I can generate the **exact Python modules + file tree** aligned to your current ODIN layout (odina.py / v37 master JSON), but this markdown patch is the canonical spec you can commit today.
