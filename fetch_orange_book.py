# -*- coding: utf-8 -*-
"""fetch_orange_book.py -- refresh _orange_book/ from the FDA's Orange Book data files zip (audit 4.3).

The FDA publishes the Orange Book as one zip (exclusivity.txt, patent.txt, products.txt), updated monthly:
https://www.fda.gov/media/76860/download . The copy in the repo was from 2026-09-01. This downloads the zip
at most every 7 days, extracts the three files and records the FDA's file date (the zip member timestamp)
in _orange_book/_as_of.txt, which /patent-cliff/exclusivity prints. A failed download keeps the last copy.

    python fetch_orange_book.py [--force]
"""
import datetime as dt
import io
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OB = os.path.join(HERE, "_orange_book")
URL = "https://www.fda.gov/media/76860/download"


def main():
    asof_p = os.path.join(OB, "_as_of.txt")
    if "--force" not in sys.argv and os.path.exists(asof_p):
        checked = io.open(asof_p, encoding="utf-8").read().split()
        if len(checked) > 1 and (dt.date.today() - dt.date.fromisoformat(checked[1])).days < 7:
            print(f"orange book: files of {checked[0]}, checked {checked[1]}; next check within 7 days")
            return 0
    try:
        data = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}),
                                      timeout=90).read()
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception as e:  # noqa: BLE001
        print(f"orange book: download failed ({e}); keeping the copy in _orange_book/")
        return 0
    names = {n.lower(): n for n in z.namelist()}
    need = ["exclusivity.txt", "patent.txt", "products.txt"]
    if not all(n in names for n in need):
        print(f"orange book: zip lacks {need}; keeping the copy")
        return 0
    os.makedirs(OB, exist_ok=True)
    stamp = max(dt.date(*z.getinfo(names[n]).date_time[:3]) for n in need)
    for n in need:
        io.open(os.path.join(OB, n), "wb").write(z.read(names[n]))
    io.open(asof_p, "w", encoding="utf-8").write(f"{stamp.isoformat()} {dt.date.today().isoformat()}\n")
    print(f"orange book: refreshed, FDA files dated {stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
