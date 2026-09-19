# -*- coding: utf-8 -*-
"""Pull the failed step and its log tail from the latest CI run."""
import io, json, os, re, sys, urllib.request, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
H = {"User-Agent": "pdufa-builder", "Accept": "application/vnd.github+json"}
if tok:
    H["Authorization"] = "Bearer " + tok
run_id = sys.argv[1] if len(sys.argv) > 1 else "35451925692"
base = f"https://api.github.com/repos/rockyshoals-lgtm/pdufa-bio/actions/runs/{run_id}"
jobs = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/jobs", headers=H), timeout=60).read())
for j in jobs["jobs"]:
    print("job:", j["name"], j["conclusion"])
    for s in j["steps"]:
        if s["conclusion"] not in ("success", "skipped", None):
            print("   FAILED STEP:", s["number"], s["name"], s["conclusion"])
    jid = j["id"]
    try:
        data = urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/rockyshoals-lgtm/pdufa-bio/actions/jobs/{jid}/logs", headers=H), timeout=120).read()
        text = data.decode("utf-8", "replace")
    except Exception as e:
        print("   log fetch:", e); continue
    lines = text.splitlines()
    # find the failing step block: print lines around 'FAIL' / 'DO NOT PUBLISH' / 'error' / 'rejected'
    keys = re.compile(r"DO NOT PUBLISH|FAIL|##\[error\]|rejected|non-fast-forward|Traceback|exit code", re.I)
    hits = [i for i, l in enumerate(lines) if keys.search(l)]
    print("   log lines:", len(lines), "| key hits:", len(hits))
    shown = set()
    for i in hits[:40]:
        for k in range(max(0, i - 2), min(len(lines), i + 3)):
            if k not in shown:
                shown.add(k)
                print("   ", re.sub(r"^\S+T\S+Z ", "", lines[k])[:220])
