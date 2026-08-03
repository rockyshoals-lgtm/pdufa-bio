# -*- coding: utf-8 -*-
"""strip_dashes.py -- remove em/en dashes used as punctuation across the site.

The em dash is the single loudest "written by a language model" tell in prose, and the site had
~4,500 of them. This replaces them with ordinary punctuation without touching the things that only
LOOK like dashes: hyphenated words (run-up, T-90, first-in-class), CSS, JavaScript, ticker slugs and
ISO dates all use the ASCII hyphen and are left completely alone.

Rules, in order:

  1. Known templated phrases get a hand-written replacement (these are ~70% of all occurrences and
     a generic rule would produce comma splices: "Facts only, verify against primary filings").
  2. A dash that IS the whole value of a cell is a missing-data marker, not punctuation, so it
     becomes explicit text ("Not listed" / "n/a") which is also better for screen readers.
  3. Everything else: a colon when the dash separates a label from a short value or title fragment,
     otherwise a comma.

<script> and <style> blocks are excluded entirely. Run --preview first: it writes every distinct
replacement to dash_sweep_review.txt so the tail can actually be read rather than trusted.

    python strip_dashes.py --preview
    python strip_dashes.py
"""
import argparse, collections, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
REVIEW = os.path.join(HERE, "dash_sweep_review.txt")

EM = "—"
EN = "–"

# 1. Curated replacements for the templated phrases.
PHRASES = [
    (f" {EM} verify against primary filings", ". Verify against primary filings"),
    (f" {EM} verify against the official program", ". Verify against the official program"),
    (f" {EM} history, not a prediction", ". History, not a prediction"),
    (f" {EM} not a prediction", ". Not a prediction"),
    (f" {EM} not investment advice", ". Not investment advice"),
    (f' {EM} <a href="/why-no-approval-probability">here&rsquo;s why</a>',
     '. <a href="/why-no-approval-probability">Here&rsquo;s why</a>'),
    (f' {EM} <a href="/why-no-approval-probability">here\'s why</a>',
     '. <a href="/why-no-approval-probability">Here\'s why</a>'),
    (f" {EM} direction removed", ". Direction removed"),
    (f" {EM} a handful of", ". A handful of"),
]

# 2. A lone dash standing in for a missing value.
CELL_RULES = [
    (re.compile(r"<b>\s*" + EM + r"\s*</b>"), "<b>Not listed</b>"),
    (re.compile(r"(<td[^>]*>)\s*" + EM + r"\s*(</td>)"), r"\1n/a\2"),
]

# Placeholders that JavaScript overwrites at runtime. Not prose, leave them alone.
KEEP_IDS = ("asof", "cnt")

SKIP_BLOCK = re.compile(
    # Real JavaScript only. JSON-LD is swept: its description fields are what Google renders in
    # rich results, so an em dash there is as visible as one in the body copy.
    r"<script\b(?![^>]*ld\+json).*?</script>"
    r"|<style\b.*?</style>"
    # elements whose dash is a loading placeholder that JavaScript replaces on hydration
    r"|<(?:b|span|div|td)[^>]*id=\"(?:" + "|".join(KEEP_IDS) + r")\"[^>]*>.*?</(?:b|span|div|td)>",
    re.S | re.I)


# A dash joining two independent clauses cannot become a comma without creating a splice, so those
# take a semicolon. Detected by a finite verb in the clause that follows.
FINITE = re.compile(r"\b(is|are|was|were|makes?|has|have|had|will|would|should|can|does|do|did|"
                    r"went|means?|appears?|seems?|remains?|gets?|becomes?)\b")
