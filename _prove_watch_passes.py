# -*- coding: utf-8 -*-
"""Re-arm RARE and TLX on a COPY of the dataset and prove the press + EDGAR passes catch both."""
import io, json, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DS = "pdufa_site_src/api/v1/dataset.mjs"; BAK = DS + ".provebak"
shutil.copy2(DS, BAK)
try:
    s = io.open(DS, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = s.index("["), s.rindex("]") + 1
    rows = json.loads(s[i:j])
    for r in rows:
        if r["id"] in ("pdufa_rare_2026-09-19", "pdufa_tlx_2026-09-11"):
            r["st"] = "Upcoming"; r.pop("oc", None); r.pop("dcd", None)
            r["name"] = {"pdufa_rare_2026-09-19": "UX111 - (ABO-102)", "pdufa_tlx_2026-09-11": "TLX101-Px (Pixclara)"}[r["id"]]
    io.open(DS, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
    p = subprocess.run([sys.executable, "-X", "utf8", "watch_fda_approvals.py", "--dry-run"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for l in p.stdout.splitlines():
        if "RARE" in l or "TLX" in l or "WATCH" in l:
            print("  ", l[:230])
    print("RARE via press feed:", "CAUGHT" if re.search(r"RARE .*press release", p.stdout) else "not caught")
    print("TLX via EDGAR 6-K :", "CAUGHT" if re.search(r"TLX .*sponsor 6-K filed \d+-\d+-\d+ states", p.stdout) else "not caught")
finally:
    shutil.copy2(BAK, DS); os.remove(BAK)
