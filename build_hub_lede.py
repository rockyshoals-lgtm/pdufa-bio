# -*- coding: utf-8 -*-
"""build_hub_lede.py -- one declarative sentence above each table, so we get quoted and not just ranked.

We are #3 on Bing for the head query. Positions 1 and 2 are beatable on substance, but the thing
that actually moves a result from "listed" to "quoted" -- in a Bing snippet, in an AI answer, in a
People-Also-Ask box -- is a single sentence that answers the question outright, in the first words,
without the reader opening the page.

Our hubs open with a table. A table is the best possible thing for a human comparing dates and the
worst possible thing for an extractor, which has nothing to lift. Every one of these pages was
leading with rows.

So each hub gets one sentence stating what the page contains, in numbers.

The rule that makes this safe: EVERY FIGURE IS COUNTED FROM THE PAGE'S OWN ROWS, at build time,
immediately before the sentence is written. Not from the dataset, not from a constant, not from a
second query that could drift. If the table says 452 decisions, the sentence says 452, because it
counted them. A summary that disagrees with the table beneath it is worse than no summary: it is
the exact failure this site exists not to have.

If the row parse finds nothing, the page is skipped loudly rather than given a sentence containing
a zero. Publishing "0 FDA decisions are scheduled" because a CSS class changed is how a page that
ranks becomes a page that embarrasses us.

    python build_hub_lede.py [--dry-run]
"""
import argparse, datetime as dt, html, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--LEDE:BEGIN-->", "<!--LEDE:END-->"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
ABBR = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)}

ROW = re.compile(r'<a class="row"[^>]*>(.*?)</a>', re.S)


def text_of(frag):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frag))).strip()


