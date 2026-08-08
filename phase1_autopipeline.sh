#!/bin/bash
# Phase 1 auto-pipeline: waits for Form 4 stage 2 to complete, then runs
# 1.4 (features builder) -> 1.5 (ODIN honest eval) -> 1.6 (Gungnir honest eval).

set -u
cd /sessions/confident-serene-ptolemy/mnt/9realms
LOG=/sessions/confident-serene-ptolemy/mnt/9realms/phase1_autopipeline.log
: > "$LOG"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "phase1_autopipeline started"

# --- Step 1: wait for stage 2 complete ---
log "waiting for 'Stage 2 COMPLETE' in form4_stage2.log..."
while true; do
  if grep -q "Stage 2 COMPLETE" form4_stage2.log 2>/dev/null; then
    log "stage 2 complete detected"
    break
  fi
  # also abort if the process died and no completion
  if ! pgrep -f form4_stage2_concurrent.py >/dev/null; then
    if ! grep -q "Stage 2 COMPLETE" form4_stage2.log 2>/dev/null; then
      log "stage 2 process died before completion — abort"
      exit 2
    fi
  fi
  sleep 15
done

# --- Step 2: features builder ---
log "=== Phase 1.4: form4_features_builder.py ==="
python3 form4_features_builder.py >> "$LOG" 2>&1
RC=$?
log "features builder exit=$RC"
if [ $RC -ne 0 ]; then log "FEATURES BUILDER FAILED — abort"; exit 3; fi
if [ ! -f form4_event_features.csv ]; then log "MISSING form4_event_features.csv — abort"; exit 4; fi

# --- Step 3: ODIN honest eval ---
log "=== Phase 1.5: form4_odin_honest_eval.py ==="
python3 form4_odin_honest_eval.py >> "$LOG" 2>&1
RC=$?
log "ODIN eval exit=$RC"
if [ $RC -ne 0 ]; then log "ODIN EVAL FAILED — continue to Gungnir anyway"; fi

# --- Step 4: Gungnir honest eval ---
log "=== Phase 1.6: form4_gungnir_honest_eval.py ==="
python3 form4_gungnir_honest_eval.py >> "$LOG" 2>&1
RC=$?
log "Gungnir eval exit=$RC"
if [ $RC -ne 0 ]; then log "GUNGNIR EVAL FAILED"; fi

log "phase1_autopipeline DONE"
ls -la form4_event_features.csv form4_odin_honest_results.json form4_gungnir_honest_results.json 2>&1 | tee -a "$LOG"
