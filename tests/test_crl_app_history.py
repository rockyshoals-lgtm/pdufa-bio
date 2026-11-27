# -*- coding: utf-8 -*-
"""CI guard: each decision page lists the other FDA actions on its own application number.

2026-11-25 (David: "mine for more ... past CRLs ... red team everything, check for currency"). A CRL decision page
and the later approval of the same application did not know about each other (Saphnelo for subcutaneous use, BLA
761451: CRL October 10, 2025, approval April 24, 2026). link_crl_app_history.py writes an <!--APPHIST--> block on
every /fda-decision page whose own FDA record names an application that has a released CRL and another action,
or whose own action is a released CRL with a /crl/letter text page (2026-11-27).
This fails if:
  * the workflow does not run link_crl_app_history.py
  * a page that should carry the block does not, or a page carries one it should not
  * a block lists an application number other than the page's own record's
  * a block leaves out a released CRL or a 2025+ Drugs@FDA approval on that application, or lists a date the files
    do not hold
  * a /crl/letter or /fda-decision link in a block points at a page that does not exist

    python tests/test_crl_app_history.py      (PLANT=1 drops one block; the guard must fail)
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
WORKFLOW = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")


def main():
    import link_crl_app_history as h
    fails = []
    wf = io.open(WORKFLOW, encoding="utf-8").read() if os.path.exists(WORKFLOW) else ""
    if "python link_crl_app_history.py" not in wf:
        fails.append("the workflow does not run link_crl_app_history.py, so the blocks go stale")

    L, A, P = h.letters(), h.approvals(), h.pages()
    if os.environ.get("PLANT") == "1":
        for slug, pg in P.items():
            if h.B in pg["doc"]:
                pg["doc"] = re.sub(re.escape(h.B) + r".*?" + re.escape(h.E), "", pg["doc"], flags=re.S)
                break
    crl_by = {}
    for c in L:
        crl_by.setdefault(c["num"], []).append(c)
    appr_by = {}
    for a in A:
        appr_by.setdefault(a["num"], []).append(a)

    n = 0
    for slug, pg in sorted(P.items()):
        doc, num, rec = pg["doc"], pg["num"], pg["rec"]
        m = re.search(re.escape(h.B) + r"(.*?)" + re.escape(h.E), doc, re.S)
        crls = crl_by.get(num, []) if num else []
        apprs = appr_by.get(num, []) if crls else []
        others = [c for c in crls if c["pdf"] != rec] + [a for a in apprs if a["letter"] != rec]
        want = bool(crls and (others or h.own_text(crls, rec)))
        if want and not m:
            fails.append(f"/fda-decision/{slug}: application {num} has a released CRL and another FDA action (or its own CRL has a text page), "
                         f"but the page does not list them")
            continue
        if m and not want:
            fails.append(f"/fda-decision/{slug}: lists FDA actions on application {num}, which has no released CRL "
                         f"and another action, nor a CRL of its own with a text page")
            continue
        if not m:
            continue
        n += 1
        blk = m.group(1)
        got = re.search(r'data-apphist="(\d{6})"', blk)
        if not got or got.group(1) != num:
            fails.append(f"/fda-decision/{slug}: block names application {got and got.group(1)}, "
                         f"the page's own record names {num}")
        for c in crls:
            if c["pdf"] not in blk:
                fails.append(f"/fda-decision/{slug}: block leaves out the {h.pretty(c['date'])} letter on {num}")
            if h.pretty(c["action"]) not in blk:
                fails.append(f"/fda-decision/{slug}: block does not show the {h.pretty(c['action'])} CRL date")
        for a in apprs:
            if h.pretty(a["date"]) not in blk:
                fails.append(f"/fda-decision/{slug}: block leaves out the {h.pretty(a['date'])} approval on {num}")
        for d in re.findall(r"<b>([A-Z][a-z]+ \d{1,2}, \d{4})</b>", blk):
            known = {h.pretty(c["action"]) for c in crls} | {h.pretty(a["date"]) for a in apprs}
            if d not in known:
                fails.append(f"/fda-decision/{slug}: block lists {d}, which no released letter or approval on {num} "
                             f"holds")
        for sl in re.findall(r'href="/crl/letter/([^"]+)"', blk):
            if not os.path.exists(os.path.join(SITE, "crl", "letter", sl, "index.html")):
                fails.append(f"/fda-decision/{slug}: links /crl/letter/{sl}, which does not exist")
        for sl in re.findall(r'href="/fda-decision/([^"]+)"', blk):
            if not os.path.exists(os.path.join(SITE, "fda-decision", sl, "index.html")):
                fails.append(f"/fda-decision/{slug}: links /fda-decision/{sl}, which does not exist")
        if blk.count("<b>this page</b>") > 1:
            fails.append(f"/fda-decision/{slug}: more than one row marked as this page")

    if fails:
        print(f"FAIL test_crl_app_history: {len(fails)} problem(s); fix: python link_crl_app_history.py")
        for f in fails[:30]:
            print("   " + f)
        return 1
    print(f"  PASS application history: {n} decision page(s) list every released CRL and 2025+ approval on their "
          f"own application")
    return 0


if __name__ == "__main__":
    sys.exit(main())
