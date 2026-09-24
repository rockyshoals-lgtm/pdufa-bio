# -*- coding: utf-8 -*-
"""CI guard: no indexable page says "1 days" (or "1 Days").

2026-09-23: MRK's WINREVAIR label update was approved one day after its goal date and the
decision page shipped "1 Days Late" in its <title> and "1 days after its" in the meta
description -- the two strings an answer engine lifts verbatim. GSK/SPRO/VTRS had carried
"1 Days Early" since June. The three owners (rewrite_decision_snippets, mark_event_pages_decided,
build_early_decisions) now pluralise through _dw(); this catches any writer that does not.

    python tests/test_no_one_days.py
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
SKIP = re.compile(r"[\\/]_[a-z]+bak|[\\/]_pdufa_")
PAT = re.compile(r"(?<![\d.,])[+-]?1 [Dd]ays\b")


def main():
    fails, n = [], 0
    for f in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if SKIP.search(f):
            continue
        doc = io.open(f, encoding="utf-8", errors="replace").read()
        if re.search(r'name="robots"[^>]*noindex', doc[:4000]):
            continue
        n += 1
        text = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", doc)
        text = re.sub(r"<[^>]+>", " ", text)
        for m in PAT.finditer(text):
            rel = "/" + os.path.relpath(os.path.dirname(f), SITE).replace("\\", "/")
            fails.append(f"{rel}: '{text[max(0, m.start() - 40):m.end() + 20].strip()}'")
            break
        else:
            m = re.search(r"<title>[^<]*\b1 [Dd]ays\b|name=\"description\" content=\"[^\"]*\b1 [Dd]ays\b", doc)
            if m:
                rel = "/" + os.path.relpath(os.path.dirname(f), SITE).replace("\\", "/")
                fails.append(f"{rel}: title/description says '1 days'")
    if fails:
        print(f"FAIL: {len(fails)} indexable page(s) say '1 days':")
        for x in fails[:20]:
            print("   " + x)
        return 1
    print(f"OK -- no '1 days' on {n} indexable page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
