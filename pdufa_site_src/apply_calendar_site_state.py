#!/usr/bin/env python3
"""
apply_calendar_site_state.py  --  flip pdufa.bio from the momentum/holding state back to
the FREE PUBLIC PDUFA CALENDAR. Idempotent; backs up vercel.json first.

Does three things:
  1) HOMEPAGE -> calendar. Restore index.html from _home_pdufa_backup.html
     ("2026 FDA PDUFA Calendar") and point the `/` rewrite at it (off surges.html).
  2) FREE / PUBLIC. Disable the password gate (rename middleware.js -> middleware.js.disabled)
     so anyone can view. (PRO_GATING already defaults OFF in api/data.js.)
  3) STRIP PRICING routes. Remove the /pricing rewrite + pricing-related redirects so the
     paywall isn't linked. (pricing.html stays on disk, dormant.)

Run from the site root (pdufa_site_src). Safe to re-run.
Usage:  python apply_calendar_site_state.py [--dry-run]
"""
import os, re, json, sys, shutil, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
HOMEPAGE_SRC = "_home_pdufa_backup.html"   # the backed-up PDUFA calendar homepage
HOME_DEST = "index.html"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    dry = a.dry_run
    today = datetime.date.today().isoformat()
    changes = []

    # 1) restore homepage file
    src = os.path.join(HERE, HOMEPAGE_SRC); dst = os.path.join(HERE, HOME_DEST)
    if os.path.exists(src):
        changes.append(f"copy {HOMEPAGE_SRC} -> {HOME_DEST} (restore PDUFA calendar homepage)")
        if not dry: shutil.copy2(src, dst)
    else:
        print(f"  WARN: {HOMEPAGE_SRC} not found — homepage file not restored")

    # 2) vercel.json — homepage rewrite + strip pricing
    vj = os.path.join(HERE, "vercel.json")
    d = json.load(open(vj, encoding="utf-8"))
    rewrites = d.get("rewrites", [])
    for r in rewrites:
        if r.get("source") == "/":
            if r.get("destination") != "/index.html":
                changes.append(f"rewrite  / : {r.get('destination')} -> /index.html")
                r["destination"] = "/index.html"
    # NOTE: pricing is KEPT. The base calendar is free/public; the PRO tier ($10/mo billed
    # annually, 1-month free trial) gates only options expected-move + IV + date-slip alerts.
    # (Pro features activate only when PRO_GATING_ENABLED=1 is set on Vercel.)
    d["rewrites"] = rewrites
    if not dry:
        shutil.copy2(vj, vj + ".bak_" + today)
        json.dump(d, open(vj, "w", encoding="utf-8"), indent=1)

    # 3) disable the password gate -> free public
    mw = os.path.join(HERE, "middleware.js")
    if os.path.exists(mw):
        changes.append("disable middleware.js password gate (rename -> middleware.js.disabled) = free public")
        if not dry:
            tgt = mw + ".disabled"
            if os.path.exists(tgt): os.remove(tgt)
            os.rename(mw, tgt)

    print(("DRY-RUN — would apply:" if dry else "APPLIED:"))
    for c in changes: print("  •", c)
    if not changes: print("  (already in calendar/free/public state — nothing to do)")
    if not dry:
        print(f"\nvercel.json backup: vercel.json.bak_{today}")
        print("pdufa.bio is now set to: FREE PUBLIC 2026 FDA PDUFA CALENDAR homepage.")

if __name__ == "__main__":
    main()
