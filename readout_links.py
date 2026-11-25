# -*- coding: utf-8 -*-
"""readout_links.py -- the pdufa.bio pages a readout row links to: its drug page and its company's PDUFA page.

David 2026-11-25: link the readout dates to the rest of the site. A readout row on /readouts linked only to its
ticker; the drug page (/drug/<slug>, built by build_drug_pages.py from the same dataset row) and the company's
PDUFA-history page (/pdufa/<TICKER>) were one search away. This resolves both, and only ever returns a page that
exists on disk at the time it is asked, so a link it hands out is never dead in the build that writes it.

The drug slug is derived exactly as build_drug_pages.py derives it (clean_name + slugify of the name before any
parenthetical, then the generic in the parenthetical when the brand has no page, then _drug_slug_folds.json),
so the link lands on the page that row produced, never on a same-word page guessed from the program text.

    from readout_links import drug_page, pdufa_page
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

try:
    from build_drug_pages import clean_name, slugify, JUNK_SLUG
except Exception:  # pragma: no cover - the builder is in the repo; without it we link nothing
    clean_name = slugify = JUNK_SLUG = None

_FOLDS = None


def _folds():
    global _FOLDS
    if _FOLDS is None:
        try:
            _FOLDS = json.load(open(os.path.join(HERE, "_drug_slug_folds.json"), encoding="utf-8")).get("folds", {})
        except Exception:
            _FOLDS = {}
    return _FOLDS


def _page(*parts):
    return os.path.isfile(os.path.join(SITE, *parts, "index.html"))


def drug_page(row):
    """'/drug/<slug>' for this dataset row's drug page, or None when there is no such page."""
    if clean_name is None:
        return None
    name = clean_name(row.get("name"))
    if not name:
        return None
    slug = slugify(re.split(r"\s*\(", name)[0])
    cands = [slug] if slug else []
    mg = re.search(r"\(([a-z][a-z0-9-]{4,40})\)\s*$", name)
    if mg:
        cands.append(slugify(re.sub(r"-[a-z]{4}$", "", mg.group(1))))
    tk = str(row.get("t") or "").strip().upper()
    for s in cands:
        s = _folds().get(s, s)
        if not s or (JUNK_SLUG and JUNK_SLUG.search(s)):
            continue
        # A row named "mitapivat RISE ..." produced /drug/mitapivat-rise; when the plain drug page
        # (/drug/mitapivat) exists for the SAME company, that is the page a reader wants. Shortest such
        # prefix wins; the company check stops a shared first word landing on another company's drug.
        parts = s.split("-")
        for i in range(1, len(parts)):
            pre = "-".join(parts[:i])
            if len(pre) >= 4 and _page("drug", pre) and _mentions(pre, tk):
                return f"/drug/{pre}"
        if _page("drug", s):
            return f"/drug/{s}"
    return None


def _mentions(slug, tk):
    if not tk:
        return False
    try:
        return f'href="/ticker/{tk}"' in open(os.path.join(SITE, "drug", slug, "index.html"),
                                              encoding="utf-8", errors="replace").read()
    except OSError:
        return False


def pdufa_page(ticker):
    """'/pdufa/<TICKER>' when the company's PDUFA-history page exists, else None."""
    tk = str(ticker or "").strip().upper()
    if tk and re.fullmatch(r"[A-Z0-9.]{1,8}", tk) and _page("pdufa", tk):
        return f"/pdufa/{tk}"
    return None


def drug_title(url):
    """The drug page's own <h1> name (before any parenthetical), for link text; None when unreadable."""
    m = re.fullmatch(r"/drug/([a-z0-9-]+)", str(url or ""))
    if not m:
        return None
    try:
        doc = open(os.path.join(SITE, "drug", m.group(1), "index.html"), encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    h = re.search(r"<h1[^>]*>([^<]+)", doc)
    if not h:
        return None
    import html as _h
    return re.split(r"\s*\(", _h.unescape(h.group(1)).strip())[0].strip() or None
