# -*- coding: utf-8 -*-
"""drug_names.py -- one owner for turning a stored drug/indication string into publishable text.

Audit 2026-10-03, items 4.7 (#65) and 2.1. The decisions archive was imported from a feed that cut
drug names at 44 characters and indications at 50 ("TRUQAP (capivasertib) in combination with ab",
"functional constipation (FC) in patients 2 to 5 ye"). The title builder then read its OWN previous
title back as the drug name, so a cut title ("Ipratropium Bromide HFA Inhala") re-cut itself every
run. Nothing downstream can recover the missing characters, so the rule is: never publish a fragment.
A cut name is shortened to its last complete unit; a cut indication is dropped, not guessed at.

    clean_drug_name("TRUQAP (capivasertib) in combination with ab")  -> "TRUQAP (capivasertib)"
    clean_drug_name("VEPPANU (vepdegestrant) - (VERITAC-2)")         -> "VEPPANU (vepdegestrant)"
    clean_indication("functional constipation (FC) in patients 2 to 5 ye") -> None
"""
import html
import re

NAME_CUT = 44          # the archive feed's drug-name width
IND_CUT = 50           # the archive feed's indication width


def _balanced(s):
    return s.count("(") == s.count(")")


def _end_of_first_group(s):
    """Index just past the first ')' at which the parentheses balance, or -1."""
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def looks_cut_name(raw):
    s = str(raw or "").strip()
    return len(s) == NAME_CUT or not _balanced(s)    # the feed cut at exactly 44; longer names are whole


def clean_drug_name(raw):
    """Publishable drug name: trial suffix removed, truncation cut back to a complete unit."""
    s = html.unescape(str(raw or "")).strip()
    while html.unescape(s) != s:
        s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).replace("™", "").replace("®", "")
    s = re.sub(r"(\s+FDA)+$", "", s)
    cut = looks_cut_name(s)
    # trial / program suffix " - (TEMPO)", "- (SUNSHINE)", " - (DESTINY-" (complete or cut)
    s = re.sub(r"\s*-\s*\(\s*[A-Za-z0-9][^()]*\)?\s*$", "", s).strip()
    # an indication suffix " - idiopathic nephrotic syndrome" (lower-case) is not part of the name
    s = re.sub(r"\s+-\s+[a-z][a-z ,'-]{6,}$", "", s).strip()
    if cut:
        if not _balanced(s):
            s = s[:s.rindex("(")].rstrip(" ,(-/")
        e = _end_of_first_group(s)
        if 0 < e < len(s):
            s = s[:e]          # text after the first complete group of a CUT name is unreliable
        elif e == -1 and len(s) >= NAME_CUT - 6:
            # no parenthetical: drop the last (possibly partial) token or clause
            if ", " in s:
                s = s[:s.rindex(", ")]
            else:
                s = s.rsplit(" ", 1)[0]
    s = s.rstrip(" ,-/.")
    while not _balanced(s) and "(" in s:
        s = s[:s.rindex("(")].rstrip(" ,(-/")
    return s


def clean_indication(raw):
    """Publishable indication, or None when the stored text is a cut fragment."""
    s = html.unescape(str(raw or "")).strip().rstrip(".").strip()
    s = re.sub(r"\s+", " ", s)
    if not s:
        return None
    if len(s) == IND_CUT and not (s.endswith(")") and _balanced(s)):
        return None
    if not _balanced(s):
        return None
    return s


def lower_first(s):
    """Indication text mid-sentence: lower-case a leading capital unless it is an acronym/proper."""
    if not s:
        return s
    w = s.split(" ", 1)[0]
    if len(w) > 1 and w[0].isupper() and w[1:].islower() and w.lower() not in {
            "parkinson's", "alzheimer's", "crohn's", "hodgkin", "huntington's", "niemann-pick",
            "duchenne", "fabry", "pompe", "gaucher", "hunter", "noonan", "alexander", "menkes", "wilson's"}:
        return w.lower() + s[len(w):]
    return s


def clean_company(raw):
    """Company as stored by the archive feed, made publishable: no cut parenthetical, no share-class tail."""
    s = html.unescape(str(raw or "")).strip()
    while not _balanced(s) and "(" in s:
        s = s[:s.rindex("(")].rstrip(" ,(-/")
    s = re.sub(r"\s+(American Depositary Shares?|ADS|Ordinary Shares?|Common Stock)\b.*$", "", s, flags=re.I)
    s = re.sub(r"\s+[A-Z]$", "", s)          # a share-class word cut to one letter ("Limited A")
    return s.strip(" ,")
