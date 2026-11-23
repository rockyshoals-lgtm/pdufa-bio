# -*- coding: utf-8 -*-
"""CI guard: no phrase written twice in a row, and no footer sentence said twice.

2026-11-20 (live check): two stutters were on pdufa.bio at once.
  * /ticker/TARS read "TP-04 Kore Phase 2 Phase 2 topline". Readout names were joined as program + trial + readout
    with the shared phrase written twice; 60 dataset names carried it ("Phase 3 Phase 3", "Part A Part A",
    "VK2735 VK2735", ...), so every page built from the dataset did too. Fixed by text_hygiene.join_phrases at the
    writer and fix_repeated_phrases.py in the rebuild.
  * The /runup-by-year footer said "past behaviour does not predict future outcomes" twice, and /vktx said
    "Nothing on this page is investment ... advice" twice: apply_legal_footer.py kept a wrapped copy of a sentence
    its canonical text already says.

Checks
  1. every row name in the API dataset;
  2. the visible text of every page (one text run at a time, so a table's adjacent cells never count) and every
     SUMMARY in /calendar.ics;
  3. every legal footer (<div class="legal"> or <footer>): no run of six words twice.
A repeat is 1-6 words that come again straight away, case-insensitively, and contain a letter ("2026 2026" in a
table is numbers). ALLOW holds a phrase that is meant to repeat (a place like "Walla Walla"), lower case.

PLANT=1 adds one stutter to each check in memory, to show each check fails when it should.
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from text_hygiene import find_repeat  # noqa: E402
from crl_verbatim import strip_verbatim  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
ALLOW = set()
PLANT = os.environ.get("PLANT") == "1"
STRIP = re.compile(r"<(script|style|svg)\b.*?</\1>|<!--.*?-->",
                   re.S | re.I)
FOOTERS = re.compile(r'<div class="legal"[^>]*>(.*?)</div>|<footer[^>]*>(.*?)</footer>', re.S)
DOTS = [("pdufa.bio", "pdufabio"), ("U.S.", "US"), ("e.g.", "eg"), ("i.e.", "ie"), ("Inc.", "Inc"), ("vs.", "vs")]


def repeat(text):
    r = find_repeat(text)
    return r if r and r.lower() not in ALLOW else None


def pages():
    out = []
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        rel = os.path.relpath(p, SITE)
        if re.search(r"(^|[\\/])_[^\\/]*bak", rel) or "xbak" in rel:
            continue
        out.append(p)
    return sorted(out)


def footer_dupes(inner, n=6):
    """Any run of n words the footer says twice ("past behaviour does not predict future outcomes" once on its own
    and once inside the canonical sentence counts, which a whole-sentence comparison missed)."""
    t = re.sub(r"<[^>]+>", " ", inner)
    t = html.unescape(t)
    for a, b in DOTS:
        t = t.replace(a, b)
    w = re.sub(r"[^a-z0-9]+", " ", t.lower()).split()
    first, dup = {}, []
    for i in range(len(w) - n + 1):
        g = tuple(w[i:i + n])
        if g in first and i - first[g] >= n:
            dup.append(" ".join(g))
            break
        first.setdefault(g, i)
    return dup


def main():
    bad = []

    # 1. dataset names
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.find("["):src.rfind("]") + 1])
    if PLANT:
        rows.append({"id": "PLANT", "name": "TP-04 Kore Phase 2 Phase 2 topline"})
    for r in rows:
        rp = repeat(r.get("name") or "")
        if rp:
            bad.append(f"api/v1/dataset.mjs {r.get('id')}: name {r.get('name')!r} repeats '{rp}'")

    # 2 + 3. page text and footers
    files = pages()
    for p in files:
        raw = io.open(p, encoding="utf-8", errors="replace").read()
        if PLANT and p.endswith(os.path.join("ticker", "TARS", "index.html")):
            raw = raw.replace("<body", "<body><p>Kore Phase 2 Phase 2 topline</p", 1)
        if PLANT and p.endswith(os.path.join("runup-by-year", "index.html")):
            raw = re.sub(r'(<div class="legal"[^>]*>)', r"\1Past behaviour does not predict future outcomes. ", raw, count=1)
            raw = re.sub(r'(<div class="legal"[^>]*>.*?)(</div>)',
                         r"\1 Past behaviour does not predict future outcomes.\2", raw, count=1, flags=re.S)
        rel = os.path.relpath(p, SITE).replace("\\", "/")
        # the FDA's own words on /crl/letter pages are kept as released, stutters included (crl_verbatim.py)
        txt = strip_verbatim(STRIP.sub(" ", raw), p)
        for node in re.findall(r">([^<]{6,})<", txt):
            rp = repeat(html.unescape(node))
            if rp:
                bad.append(f"{rel}: '{rp}' in {html.unescape(node).strip()[:90]!r}")
        for m in FOOTERS.finditer(txt):
            for d in footer_dupes(m.group(1) or m.group(2) or ""):
                bad.append(f"{rel}: footer says twice: {d!r}")

    ics = os.path.join(SITE, "calendar.ics")
    if os.path.exists(ics):
        t = re.sub(r"\r?\n[ \t]", "", io.open(ics, encoding="utf-8").read())
        if PLANT:
            t += "\nSUMMARY:~TARS Readout: TP-04 Kore Phase 2 Phase 2 topline\n"
        for line in t.splitlines():
            if line.startswith("SUMMARY:"):
                rp = repeat(line.replace("\\,", ","))
                if rp:
                    bad.append(f"calendar.ics: '{rp}' in {line[:100]!r}")

    for b in bad[:40]:
        print("  FAIL", b)
    if bad:
        print(f"{len(bad)} repeated phrase(s) or footer sentence(s). Names: run fix_repeated_phrases.py; "
              f"footers: apply_legal_footer.py; anything meant to repeat goes in ALLOW.")
        sys.exit(1)
    print(f"OK -- no phrase written twice in a row in {len(rows)} dataset names, {len(files)} pages or the "
          f"calendar feed, and no footer says a sentence twice.")


if __name__ == "__main__":
    main()
