# -*- coding: utf-8 -*-
import json, os, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
h = {"User-Agent": "pdufa-builder", "Accept": "application/vnd.github+json"}
if tok:
    h["Authorization"] = "Bearer " + tok
u = "https://api.github.com/repos/rockyshoals-lgtm/pdufa-bio/actions/workflows/320578931/runs?per_page=8"
try:
    j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40).read())
    for r in j.get("workflow_runs", []):
        print(f"  {r['created_at']}  {str(r['status']):<12} {str(r['conclusion']):<10} {r['head_sha'][:9]}  {r['html_url']}")
except Exception as e:
    print("  GitHub API unavailable:", e)
    print("  (token env:", "present" if tok else "ABSENT", ")")
