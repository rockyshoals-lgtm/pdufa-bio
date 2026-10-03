# -*- coding: utf-8 -*-
"""Prove the 10-03 rendered-output guards 0 -> planted 1 -> 0. Restores every planted file."""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PY = sys.executable


def run(t):
    r = subprocess.run([PY, "-X", "utf8", os.path.join("tests", t)], cwd=HERE, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[0][:150]


def prove(test, path, mutate):
    before = run(test)
    orig = io.open(path, encoding="utf-8", newline="").read()
    try:
        io.open(path, "w", encoding="utf-8", newline="").write(mutate(orig))
        planted = run(test)
    finally:
        io.open(path, "w", encoding="utf-8", newline="").write(orig)
    after = run(test)
    print(f"{test}: before rc={before[0]} | planted rc={planted[0]} ({planted[1]}) | after rc={after[0]}")


def held_bad(t):
    j = json.loads(t)
    j["held_leads"] = [{"row_id": "x", "source": "y", "first_seen": "z"}]
    j["held_since"] = None
    return json.dumps(j, indent=1)


prove("test_quarantine_not_blockade.py", os.path.join(SITE, "build-info.json"), held_bad)
prove("test_quarantine_not_blockade.py", os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"),
      lambda t: t.replace("          exit 0\n\n      - name: \"Quarantine: record", "          exit $rc\n\n      - name: \"Quarantine: record", 1))
prove("test_data_built_at.py", os.path.join(SITE, "index.html"), lambda t: t.replace("data-fresh-built", "data-fresh-x"))
prove("test_data_built_at.py", os.path.join(SITE, "api", "_build-info.json"),
      lambda t: json.dumps({k: v for k, v in json.loads(t).items() if k != "data_built_at"}, indent=1))
