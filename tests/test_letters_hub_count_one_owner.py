# -*- coding: utf-8 -*-
"""CI guard: /fda-approval-letters states one count in its title, h1, Dataset schema and table (audit 2026-10-04 item 5).

    python tests/test_letters_hub_count_one_owner.py
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(HERE, "pdufa_site_src", "fda-approval-letters", "index.html")


def counts(doc):
    """The four places the hub states its size."""
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
    # one table per year since 2025 actions joined (2026-11-18); each table has its own header row
    rows = len(re.findall(r"<tr[^>]*>(?!\s*<th)", doc))
    return {"title": t and int(t.group(1)), "h1": h and int(h.group(1)), "schema": size, "table_rows": rows}


def agree(vals):
    return None not in vals.values() and len(set(vals.values())) == 1


def _page(stated, rows_per_year):
    """A minimal hub page: `stated` in title/h1/schema, one table per year with its own header row."""
    tables = "".join("<table><tr><th>FDA action date</th><th>Drug</th></tr>"
                     + "".join(f"<tr><td>d{i}</td><td>x</td></tr>" for i in range(n)) + "</table>"
                     for n in rows_per_year)
    return (f"<title>FDA Approval Letters: {stated} FDA Decisions</title><h1>Letters: {stated} FDA decisions</h1>"
            f'<script type="application/ld+json">{{"@type": "Dataset", "size": {{"value": {stated}}}}}</script>' + tables)


def self_test():
    """2026-11-18: the guard read one header row, so a second year's table counted as a row. It must still catch a
    real mismatch: a dropped row, an extra row, or a count stated wrongly in one place."""
    assert agree(counts(_page(5, [3, 2]))), "two-year hub with matching counts must pass"
    assert agree(counts(_page(3, [3]))), "one-year hub must pass"
    assert not agree(counts(_page(5, [3, 1]))), "a missing table row must fail"
    assert not agree(counts(_page(5, [4, 2]))), "an extra table row must fail"
    bad = _page(5, [3, 2]).replace("5 FDA decisions</h1>", "6 FDA decisions</h1>")
    assert not agree(counts(bad)), "an h1 that disagrees must fail"


def main():
    self_test()
    doc = io.open(P, encoding="utf-8", errors="replace").read()
    vals = counts(doc)
    rows = vals["table_rows"]
    if not agree(vals):
        print(f"FAIL: /fda-approval-letters counts disagree: {vals}")
        return 1
    print(f"OK -- /fda-approval-letters: {rows} FDA actions stated in title, h1, Dataset schema and table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
