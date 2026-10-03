# -*- coding: utf-8 -*-
"""CI guard: a watcher lead holds its own row, never the whole site (audit 2026-10-03, Tier 1.1).

17 consecutive runs (2026-09-27 23:32 UTC to 10-03) deployed nothing because four watcher steps
exited 1 on a lead. Fails when:
  1. any watcher step in the workflow can still fail the job on a lead (a bare `python watch_*.py`
     step, or a watcher step ending `exit $rc`), or the quarantine collect/apply steps are missing,
     or apply does not run before the CI guards;
  2. the RENDERED /build-info.json (pdufa_site_src/build-info.json and api/_build-info.json) lacks
     held_since / held_leads, or they disagree (held rows listed with held_since null, or the reverse);
  3. restore_rows touches any row other than the held one (replayed on the real dataset).

    python tests/test_quarantine_not_blockade.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import quarantine_leads as Q  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
WF = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")


def steps(text):
    parts = re.split(r"\n      - name: ", text)
    return [("- name: " + p.split("\n", 1)[0], p) for p in parts[1:]]


def main():
    fails = []
    wf = io.open(WF, encoding="utf-8").read()
    st = steps(wf)
    names = [n for n, _ in st]
    for n, body in st:
        if re.search(r"\bwatch_(fda_approvals|drug_approvals|fda_drugs_feed|sponsor_newswire|edgar_8k)\.py", body):
            if "WATCH_LEADS_JSONL" not in body:
                fails.append(f"workflow step '{n}' runs a watcher without WATCH_LEADS_JSONL (a lead would fail the job)")
            if re.search(r"exit \$rc", body):
                fails.append(f"workflow step '{n}' still ends `exit $rc` on a lead (blockade)")
    if not any(re.search(r"\bwatch_fda_approvals\.py", b) for _, b in st):
        fails.append("no workflow step runs the watchers at all")
    ci = next((i for i, n in enumerate(names) if n.startswith("- name: CI guards")), None)
    col = next((i for i, (n, b) in enumerate(st) if "quarantine_leads.py collect" in b), None)
    app = next((i for i, (n, b) in enumerate(st) if "quarantine_leads.py apply" in b), None)
    if col is None or app is None:
        fails.append("workflow lacks the quarantine collect/apply steps")
    elif ci is None or app > ci:
        fails.append("quarantine apply must run before the CI guards step")

    for rel in ("build-info.json", os.path.join("api", "_build-info.json")):
        p = os.path.join(SITE, rel)
        bi = json.load(io.open(p, encoding="utf-8"))
        if "held_since" not in bi or "held_leads" not in bi:
            fails.append(f"/{rel} has no held_since / held_leads (run quarantine_leads.py apply)")
            continue
        if bool(bi["held_leads"]) != bool(bi["held_since"]):
            fails.append(f"/{rel}: held_since={bi['held_since']!r} but held_leads has {len(bi['held_leads'])} row(s)")

    src = io.open(Q.DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    a, b = rows[0]["id"], rows[1]["id"]
    work = json.loads(json.dumps(rows))
    work[0]["ua"], work[1]["ua"] = "changed-0", "changed-1"
    wtext = "export default " + json.dumps(work)
    new, n = Q.restore_rows(wtext, src, {a})
    out = {r["id"]: r for r in json.loads(new[new.index("["):new.rindex("]") + 1])}
    if n != 1 or out[a].get("ua") == "changed-0" or out[b].get("ua") != "changed-1":
        fails.append(f"restore_rows must restore exactly the held row {a} and leave {b} rebuilt (n={n})")

    if fails:
        print(f"FAIL: {len(fails)} quarantine failure(s):")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- watchers hold rows, not the site: no blocking watcher step, apply before guards, "
          "build-info carries held_since/held_leads, restore touches only the held row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
