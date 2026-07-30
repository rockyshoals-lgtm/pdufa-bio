# -*- coding: utf-8 -*-
"""check_adcom_results.py -- flag AdComm meetings whose date has passed but whose vote result has not
been published yet. This is the AdComm twin of check_pdufa_decided.py: it does NOT auto-publish a vote
(panel outcomes need primary-source verification, same as PDUFA outcomes) -- it surfaces the pages that
need a human to verify + post the result, so an AdComm like CAPR/REPL is never silently left "scheduled".

A page counts as RESOLVED if it shows a decisive vote (e.g. "3 for ... 9 against"). Otherwise, if the
meeting date is on/before today, it is flagged.

    python check_adcom_results.py        # prints NEEDS RESULT lines (exit 0 always; advisory)
"""
import glob, os, re
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ADCOMM = os.path.join(HERE, "pdufa_site_src", "adcomm")
TODAY = dt.date.today()
VOTE = re.compile(r'(\d+)\s*(?:for|yes)\b.{0,16}?(\d+)\s*(?:against|no)\b', re.I | re.S)
DIRNAME = re.compile(r'^([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$')


def main():
    flagged = []
    for page in sorted(glob.glob(os.path.join(ADCOMM, "*", "index.html"))):
        m = DIRNAME.match(os.path.basename(os.path.dirname(page)))
        if not m:
            continue
        tk, date = m.group(1), m.group(2)
        if dt.date.fromisoformat(date) > TODAY:
            continue  # still upcoming
        html = open(page, encoding="utf-8", errors="replace").read()
        if VOTE.search(html):
            continue  # a decisive vote is already published
        flagged.append((tk, date))

    if flagged:
        print(f"*** {len(flagged)} AdComm meeting(s) PAST-DATE with NO published vote result -- "
              f"verify against the company PR / FDA and post the outcome: ***")
        for tk, date in flagged:
            print(f"  ADCOM NEEDS RESULT  {tk}  {date}  -> pdufa_site_src/adcomm/{tk}-{date}/index.html")
    else:
        print("All past AdComm meetings have a published vote result.")


if __name__ == "__main__":
    main()
