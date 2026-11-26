"""announced_day.py -- the day a decision page says the sponsor announced, from its own "Announced" key fact.

2026-11-26 (held-page red team): a page's slug is the first US trading day on or after the public news, so an
after-close or weekend announcement keys to a later day. Generated sentences used the slug as the announcement
day: GSK-2025-02-18 said "The sponsor announced it on February 18, 2025" when GSK announced Penmenvy on Saturday
February 15, and AXGN-2025-12-04 said December 4 for a December 3 after-close release. Every sentence that names
the announcement day reads it here; with no such key fact the slug day stands, as before.
"""
import re

_KV = re.compile(r'<span>Announced</span><b>\s*(\d{4}-\d{2}-\d{2})([^<]*)</b>')


def announced_iso(doc, slug_day):
    """The ISO announcement day the page states, else the slug day."""
    m = _KV.search(doc or "")
    return m.group(1) if m else slug_day


def after_close(doc):
    """True when the page says the announcement came after the close (so the slug is the next trading day)."""
    m = _KV.search(doc or "")
    return bool(m and re.search(r"after the close", m.group(2), re.I))
