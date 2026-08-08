#!/usr/bin/env python3
"""
Phase 2 Stage 1 — Build the list of FINRA biweekly short-interest settlement dates
for the 2015-01-01 → 2026-04-15 window.

Business rule (FINRA):
  Two settlement dates per month:
    - 15th of the month (or prior business day if 15th falls on weekend/holiday)
    - last business day of the month
  Published ~8 business days after settlement date.

We construct the THEORETICAL settlement dates (business-day-adjusted).
The actual FINRA publication lag is not our concern for T-1 compliance —
only the settlement date matters for feature snapshotting.

Output:
  si_settlement_dates.json  — list of ISO settlement dates
"""
import json
from pathlib import Path
from datetime import datetime, timedelta, date
import calendar

BASE = Path('/sessions/confident-serene-ptolemy/mnt/9realms')
OUT = BASE / 'si_settlement_dates.json'

# US federal holidays 2015-2026 (approximate — good enough for business-day
# adjustment of short-interest settlement dates).
HOLIDAYS = {
    # 2015
    '2015-01-01','2015-01-19','2015-02-16','2015-05-25','2015-07-03',
    '2015-09-07','2015-10-12','2015-11-11','2015-11-26','2015-12-25',
    # 2016
    '2016-01-01','2016-01-18','2016-02-15','2016-05-30','2016-07-04',
    '2016-09-05','2016-10-10','2016-11-11','2016-11-24','2016-12-26',
    # 2017
    '2017-01-02','2017-01-16','2017-02-20','2017-05-29','2017-07-04',
    '2017-09-04','2017-10-09','2017-11-10','2017-11-23','2017-12-25',
    # 2018
    '2018-01-01','2018-01-15','2018-02-19','2018-05-28','2018-07-04',
    '2018-09-03','2018-10-08','2018-11-12','2018-11-22','2018-12-25',
    # 2019
    '2019-01-01','2019-01-21','2019-02-18','2019-05-27','2019-07-04',
    '2019-09-02','2019-10-14','2019-11-11','2019-11-28','2019-12-25',
    # 2020
    '2020-01-01','2020-01-20','2020-02-17','2020-05-25','2020-07-03',
    '2020-09-07','2020-10-12','2020-11-11','2020-11-26','2020-12-25',
    # 2021
    '2021-01-01','2021-01-18','2021-02-15','2021-05-31','2021-07-05',
    '2021-09-06','2021-10-11','2021-11-11','2021-11-25','2021-12-24',
    # 2022
    '2022-01-17','2022-02-21','2022-05-30','2022-06-20','2022-07-04',
    '2022-09-05','2022-10-10','2022-11-11','2022-11-24','2022-12-26',
    # 2023
    '2023-01-02','2023-01-16','2023-02-20','2023-05-29','2023-06-19',
    '2023-07-04','2023-09-04','2023-10-09','2023-11-10','2023-11-23','2023-12-25',
    # 2024
    '2024-01-01','2024-01-15','2024-02-19','2024-05-27','2024-06-19',
    '2024-07-04','2024-09-02','2024-10-14','2024-11-11','2024-11-28','2024-12-25',
    # 2025
    '2025-01-01','2025-01-20','2025-02-17','2025-05-26','2025-06-19',
    '2025-07-04','2025-09-01','2025-10-13','2025-11-11','2025-11-27','2025-12-25',
    # 2026
    '2026-01-01','2026-01-19','2026-02-16','2026-05-25','2026-06-19','2026-07-03',
}


def is_business_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    if d.strftime('%Y-%m-%d') in HOLIDAYS:
        return False
    return True


def prev_business_day(d: date) -> date:
    while not is_business_day(d):
        d = d - timedelta(days=1)
    return d


def last_business_day_of_month(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    return prev_business_day(d)


def mid_month_settlement(year: int, month: int) -> date:
    """15th of month, rolled back to prior business day if needed."""
    d = date(year, month, 15)
    return prev_business_day(d)


def main():
    dates = []
    for year in range(2015, 2027):
        month_limit = 13 if year < 2026 else 5  # 2026 stops at April
        for month in range(1, month_limit):
            mid = mid_month_settlement(year, month)
            end = last_business_day_of_month(year, month)
            dates.append(mid.strftime('%Y-%m-%d'))
            dates.append(end.strftime('%Y-%m-%d'))

    dates = sorted(set(dates))
    out = {
        'n_dates': len(dates),
        'start': dates[0],
        'end': dates[-1],
        'dates': dates,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'[+] Wrote {OUT}')
    print(f'    {len(dates)} biweekly settlement dates from {dates[0]} to {dates[-1]}')
    print(f'    First 5: {dates[:5]}')
    print(f'    Last  5: {dates[-5:]}')


if __name__ == '__main__':
    main()
