# -*- coding: utf-8 -*-
"""dedupe_decision_summary.py -- a decision page states its decision once, then gives the detail.

Design red team 2026-11-18 (change 10). GSK's Nelkarmi page stated the approval about nine times: the fact lede, the
Verified-against line, a summary paragraph ("The FDA granted accelerated approval to Nelkarmi (neladalkib) on November
17, 2026 for adults with ...") that the narrative below key facts says again in full, the narrative, the FDA-record
line and two FAQs asking the same question. The fact lede is the one statement; the Verified-against and FDA-record
lines are provenance; the narrative is the detail. This removes the summary paragraph under the banner when every
word it carries (names, numbers, terms) is already in the page's own content -- the lede, key facts, narrative,
FDA-record line and FAQ -- so no fact leaves the page. A summary that holds anything the rest does not is kept.
build_decision_faq.py lets a hand-written approval question replace the generated one (the duplicate FAQ).

Runs after build_decision_lede.py. Idempotent. tests/test_decision_page_one_statement.py fails on a summary that
says nothing the page does not.

    python dedupe_decision_summary.py [--dry-run]
"""
import argparse
import glob
import html
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STOP = set("that with this from were have their which into after before only first also about been under than more "
           "over other these those such there where when whose being would could should approved approval granted "
           "announced announces said says states same study trial".split())
DECISION_WORDS = re.compile(r"approv|granted|Complete Response|Not Approvable", re.I)


def tokens(text):
    return {w.lower().strip(".,;:()") for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}|\d[\d.,%]*\d|\d", text)} - STOP - {""}


def plain(fragment):
    fragment = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", fragment, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def summary_span(doc):
    """(start, end, inner html) of the first plain paragraph under the banner, past the lede and provenance lines."""
    i = doc.find('<div class="ban ')
    if i < 0:
        return None
    j = doc.find("<h2", i)
    if j < 0:
        return None
    for m in re.finditer(r'<p class="sub"[^>]*>(.*?)</p>', doc[i:j], re.S):
        st = i + m.start()
        if re.search(r"<!--(FACTLEDE|VERIFIED|FIRSTREC):BEGIN-->(?:(?!<!--).)*$", doc[:st], re.S):
            continue
        return st, i + m.end(), m.group(1)
    return None


def content(doc, span):
    """The page's own content apart from the summary: banner to the end of the FAQ, without the nav blocks."""
    st, en, _ = span
    i = doc.find('<div class="ban ')
    k = doc.find("<!--DFAQ:END-->")
    body = doc[i:st] + doc[en:(k if k > en else len(doc))]
    body = re.sub(r"<!--(RELATED|SITELINKS|LETTERSLINK|F13|VERIFIED|FIRSTREC):BEGIN-->.*?<!--\1:END-->", " ", body, flags=re.S)
    return plain(body)


def number_pairs(text):
    """Each number with the word before it ("September 26", "supplement 10", "ages 12"): a bare "26" proves nothing."""
    t = re.sub(r"\s+", " ", text.lower())
    return {f"{a} {b}" for a, b in re.findall(r"([a-z][a-z\-]*)[ ,(]+(\d[\d.,%]*\d|\d)\b", t)}


def missing(doc, span):
    rest_text = content(doc, span)
    rest = tokens(rest_text)
    rest |= {w.split("-")[0] for w in rest}
    words = [w for w in tokens(plain(span[2])) - rest if not all(x in rest for x in w.split("-"))]
    # numbers: the pair must be on the page (a date may also be written m/d/yy or Mon D)
    rest_pairs = number_pairs(rest_text)
    full = {"jan": "january", "feb": "february", "mar": "march", "apr": "april", "jun": "june", "jul": "july",
            "aug": "august", "sep": "september", "oct": "october", "nov": "november", "dec": "december"}
    rest_pairs |= {f"{full.get(a, a)} {b}" for a, b in (x.split(" ", 1) for x in rest_pairs)}
    mine = {f"{full.get(a, a)} {b}" for a, b in (x.split(" ", 1) for x in number_pairs(plain(span[2])))}
    nums = [x for x in mine if x not in rest_pairs and not x.split(" ")[0] in STOP | {"on", "in", "of", "and", "the", "to", "by", "at", "for"}]
    return sorted(set(words) | set(nums))


def redundant(doc):
    span = summary_span(doc)
    if not span or "<!--FACTLEDE:BEGIN-->" not in doc or not DECISION_WORDS.search(plain(span[2])):
        return None
    return span if not missing(doc, span) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        span = redundant(doc)
        if not span:
            continue
        new = doc[:span[0]] + doc[span[1]:]
        n += 1
        print(f"  /fda-decision/{os.path.basename(os.path.dirname(p))}: summary repeated the page, removed")
        if not a.dry_run:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"decision summaries: {n} removed (each said nothing the rest of its page does not)" +
          (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