def row_date(t):
    """(year, month) from a row label, at whatever precision it carries."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(?:\d{1,2},\s*)?(\d{4})", t)
    if m and m.group(1).lower() in ABBR:
        return int(m.group(2)), ABBR[m.group(1).lower()]
    return None


def span(dates):
    """'August 2026 to May 2027', or a single month when they all share one."""
    if not dates:
        return ""
    lo, hi = min(dates), max(dates)
    a, b = f"{MONTHS[lo[1] - 1]} {lo[0]}", f"{MONTHS[hi[1] - 1]} {hi[0]}"
    return a if a == b else f"{a} to {b}"


def parse(doc):
    out = []
    for frag in ROW.findall(doc):
        t = text_of(frag)
        low = t.lower()
        iso = re.search(r"\d{4}-\d{2}-\d{2}", t)
        out.append({
            "text": t,
            "iso": iso.group(0) if iso else None,
            "date": row_date(t),
            "approved": "approved" in low,
            "crl": "crl" in low or "complete response" in low,
        })
    return out


def sentence(path, rows):
    n = len(rows)
    dates = [r["date"] for r in rows if r["date"]]
    when = span(dates)
    ap = sum(1 for r in rows if r["approved"])
    crl = sum(1 for r in rows if r["crl"])

    if path == "calendar":
        # "Still ahead" has to mean still ahead. A row whose date has passed with no outcome
        # published is waiting on the FDA, not upcoming, and lumping the two together would put a
        # false statement in the one sentence written to be quoted.
        today = dt.date.today().isoformat()
        decided = ap + crl
        rest = [r for r in rows if not (r["approved"] or r["crl"])]
        upcoming = sum(1 for r in rest if not r["iso"] or r["iso"] >= today)
        awaiting = len(rest) - upcoming

        s = (f"This page lists {n} FDA decision dates"
             + (f" covering {when}" if when else "") + ". ")
        if decided:
            s += f"{upcoming} are still ahead, and {decided} have been decided and are marked "\
                 f"with the outcome. "
            if awaiting:
                s += (f"{awaiting} passed its target date without a published decision."
                      if awaiting == 1 else
                      f"{awaiting} have passed their target date without a published decision.")
                s += " "
        s += ("Each date comes from an FDA notice or a company filing, and where the source gives "
              "only a month or a quarter we say so instead of inventing a day.")
        return s

    if path == "decisions":
        s = f"This page lists {n} FDA decisions"
        if ap or crl:
            s += f", {ap} approvals and {crl} Complete Response Letters"
        s += (f", covering {when}. " if when else ". ")
        s += ("Every decision has its own page carrying the source document and the share-price "
              "reaction we measured on the day.")
        return s

    if path == "decisions/approvals":
        return (f"This page lists {n} FDA approvals"
                + (f" covering {when}" if when else "") + ". "
                + "Each one links the FDA approval notice or the company filing that announced it.")

    if path == "decisions/crl":
        return (f"This page lists {n} Complete Response Letters"
                + (f" covering {when}" if when else "") + ". "
                + "A Complete Response Letter means the FDA declined to approve the application as "
                  "submitted, and it does not by itself mean the drug is rejected for good.")

    if path == "readouts":
        return (f"This page lists {n} expected clinical trial readouts"
                + (f" covering {when}" if when else "") + ". "
                + "These dates come from company guidance and ClinicalTrials.gov, so most are known "
                  "only to a month or a quarter, and we publish them at that precision rather than "
                  "guessing a day.")

    if path == "adcomm":
        voted = sum(1 for r in rows if "voted" in r["text"].lower())
        s = (f"This page lists {n} FDA advisory committee meetings"
             + (f" covering {when}" if when else "") + ". ")
        if voted:
            s += f"{voted} have taken a vote, and the vote count is shown. "
        s += ("An advisory committee vote is a recommendation to the FDA, which is not bound by it "
              "and has gone against it before.")
        return s
    return None


def homepage_sentence():
    """The one page that is not a table, and the one most likely to be ranking.

    Its h1 is a slogan and the next thing on the page is a search box, so there was no extractable
    fact anywhere near the top of the most important URL we own.

    The counts here are read from the sibling pages rather than recomputed, for the same reason the
    other ledes count their own rows: /calendar, /decisions and /readouts each publish a number, and
    the homepage must not be able to state a different one. Deriving all four from the same rows
    makes disagreement impossible rather than merely unlikely.
    """
    def rows_of(rel):
        f = os.path.join(SITE, rel, "index.html")
        if not os.path.exists(f):
            return []
        doc = open(f, encoding="utf-8", errors="replace").read()
        return parse(re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S))

    cal, dec, rd = rows_of("calendar"), rows_of("decisions"), rows_of("readouts")
    if not (cal and dec):
        return None

    today = dt.date.today().isoformat()
    ahead = sum(1 for r in cal if not (r["approved"] or r["crl"])
                and (not r["iso"] or r["iso"] >= today))
    ap = sum(1 for r in dec if r["approved"])
    crl = sum(1 for r in dec if r["crl"])

    s = f"pdufa.bio tracks {ahead} upcoming FDA decision dates"
    if rd:
        s += f" and {len(rd)} expected clinical trial readouts"
    s += (f", alongside {len(dec)} decisions already made: {ap} approvals and {crl} Complete "
          f"Response Letters. ")
    s += ("Every date links the FDA notice or company filing it came from, and each past decision "
          "shows the share-price reaction we measured on the day.")
    return s


TARGETS = ["calendar", "decisions", "decisions/approvals", "decisions/crl", "readouts", "adcomm"]


def main():
    ap_ = argparse.ArgumentParser(); ap_.add_argument("--dry-run", action="store_true")
    a = ap_.parse_args()

    done = skipped = 0
    for rel in TARGETS:
        p = os.path.join(SITE, rel, "index.html")
        if not os.path.exists(p):
            print(f"  skip /{rel}: no page"); continue
        doc = open(p, encoding="utf-8", errors="replace").read()

        # Count from the live page, with the previous sentence stripped so a re-run cannot read
        # its own numbers back in and count them as rows.
        clean = re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S)
        rows = parse(clean)
        if not rows:
            print(f"  SKIP /{rel}: row parse found 0 rows -- refusing to publish a sentence "
                  f"containing a zero. The row markup probably changed.")
            skipped += 1
            continue

        s = sentence(rel, rows)
        if not s:
            continue

        # GSC: ~250 impressions on head "pdufa calendar/date" terms, zero clicks, position ~20.
        # The title is a label; make it a reason to click. KEYWORD-FIRST deliberately: /calendar
        # ranks #3 on Bing with the phrase at the front, so the ranking phrase keeps its position
        # and the count + cadence go after it. The count is the same row count the lede publishes,
        # so title, sentence and table cannot disagree.
        titles = {
            "calendar":  f"2026 FDA PDUFA Calendar: {len(rows)} Dates, Updated Daily | pdufa.bio",
            "decisions": f"FDA Decisions Archive: {len(rows)} Tracked, Updated Daily | pdufa.bio",
            "readouts":  f"Clinical Trial Readout Calendar: {len(rows)} Dates | pdufa.bio",
        }
        if rel in titles:
            doc = re.sub(r"(<title[^>]*>).*?(</title>)",
                         lambda m: m.group(1) + titles[rel] + m.group(2), doc, count=1, flags=re.S)
        block = (f'{B}<p style="margin:0 0 14px;font-size:14.5px;line-height:1.75;color:#cfe0f5;'
                 f'max-width:74ch">{html.escape(s)}</p>{E}')

        if B in doc:
            doc = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            # After the freshness stamp if there is one, otherwise straight after the heading.
            anchor = "<!--FRESH:END-->"
            if anchor in doc:
                i = doc.index(anchor) + len(anchor)
            elif "</h1>" in doc:
                i = doc.index("</h1>") + len("</h1>")
            else:
                print(f"  skip /{rel}: no insertion point"); continue
            doc = doc[:i] + block + doc[i:]

        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        done += 1
        print(f"  /{rel:<20} {len(rows):>4} rows counted")
        print(f"       {s[:150]}")

    # The homepage last, so it reads the numbers the other pages just published.
    hp = os.path.join(SITE, "index.html")
    s = homepage_sentence()
    if s and os.path.exists(hp):
        doc = open(hp, encoding="utf-8", errors="replace").read()
        block = (f'{B}<p style="margin:0 0 16px;font-size:15px;line-height:1.75;color:#cfe0f5;'
                 f'max-width:76ch">{html.escape(s)}</p>{E}')
        if B in doc:
            doc = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
            i = doc.index(anchor) + len(anchor)
            doc = doc[:i] + block + doc[i:]
        if not a.dry_run:
            open(hp, "w", encoding="utf-8").write(doc)
        done += 1
        print(f"  /{'':<20} homepage")
        print(f"       {s[:150]}")

    print(f"\nlede on {done} page(s), {skipped} skipped"
          + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
