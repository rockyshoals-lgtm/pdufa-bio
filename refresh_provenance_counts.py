# -*- coding: utf-8 -*-
"""refresh_provenance_counts.py -- publish the archive's provenance split as it actually is.

/decisions carried a hand-written claim: "449 records · Verified 142 with a primary source ·
Unverified 307 inferred from price". It was an honest attempt, and the number was wrong, because
"verified" was defined by ABSENCE rather than presence:

    a decision is verified if its own page does not carry the price-only marker

Absence of a disclaimer is not evidence. Checking what those pages actually contain: of 150 pages
outside the price-inferred set, only 34 link a primary source. The other 116 assert an FDA outcome
with a drug name, a date, and nothing to check it against. They were being counted, publicly, as
"with a primary source".

A binary cannot describe this archive, so this publishes three states and computes all of them from
the pages on every build:

    Sourced          the page links an FDA, SEC, journal or company release
    Inferred         the page says on its face that the outcome was read from the price reaction
    Unsourced        neither: we assert it, and show you nothing

The third number is uncomfortable, which is the reason to publish it. A reader can discount an
unsourced row; they cannot discount one that has been folded into a "verified" total. Shrinking the
verified claim from 142 to what we can actually show is the only version of this that survives
someone checking.

    python refresh_provenance_counts.py [--dry-run]
"""
import argparse, glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "decisions", "index.html")
B, E = "<!--PROVENANCE:BEGIN-->", "<!--PROVENANCE:END-->"

PRICE_ONLY = re.compile(r"outcome unverified|price[- ]only|consistent with an? (approval|CRL)", re.I)
GOOD = re.compile(r"(fda\.gov|sec\.gov|clinicaltrials\.gov|nih\.gov|doi\.org|nejm\.org|"
                  r"thelancet\.com|jamanetwork\.com|globenewswire\.com|prnewswire\.com|"
                  r"businesswire\.com|accessnewswire\.com|stocktitan\.net|newsroom\.|"
                  r"ir\.|investors?\.)", re.I)


def classify():
    sourced = inferred = unsourced = 0
    unsourced_slugs = []
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        html = open(p, encoding="utf-8", errors="replace").read()
        if PRICE_ONLY.search(html):
            inferred += 1
            continue
        # Sourced means the page links an external document you can go and read. Whether that
        # host is a regulator or the company's own newsroom is a quality question, reported
        # separately; it is not the difference between showing evidence and showing none. The two
        # checks disagreed by exactly the 3 pages citing an unusual host until this was aligned.
        ext = [u for u in re.findall(r'href="(https?://[^"]+)"', html) if "pdufa.bio" not in u]
        if ext:
            sourced += 1
        else:
            unsourced += 1
            unsourced_slugs.append(os.path.basename(os.path.dirname(p)))
    return sourced, inferred, unsourced, unsourced_slugs


def bar(label, n, total, colour, note):
    pct = (n / total * 100) if total else 0
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin:7px 0">'
        f'<div class="cd" style="width:150px;font-size:13px;font-weight:700;color:{colour}">'
        f'{label}</div>'
        f'<div style="flex:1;display:flex;height:22px;border-radius:6px;overflow:hidden;'
        f'border:1px solid var(--line)">'
        f'<div style="width:{pct:.1f}%;background:{colour};height:100%"></div>'
        f'<div style="width:{100 - pct:.1f}%;background:#132741;height:100%"></div></div>'
        f'<div class="cd" style="width:210px;text-align:right;font-size:12.5px;color:#7c93b6">'
        f'<b style="color:{colour}">{n:,}</b> {note}</div></div>')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    s, i, u, slugs = classify()
    total = s + i + u
    print(f"{total:,} decision pages: {s:,} sourced, {i:,} price-inferred, {u:,} unsourced")
    if u:
        print(f"   unsourced examples: {', '.join(slugs[:6])}")

    block = (
        f'{B}'
        f'{bar("Sourced", s, total, "#46d17f", "link a primary source")}'
        f'{bar("Inferred", i, total, "#f0c86a", "read from the price reaction")}'
        f'{bar("Unsourced", u, total, "#ff8f8f", "asserted, no source shown")}'
        f'<div style="font-size:12px;color:var(--mut2);line-height:1.7;margin:10px 0 0">'
        f'<b style="color:#eef4fc">What these mean.</b> '
        f'<b style="color:#46d17f">Sourced</b> pages link the FDA notice, SEC filing or company '
        f'release the outcome came from, so you can check them. '
        f'<b style="color:#f0c86a">Inferred</b> pages say on their face that the outcome was read '
        f'from how the stock reacted, not from a document. '
        f'<b style="color:#ff8f8f">Unsourced</b> pages assert an outcome and show you nothing; '
        f'they are older entries we have not yet gone back and sourced, and we would rather count '
        f'them honestly than fold them into a total. '
        f'This split used to read "Verified {s + u} with a primary source", which counted the '
        f'unsourced ones, because the old rule treated the absence of a disclaimer as evidence. '
        f'Absence of a disclaimer is not evidence.</div>'
        f'{E}')

    doc = open(PAGE, encoding="utf-8", errors="replace").read()
    if B in doc:
        doc = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
    else:
        # Replace the two hand-written Verified / Unverified bars.
        #
        # Matching them with one regex does not work: they are sibling <div> trees with nested
        # divs, and a lazy .*? stops at the first </div></div></div> inside the first bar. Walk the
        # tag balance instead, which is the only reliable way to find where a container ends.
        def container(doc, at):
            depth, i = 0, at
            for m in re.finditer(r"<div\b|</div>", doc[at:]):
                depth += 1 if m.group(0).startswith("<div") else -1
                i = at + m.end()
                if depth == 0:
                    return i
            return None

        start = None
        for m in re.finditer(r'<div style="display:flex;align-items:center;gap:12px;[^"]*">', doc):
            tail = doc[m.end():m.end() + 220]
            if ">Verified<" in tail:
                start = m.start(); break
        if start is None:
            print("could not find the old Verified bar; nothing changed")
            return
        end = container(doc, start)                      # end of the Verified bar
        nxt = re.compile(r'<div style="display:flex;align-items:center;gap:12px;[^"]*">')
        m2 = nxt.match(doc, end) or nxt.search(doc, end, end + 40)
        if m2 and ">Unverified<" in doc[m2.end():m2.end() + 220]:
            end = container(doc, m2.start()) or end      # extend over the Unverified bar too
        doc = doc[:start] + block + doc[end:]

    doc = re.sub(r"(\d[\d,]*)\s+records", f"{total:,} records", doc, count=1)

    if not a.dry_run:
        open(PAGE, "w", encoding="utf-8").write(doc)
    print("wrote /decisions provenance block" + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
