#!/usr/bin/env python3
"""Orchestrator: wait for Phase 1 to finish, then run Phase 2 (intraday) and Phase 3 (analysis).
Launch this in the background; it babysits the pipeline to completion. Unattended."""
import time, json, subprocess, sys, os

PROG = "_phase1_progress.json"

def phase1_done():
    try:
        p = json.load(open(PROG))
        return bool(p.get("i") and p.get("total") and p["i"] >= p["total"])
    except Exception:
        return False

print("orchestrator: waiting for Phase 1 to complete...", flush=True)
waited = 0
while not phase1_done():
    time.sleep(15); waited += 15
    if waited % 300 == 0:
        print(f"  ...still waiting ({waited//60} min)", flush=True)

print("Phase 1 complete -> running Phase 2 (intraday volume)", flush=True)
subprocess.run([sys.executable, "surge_study_phase2.py"], check=False)
print("Phase 2 complete -> running Phase 3 (analysis + report)", flush=True)
subprocess.run([sys.executable, "surge_study_phase3.py"], check=False)
print("PIPELINE COMPLETE", flush=True)
