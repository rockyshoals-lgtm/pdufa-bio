# -*- coding: utf-8 -*-
"""CI guard: a republished old FDA notice never becomes a lead (audit 2026-11-11 §0a).

On Nov 10, 2026 the FDA drugs feed republished 2021-2024 oncology notices with a Nov 10, 2026 pubDate; the watcher
dated them by pubDate and held BMY and JAZZ rows. watch_fda_drugs_feed.leads_from now dates an item by its own
"On {Month D, YYYY}" sentence and drops it when that date is more than 14 days older than the feed date.

Planted: (1) the 2024 adagrasib notice with a 2026 pubDate -> no lead, listed as republished;
(2) a current notice ("On November 10, 2026") naming the same tracked drug -> one lead, dated Nov 10;
(3) an item with no "On" sentence keeps its pubDate (the 09-25 replay behaviour).
"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

ROWS = [{"id": "pdufa_bmy_2027-05-13", "t": "BMY", "d": "2027-05-13", "type": "PDUFA", "st": "Upcoming",
         "name": "adagrasib - KRAS G12C colorectal cancer", "_d": {}}]


def item(title, desc, pub):
    return (f"<item><title>{title}</title><link>https://www.fda.gov/x/{abs(hash(title))}</link>"
            f"<description>{desc}</description><pubDate>{pub}</pubDate></item>")


def main():
    import watch_fda_drugs_feed as F
    old = item("FDA grants accelerated approval to adagrasib with cetuximab for KRAS G12C-mutated colorectal cancer",
               "On June 21, 2024, the Food and Drug Administration granted accelerated approval to adagrasib with "
               "cetuximab.", "Tue, 10 Nov 2026 12:07:58 EST")
    new = item("FDA approves adagrasib for a new indication",
               "On November 10, 2026, the Food and Drug Administration approved adagrasib for a new indication.",
               "Tue, 10 Nov 2026 14:58:07 EST")
    plain = item("FDA Approves adagrasib combination", "The FDA today approved adagrasib in combination.",
                 "Mon, 09 Nov 2026 17:15:46 EST")
    fails = []
    leads, _ = F.leads_from(f"<rss><channel>{old}</channel></rss>", ROWS)
    if leads:
        fails.append("the republished 2024 notice raised a lead")
    if not F.STALE or F.STALE[0][1] != dt.date(2024, 6, 21):
        fails.append("the republished notice was not reported with its own date (2024-06-21)")
    leads, _ = F.leads_from(f"<rss><channel>{new}</channel></rss>", ROWS)
    if len(leads) != 1 or leads[0][2]["date"] != dt.date(2026, 11, 10):
        fails.append(f"the current notice should raise one lead dated 2026-11-10, got {[(l[2]['date']) for l in leads]}")
    leads, _ = F.leads_from(f"<rss><channel>{plain}</channel></rss>", ROWS)
    if len(leads) != 1 or leads[0][2]["date"] != dt.date(2026, 11, 9):
        fails.append("an item without an 'On' sentence should keep its pubDate and still raise its lead")
    if fails:
        print("FAIL: FDA feed own-date guard:")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- republished 2024 notice raises nothing (own date 2024-06-21); current notice raises one lead dated "
          "2026-11-10; an item without an 'On' sentence keeps its pubDate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
