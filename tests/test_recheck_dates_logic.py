# -*- coding: utf-8 -*-
"""CI guard: the automatic date re-check only confirms what its sources agree with.

recheck_upcoming_dates.py writes CONFIRMED entries into _date_checks.json on every rebuild, which is what
keeps tests/test_date_checks_current.py from blocking. If its logic drifted (a moved date read as a match,
an FDA action ignored, a non-SEC filer confirmed with nothing read), the ledger would vouch for dates
nobody checked. This runs its offline self-test: unchanged or restated dates confirm; a moved date, an FDA
action, an unreadable source with nothing newer, and a company whose filings could not be searched all go
to a human.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import recheck_upcoming_dates as R  # noqa: E402

if __name__ == "__main__":
    if not R.self_test():
        sys.exit(1)
    print("OK -- date re-check confirms only agreeing sources; moved dates, FDA actions and unsearchable "
          "companies go to a human.")
