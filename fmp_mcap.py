# -*- coding: utf-8 -*-
"""fmp_mcap.py -- market capitalisation from FMP (current, or as of a date). One owner for tier thresholds.

Used by extend_runup_study.py (tier at the eve of each decision), backfill_runup_mcap_tier.py and the PDUFA row
builders. FMP_API_KEY from the environment, else Odin Perfection/.env_master locally.
"""
import datetime as dt
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def key():
    k = os.environ.get("FMP_API_KEY")
    if k:
        return k
    p = os.path.join(HERE, "Odin Perfection", ".env_master")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith("FMP_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _get(url):
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(url, timeout=25))
        except Exception:  # noqa: BLE001
            time.sleep(1 + 2 * i)
    return None


def mcap_on(ticker, date=None):
    """Market cap on `date` (ISO), or the last trading day before it within 10 days; current if date is None."""
    k = key()
    if not k:
        return None
    base = "https://financialmodelingprep.com/stable/"
    if not date:
        d = _get(f"{base}market-capitalization?symbol={ticker}&apikey={k}") or []
        return (d[0].get("marketCap") if d else None) or None
    d0 = dt.date.fromisoformat(date)
    d = _get(f"{base}historical-market-capitalization?symbol={ticker}&from={(d0 - dt.timedelta(days=10)).isoformat()}"
             f"&to={date}&apikey={k}") or []
    d = sorted((x for x in d if x.get("marketCap") and x.get("date", "") <= date), key=lambda x: x["date"])
    return d[-1]["marketCap"] if d else None


def tier_label(m):
    """The study CSV's labels."""
    if not m:
        return ""
    m = float(m)
    return ("Nano (<$50M)" if m < 50e6 else "Micro ($50M-$300M)" if m < 300e6 else "Small ($300M-$2B)"
            if m < 2e9 else "Mid ($2B-$10B)" if m < 10e9 else "Large (>$10B)")


def tier_short(m):
    """The dataset's labels."""
    t = tier_label(m)
    return t.split(" ")[0] if t else ""
