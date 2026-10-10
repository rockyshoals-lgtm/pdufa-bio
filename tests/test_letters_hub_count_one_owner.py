# -*- coding: utf-8 -*-
"""CI guard: /fda-approval-letters states one count in its title, h1, Dataset schema and table (audit 2026-10-04 item 5).

    python tests/test_letters_hub_count_one_owner.py
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(HERE, "pdufa_site_src", "fda-approval-letters", "index.html")


def main():
    doc = io.open(P, encoding="utf-8", errors="replace").read()
    t = re.search(r"<title>.*?(\d+) FDA Decisions", doc, re.S)
    h = re.search(r"<h1[^>]*>.*?(\d+) FDA decisions", doc, re.S)
    size = None
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
        try:
            j = json.loads(m.group(1))
        except ValueError:
            continue
        if j.get("@type") == "Dataset":
            size = ((j.get("size") or {}).get("value"))
    rows = len(re.findall(r"<tr[^>]*>", doc)) - 1
    vals = {"title": t and int(t.group(1)), "h1": h and int(h.group(1)), "schema": size, "table_rows": rows}
    if None in vals.values() or len(set(vals.values())) != 1:
        print(f"FAIL: /fda-approval-letters counts disagree: {vals}")
        return 1
    print(f"OK -- /fda-approval-letters: {rows} FDA actions stated in title, h1, Dataset schema and table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
