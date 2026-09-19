# -*- coding: utf-8 -*-
"""Would the new press-feed pass have caught Fayuvi? Re-arm RARE on a COPY of the dataset and
run the watcher against it, never touching the real file."""
import io, json, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DS = "pdufa_site_src/api/v1/dataset.mjs"
BAK = DS + ".provebak"
shutil.copy2(DS, BAK)
try:
    s = io.open(DS, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = s.index("["), s.rindex("]") + 1
    rows = json.loads(s[i:j])
    for r in rows:
        if r["id"] == "pdufa_rare_2026-09-19":
            r["st"] = "Upcoming"; r.pop("oc", None); r.pop("dcd", None)
    io.open(DS, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
    p = subprocess.run([sys.executable, "-X", "utf8", "watch_fda_approvals.py", "--dry-run"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = p.stdout
    print("\n".join(l for l in out.splitlines() if "RARE" in l or "WATCH" in l or "armed" in l))
    print("CAUGHT" if re.search(r"RARE .*press release", out) else "NOT CAUGHT")
finally:
    shutil.copy2(BAK, DS); os.remove(BAK)