# Leading conjunctions, prepositions and subordinators never take a colon: the dash there is joining
# a trailing modifier, not introducing a value.
CONJ = re.compile(r"^(and|but|so|or|plus|yet|not|no|nor|for|with|without|because|since|while|"
                  r"after|before|though|although|i\.e|e\.g|even|despite|unless|until)\b", re.I)
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
RANGES = [
    # "Oct 2024 - Aug 2026" and "9:30am - 4:00pm": ranges read as "to", never as punctuation.
    (re.compile(r"(" + MONTHS + r"[a-z]*\.? ?\d{0,4}) ?[—–] ?(" + MONTHS + r")"), r"\1 to \2"),
    (re.compile(r"(\$?[\d.,]+ ?(?:am|pm|%|M|B)?) ?[—–] ?(\$?[\d.,]+ ?(?:am|pm|%|M|B))"), r"\1 to \2"),
]


def choose(after):
    """Colon for a short label/value, semicolon between two clauses, comma otherwise."""
    seg = re.split(r"[<|.;]", after, 1)[0].strip()
    seg = re.sub(r"&[a-z]+;", " ", seg)
    words = [w for w in seg.split() if w]
    if not words:
        return ", "
    if len(words) <= 8 and not CONJ.match(seg):
        return ": "
    if CONJ.match(seg):
        return ", "
    return "; " if FINITE.search(" " + seg + " ") else ", "


def sweep(text, log):
    for a, b in PHRASES:
        if a in text:
            log[(a, b)] += text.count(a)
            text = text.replace(a, b)

    for rx, rep in CELL_RULES:
        def _c(m):
            if any(f'id="{i}"' in m.group(0) for i in KEEP_IDS):
                return m.group(0)
            log[(m.group(0), rep)] += 1
            return re.sub(rx, rep, m.group(0))
        text = rx.sub(_c, text)

    # en dash between two alphanumerics is a range, not punctuation -> plain hyphen
    def _en(m):
        log[(m.group(0), m.group(1) + "-" + m.group(2))] += 1
        return m.group(1) + "-" + m.group(2)
    text = re.sub(r"(\w)" + EN + r"(\w)", _en, text)

    # Iterative, not recursive: some pages carry hundreds of dashes and recursion would blow the
    # stack. Each pass rewrites the first remaining dash and resumes scanning after it.
    rx = re.compile("[" + EM + EN + "]")
    pos = 0
    while True:
        m = rx.search(text, pos)
        if not m:
            break
        pre, post = text[:m.start()], text[m.end():]
        rep = choose(post[:120])
        ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 45):m.start()])[-45:]
        nxt = re.sub(r"\s+", " ", post[:45])
        log[(ctx + " [" + m.group(0) + "] " + nxt, rep.strip())] += 1
        left = pre.rstrip(" ")
        right = post.lstrip(" ")
        text = left + rep + right
        pos = len(left) + len(rep)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    log = collections.Counter()
    changed = files = 0
    for root, _, fs in os.walk(SITE):
        for f in fs:
            if not f.endswith(".html") or f.startswith("_"):
                continue
            p = os.path.join(root, f)
            html = open(p, encoding="utf-8", errors="replace").read()
            files += 1
            orig = html
            html = html.replace("&mdash;", EM).replace("&ndash;", EN)

            blocks = []

            def stash(m):
                blocks.append(m.group(0))
                return f"\x00BLK{len(blocks)-1}\x00"
            html = SKIP_BLOCK.sub(stash, html)

            html = sweep(html, log)

            html = re.sub(r"\x00BLK(\d+)\x00", lambda m: blocks[int(m.group(1))], html)
            if html != orig:
                changed += 1
                if not a.preview:
                    open(p, "w", encoding="utf-8").write(html)

    lines = [f"{v:6d}  {k[0]}   ==>   {k[1]}" for k, v in log.most_common()]
    open(REVIEW, "w", encoding="utf-8").write("\n".join(lines))
    print(f"scanned {files:,} files; {'would change' if a.preview else 'changed'} {changed:,}")
    print(f"total dash replacements: {sum(log.values()):,}  ({len(log):,} distinct contexts)")
    print(f"full review -> {os.path.basename(REVIEW)}")


if __name__ == "__main__":
    main()
