# -*- coding: utf-8 -*-
"""test_llms_txt_pages_exist.py -- every page /llms.txt names is a page this build made.

/llms.txt is the file AI assistants are pointed at and asked to quote. 2026-11-26: it gained the newer hubs
(/screener, /earnings, /devices/decisions, /fda-application, /condition) and the one-page-per-company, drug and
decision patterns, each printed only when its page is on disk. This fails if:
  1. a "- /path - ..." line, or a "(for example /path)" example, names a path with no index.html under
     pdufa_site_src (a dead page handed to an assistant), unless the path is a file the site serves (.xml, .csv);
  2. build_llms_txt.more_pages() prints a hub whose page is missing.
PLANT=dead adds a line for a page that does not exist; it must FAIL.

    python tests/test_llms_txt_pages_exist.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
import build_llms_txt as L  # noqa: E402


def built(path):
    path = path.split("#")[0].split("?")[0].rstrip("/")
    if re.search(r"\.[a-z]{2,4}$", path):
        return os.path.isfile(os.path.join(SITE, *path.strip("/").split("/")))
    return os.path.isfile(os.path.join(SITE, *path.strip("/").split("/"), "index.html")) if path else True


def main():
    txt = open(os.path.join(SITE, "llms.txt"), encoding="utf-8").read()
    if os.environ.get("PLANT") == "dead":
        txt += "\n- /no-such-hub-zz - planted\n"
    paths = re.findall(r"^- (/[^\s<]*?)(?=\s|$)", txt, re.M)
    paths += re.findall(r"\(for example (/[^\s)]+)\)", txt)
    bad = [p for p in paths if "<" not in p and not built(p)]
    hubs = [p for p, _ in L.MORE_HUBS if f"- {p} - " in L.more_pages()]
    bad += [f"{p} (more_pages)" for p in hubs if not built(p)]
    print(f"llms.txt pages: {len(paths)} path(s) checked")
    if bad:
        print(f"FAIL: {len(bad)} path(s) with no built page")
        for b in bad:
            print("  " + b)
        return 1
    print("  PASS: every page /llms.txt names is built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
