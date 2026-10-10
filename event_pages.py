# -*- coding: utf-8 -*-
"""event_pages.py -- ONE owner of "which /pdufa/ page is this row's event page".

Audit 2026-10-10 items 2 and 3: a drug with two pending applications got one page (giredestrant evERA
Dec 18 resolved to the lidERA Nov 30 page; bezuclastinib SUMMIT Dec 30 to the PEAK Nov 30 page), and the
API's `url` sent 33 of 35 upcoming rows to a hub because the calendar followed the row's url and the API
followed the calendar. Three scripts answered the question three ways. Now one does:

    resolve(row) -> "/pdufa/{slug}" or None

A page is the row's event page only when it carries the row's DATE (day rows: the title names the day,
or the page's Event startDate is the day; window rows: the title names the month). A page that merely
names the drug is not enough, because that is exactly how two applications ended up sharing one page.

Order: _d.event_slug (hand-assigned) -> {TK}-{drug} -> any /pdufa/{TK}-* page naming the drug. The
first page whose date matches wins. Used by sync_event_urls.py (dataset url + calendar hrefs),
build_pdufa_event_pages.py (a second application gets its own slug), inject_event_schema.py and
tests/test_event_page_titles_carry_date.py.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUTDIR = os.path.join(SITE, "pdufa")
MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return s


def drug_of(row):
    """The drug's name without its parenthetical (trial, code, partner)."""
    n = str(row.get("name") or "")
    n = re.split(r"\s*\(|\s+-\s+", n, 1)[0].strip()
    return n


def drug_token(row):
    return re.sub(r"[^a-z0-9]", "", drug_of(row).lower())[:10]


def date_forms(row):
    """Strings a page title may use for this row's date, at the row's precision."""
    d, dp = str(row.get("d") or "")[:10], str(row.get("dp") or "day")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        return []
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    if dp == "day":
        return [f"{MON3[m]} {dd}, {y}", f"{MON3[m]} {dd} {y}", f"{MONTHS[m]} {dd}, {y}", d]
    # window rows: site_windows.window_label is the one owner of how a window is written
    # ("Nov 2026", "Q4 2026", "2026"); accept the long month form too.
    try:
        import sys
        sys.path.insert(0, HERE)
        from site_windows import window_label
        forms = [window_label(row)]
    except Exception:  # noqa: BLE001
        forms = []
    ym = str(row.get("dm") or d[:7])
    try:
        y, m = int(ym[:4]), int(ym[5:7])
        forms += [f"{MONTHS[m]} {y}", f"{MON3[m]} {y}", ym]
    except ValueError:
        pass
    return [f for f in forms if f]


def page_title(slug):
    p = os.path.join(OUTDIR, slug, "index.html")
    if not os.path.exists(p):
        return None, ""
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"<title>(.*?)</title>", doc, re.S)
    return (m.group(1) if m else ""), doc


def page_carries_date(row, doc, title):
    forms = date_forms(row)
    if not forms:
        return False
    t = re.sub(r"\s+", " ", title or "")
    if any(f in t for f in forms):
        return True
    d = str(row.get("d") or "")[:10]
    if str(row.get("dp") or "day") == "day":
        m = re.search(r'"startDate":\s*"(\d{4}-\d{2}-\d{2})', doc or "")
        if m and m.group(1) == d:
            return True
    return False


def candidate_slugs(row):
    tk = str(row.get("t") or "").upper()
    out = []
    es = (row.get("_d") or {}).get("event_slug")
    if es:
        out.append(str(es))
    base = f"{tk}-{slugify(drug_of(row))}"
    if base != f"{tk}-":
        out.append(base)
    tok = drug_token(row)
    if tk and os.path.isdir(OUTDIR):
        for name in sorted(os.listdir(OUTDIR)):
            if name.upper().startswith(tk + "-") and name not in out:
                low = name.lower().replace("-", "")
                if tok and tok in low:
                    out.append(name)
    return out


def resolve(row):
    """'/pdufa/{slug}' of the page that states THIS row's date, else None."""
    if row.get("type") != "PDUFA":
        return None
    for slug in candidate_slugs(row):
        title, doc = page_title(slug)
        if title is None:
            continue
        # a canonicalised twin (noindex, canonical -> its primary) is never the event page; follow the
        # canonical when that page states the date (NVO-cagrisema -> NVO-am833)
        rob = re.search(r'<meta name="robots" content="([^"]*)"', doc or "")
        if rob and "noindex" in rob.group(1):
            can = re.search(r'rel="canonical" href="https://www\.pdufa\.bio/pdufa/([^"/]+)"', doc or "")
            if can and can.group(1) != slug:
                t2, d2 = page_title(can.group(1))
                if t2 is not None and page_carries_date(row, d2, t2):
                    return f"/pdufa/{can.group(1)}"
            continue
        if page_carries_date(row, doc, title):
            return f"/pdufa/{slug}"
    return None


def pending_rows(rows, today_iso=None):
    """Upcoming PDUFA rows (not Decided/Withdrawn) with a parseable date, day or window."""
    out = []
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() in ("decided", "withdrawn"):
            continue
        d = str(r.get("d") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            continue
        if today_iso and str(r.get("dp") or "day") == "day" and d < today_iso:
            continue
        out.append(r)
    return out
