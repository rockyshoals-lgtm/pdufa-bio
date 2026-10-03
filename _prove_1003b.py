# -*- coding: utf-8 -*-
"""Prove every guard added in the 10-03 Tier 2-4 pass: 0 -> planted 1 -> 0 on the rendered output. Restores all plants."""
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "pdufa_site_src")
PY = sys.executable


def run(t):
    r = subprocess.run([PY, "-X", "utf8", os.path.join("tests", t)], cwd=HERE, capture_output=True, text=True)
    return r.returncode, ((r.stdout + r.stderr).strip().splitlines() or [""])[0][:120]


def prove(test, path, mutate, label):
    before = run(test)
    orig = io.open(path, encoding="utf-8", newline="").read()
    new = mutate(orig)
    if new == orig:
        print(f"{test} [{label}]: PLANT DID NOT APPLY")
        return
    try:
        io.open(path, "w", encoding="utf-8", newline="").write(new)
        planted = run(test)
    finally:
        io.open(path, "w", encoding="utf-8", newline="").write(orig)
    after = run(test)
    ok = before[0] == 0 and planted[0] == 1 and after[0] == 0
    print(f"{'PROVED' if ok else 'NOT PROVED'} {test} [{label}]: {before[0]} -> {planted[0]} ({planted[1]}) -> {after[0]}")


P = lambda *a: os.path.join(S, *a)  # noqa: E731
prove("test_decision_lede_fact_first.py", P("fda-decision", "AZN-2026-09-04", "index.html"),
      lambda t: re.sub(r"<!--FACTLEDE:BEGIN-->.*?<!--FACTLEDE:END-->", "", t, flags=re.S), "lede removed")
prove("test_decision_lede_fact_first.py", P("fda-decision", "ABBV-2026-09-28", "index.html"),
      lambda t: t.replace("the 43rd novel drug approval", "the 42nd novel drug approval"), "wrong novel count")
prove("test_decision_lede_fact_first.py", P("fda-decision", "AXSM-2026-04-30", "index.html"),
      lambda t: t.replace("was approved by the FDA on April 30, 2026", "was approved by the FDA on April 29, 2026"), "date no FDA record holds")
prove("test_no_truncated_drug_names.py", P("fda-decision", "AMPH-2026-02-24", "index.html"),
      lambda t: re.sub(r"<title>Ipratropium Bromide HFA Inhalation Aerosol", "<title>Ipratropium Bromide HFA Inhala", t, count=1), "cut title")
prove("test_fda_days_by_action_date.py", P("fda-this-month", "index.html"),
      lambda t: t.replace('id="fda-2026-09-25"', 'id="fda-2026-09-28"'), "JUVMO under the announcement day")
prove("test_letters_hub_linked.py", P("fda-decision", "AAPG-2025-12-09", "index.html"),
      lambda t: re.sub(r"<!--LETTERSLINK:BEGIN-->.*?<!--LETTERSLINK:END-->", "", t, flags=re.S), "hub link removed")
prove("test_readout_ta_coverage.py", P("api", "v1", "dataset.mjs"),
      lambda t: re.sub(r'"ta": "(Dermatology|Respiratory|Gastroenterology|CNS|Infectious)"', '"ta": ""', t), "tags stripped")
prove("test_conference_ledes.py", P("conference", "EASD", "index.html"),
      lambda t: t.replace("took place September 28", "takes place September 28"), "wrong tense")
prove("test_13f_block.py", P("fda-decision", "RVMD-2026-08-26", "index.html"),
      lambda t: re.sub(r"reported 11,443,357 shares", "reported 11,443,358 shares", t, count=1), "share count off by one")
prove("test_adcomm_history.py", P("adcomm", "index.html"),
      lambda t: re.sub(r"2020 to 2026: (\d+) Federal", lambda m: f"2020 to 2026: {int(m.group(1)) + 1} Federal", t, count=1), "count mismatch")
prove("test_exclusivity_cliff.py", P("patent-cliff", "index.html"),
      lambda t: re.sub(r"<!--EXCL:BEGIN-->.*?<!--EXCL:END-->", "", t, flags=re.S), "hub link removed")
prove("test_crl_headings.py", P("crl", "index.html"),
      lambda t: t.replace("Product Quality Microbiology; Facility Inspections", "Product Quality Microbiology; Efficacy Failure", 1), "section not in the PDF")
prove("test_edgar_8k_replay.py", os.path.join(HERE, "watch_edgar_8k.py"),
      lambda t: t.replace("approval (of|for)|granted approval|", "approval of|"), "decision regex narrowed")
prove("test_request_time_status.py", P("api", "v1", "_lib.mjs"),
      lambda t: t.replace("if (os_ === 'TERMINATED') return 'Terminated per registry';", ""), "registry branch removed")
prove("test_event_page_fda_date_brand.py", P("pdufa", "ABBV-tavapadon", "index.html"),
      lambda t: t.replace("JUVMO (Tavapadon), Approved September 25, 2026", "Tavapadon, Approved September 28, 2026"), "announcement date + no brand")
prove("test_event_page_indication_match.py", P("pdufa", "RHHBY-gazyva", "index.html"),
      lambda t: t.replace("<!--FRESH:BEGIN-->", '<!--DECBAN:BEGIN--><div class="ban"><a href="/fda-decision/RHHBY-2026-09-25">Approved</a></div><!--DECBAN:END--><!--FRESH:BEGIN-->', 1), "INS approval on the lupus page")
