# -*- coding: utf-8 -*-
"""test_no_conflict_markers.py -- git conflict markers never ship.

2026-08-12, owner-reported from the LIVE homepage: two copies of the 'Next FDA decisions' board,
one under '<<<<<<< Updated upstream', the other above '>>>>>>> Stashed changes'. A stash-apply
conflict in the working tree was faithfully committed by the whole-tree `git add` and deployed;
it survived a full day, multiple deploys, and 41 guards, because every guard checked semantics
and none checked for the one artifact git itself leaves behind.

Any line beginning with a conflict marker, in any file under pdufa_site_src, fails the build.
(`=======` is matched only between the other two markers -- a Markdown underline is not a
conflict.)
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MARK = re.compile(r"^(?:<{7} |>{7} |\|{7} )", re.M)


def main():
    bad = []
    for p in glob.glob(os.path.join(SITE, "**", "*"), recursive=True):
        if not os.path.isfile(p):
            continue
        if os.path.splitext(p)[1].lower() in (".png", ".jpg", ".jpeg", ".gif", ".ico",
                                              ".woff", ".woff2", ".pdf", ".zip"):
            continue
        if ".bak" in os.path.basename(p).lower():
            continue          # backups are gitignored and never deploy
        try:
            doc = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        m = MARK.search(doc)
        if m:
            rel = os.path.relpath(p, SITE).replace("\\", "/")
            line = doc.count("\n", 0, m.start()) + 1
            bad.append(f"{rel}:{line}: {doc[m.start():m.start()+40]!r}")

    if bad:
        print(f"FAIL: git conflict markers in {len(bad)} file(s) -- an unresolved merge or")
        print("stash-apply is about to ship to production. This happened on 2026-08-11 and the")
        print("homepage showed two boards for a day. Resolve the conflict, rebuild, recommit.")
        for b in bad[:8]:
            print(f"   {b}")
        return 1
    print("  PASS: no git conflict markers anywhere in the site tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
