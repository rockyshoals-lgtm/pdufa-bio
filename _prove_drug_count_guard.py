# -*- coding: utf-8 -*-
"""Prove tests/test_drug_page_decision_count.py: 0 -> planted 1 -> healed 0, with the plant verified."""
import io, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY, GUARD = sys.executable, os.path.join("tests", "test_drug_page_decision_count.py")
P = "pdufa_site_src/drug/inluriyo/index.html"
BAK = P + ".prove"


def run():
    r = subprocess.run([PY, "-X", "utf8", GUARD], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip().splitlines()[:2]


def links(p):
    t = io.open(p, encoding="utf-8", errors="replace").read()
    return re.findall(r'href="(/fda-decision/[A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', t)


shutil.copy2(P, BAK)
ok = True
try:
    rc, out = run()
    print("baseline rc=%d  %s" % (rc, out[-1] if out else ""))
    print("  baseline links:", links(P))
    ok &= rc == 0

    # PLANT A: duplicate the decision link (a whole anchor)
    t = io.open(P, encoding="utf-8", errors="replace").read()
    m = re.search(r'<a class="row" href="/fda-decision/LLY-2026-09-18".*?</a>', t, re.S)
    assert m, "anchor not found -- cannot plant"
    t2 = t[:m.end()] + m.group(0) + t[m.end():]
    io.open(P, "w", encoding="utf-8").write(t2)
    print("  planted duplicate anchor; links now:", links(P))
    rc, out = run()
    print("planted-A rc=%d  want 1  %s" % (rc, (out[0] if out else "")[:120]))
    ok &= rc == 1
    shutil.copy2(BAK, P)

    # PLANT B: inflate the stated count only
    t = io.open(P, encoding="utf-8", errors="replace").read()
    t2, n = re.subn(r"(\d+) FDA decisions? (are |is )?on record",
                    lambda mm: "9 FDA decisions are on record", t)
    assert n, "count sentence not found"
    io.open(P, "w", encoding="utf-8").write(t2)
    rc, out = run()
    print("planted-B rc=%d  want 1  %s" % (rc, (out[0] if out else "")[:120]))
    ok &= rc == 1
    shutil.copy2(BAK, P)

    rc, out = run()
    print("healed rc=%d  %s" % (rc, out[-1] if out else ""))
    ok &= rc == 0
finally:
    shutil.copy2(BAK, P)
    os.remove(BAK)
print("PROOF", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
