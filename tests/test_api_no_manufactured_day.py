# -*- coding: utf-8 -*-
"""The public API must not serve a day the sponsor never gave.

Audit 2026-09-09b item 3, approved by David 2026-09-09. `date` used to carry a month
MIDPOINT whenever date_precision was not 'day': 263 of 456 rows served the 15th and 62 more
served the 30th or 31st. 71% of the endpoint /developers advertises carried a manufactured
day, on a site whose whole position is that every date is sourced. A source comment telling
consumers not to read it as a day protects nobody's parser.

Contract, asserted on the SHAPING CODE rather than a sample response, because the shape is
what every consumer gets:
  1. `_lib.mjs` gates `date` on date_precision === 'day';
  2. `date_month` is populated for rows without a day;
  3. `days_to_decision` is not computed when there is no day;
  4. /developers documents the rule (the breaking change has to be findable).

Proved 0 -> 1 -> 0 on 2026-09-09 by restoring `date: e.d || null`.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
LIB = os.path.join(SITE, "api", "v1", "_lib.mjs")
DEV = os.path.join(SITE, "developers", "index.html")


def test_api_date_is_a_day_or_null():
    src = io.open(LIB, encoding="utf-8", errors="replace").read()
    code = "\n".join(ln.split("//", 1)[0] for ln in re.sub(r"/\*.*?\*/", "", src, flags=re.S)
                     .splitlines())

    m = re.search(r"\bdate:\s*([^,\n]+)", code)
    assert m, "_lib.mjs no longer sets a `date` field -- guard cannot see"
    expr = m.group(1)
    assert "dp" in expr and "day" in expr, (
        "the API serves `date` ungated by date_precision, so month/quarter rows publish a "
        f"manufactured day again (the 263-rows-on-the-15th class): date: {expr.strip()}")

    assert re.search(r"date_month:\s*e\.dm", code), \
        "date_month must carry the real granularity when `date` is null"

    assert re.search(r"days_to_decision\s*=\s*null", code), \
        "days_to_decision must be null when there is no announced day"

    doc = io.open(DEV, encoding="utf-8", errors="replace").read()
    assert "date_month" in doc and re.search(r"null", doc), \
        "/developers must document the date rule; a breaking change has to be findable"


if __name__ == "__main__":
    test_api_date_is_a_day_or_null()
    print("OK")
