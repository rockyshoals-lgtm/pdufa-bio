# -*- coding: utf-8 -*-
"""whole_decision_names.py -- a decided row names its drug whole, on every page that lists decisions.

UX pass 2026-11-20. /decisions, /decisions/crl, /decisions/2026, /decisions/approvals, the CRL month pages and the
"related" lists on decision pages carried names an old build cut at a fixed width: "CTx-1301 (fixed dose, pediatri",
"LNTH-2501 (Gallium-68 edotreot", "ZYNYZ (retifanlimab-dlwr) - (P", "EBGLYSS (lebrikizumab-lbkz) -",
"Romidepsin injection solution,". shape_calendar.whole_names() fixed the same rows on /calendar on 2026-11-18; this
does it everywhere else, with the same source of truth: the decision page's own name (its <title>).

A row's name changes only when it is visibly cut:
  * it is a prefix of the page's name that stops mid-word or inside a bracket  -> the page's name;
  * it opens a bracket it never closes, or ends on a dangling dash or comma, and its first word is the page's
    first word                                                                    -> the page's name;
  * otherwise a dangling dash or comma is dropped, and an unclosed bracket is cut back to the last whole part and
    marked with an ellipsis, which says so.
Nothing is inferred: a name is either the page's own or the row's own, shortened. Idempotent.

    python whole_decision_names.py [--dry-run]
"""
import argparse
import glob
import html as H
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shape_calendar import SITE, page_name  # noqa: E402

# One decided row: "<a class="row" ... href="/fda-decision/SLUG"><div class="t">...</div><div class="d"><span>CRL</span>:
# NAME[<!--PV:B-->badge<!--PV:E-->]</div></a>". Every part is held inside one row (no match may run into the next).
ROW = re.compile(r'(<a class="row"[^>]*\bhref="/fda-decision/([A-Za-z0-9.\-]+)"[^>]*><div class="t">'
                 r'(?:(?!</a>|<a ).)*?</div><div class="d"><span[^>]*>(?:Approved|CRL)</span>: )'
                 r'([^<]*)'
                 r'((?:<!--PV:B-->(?:(?!</a>|<a ).)*?<!--PV:E-->)?</div></a>)', re.S)
DANGLING = re.compile(r"(?:\s+[-–—]|\s*[,;:])\s*$")


def _first(s):
    m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9\-]*)", s)
    return m.group(1).lower() if m else ""


def _top_split(t):
    """t split at its first ": " outside brackets ("Drug (a: b): indication" -> "Drug (a: b)", "indication")."""
    depth = 0
    for k, ch in enumerate(t):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ":" and depth == 0 and t[k + 1:k + 2] == " ":
            return t[:k], ": ", t[k + 2:]
    return t, "", ""


def _unclosed_at(t):
    """Index of the first "(" that is never closed, else -1."""
    stack = []
    for k, ch in enumerate(t):
        if ch == "(":
            stack.append(k)
        elif ch == ")" and stack:
            stack.pop()
    return stack[0] if stack else -1


def whole(text, names):
    """The row's name as it should read; `text` is plain (unescaped), `names` the decision page's own names (its
    "Drug / candidate" fact, then its <title> name). A row that reads "Drug: indication" is judged on its drug alone;
    a cut indication keeps its own ellipsis, which already says so."""
    if isinstance(names, str):
        names = [names]
    # a name is usable only when it is itself whole, or marks its own cut with an ellipsis (a page's "Drug /
    # candidate" fact can itself be cut: "RP1 (vusolimogene oderparepvec) and OPDIVO (")
    names = [n for n in names if n and (n.endswith("\u2026") or (_unclosed_at(n) < 0 and not DANGLING.search(n)))]
    t = re.sub(r"^[,;:]\s*", "", text.strip())
    drug, sep, rest = _top_split(t)
    if sep and drug:
        return _whole(drug, names) + sep + rest
    return _whole(t, names)


def _whole(t, names):
    if t.endswith("\u2026"):            # already marked as shortened: leave it (idempotent)
        return t
    stem = t.rstrip(" ,;:")
    unclosed = _unclosed_at(stem) >= 0
    dangling = bool(DANGLING.search(t))
    for name in names:      # a cut-off prefix of the page's own name: the longest name it begins
        if len(name) > len(stem) >= 6 and name.startswith(stem) and (name[len(stem)].isalnum() or unclosed):
            return name
    if (unclosed or dangling) and _first(t):
        for name in names[::-1]:          # the <title> name first: it is whole, the fact may carry its own ellipsis
            if _first(t) == _first(name) and _unclosed_at(name) < 0 and not name.endswith("\u2026"):
                return name
    while DANGLING.search(t):
        t = DANGLING.sub("", t)
    cut = _unclosed_at(t)
    if cut >= 0:
        t = re.sub(r"(?:\s+[-\u2013\u2014]|\s*[,;:])?\s*$", "", t[:cut]).rstrip() + "\u2026"
    return t


KV = re.compile(r'<div class="kv"><span>Drug / candidate</span><b>([^<]{1,200})</b>')
_kv = {}


def page_names(slug):
    """[the page's "Drug / candidate" fact, its <title> name]."""
    if slug not in _kv:
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        m = KV.search(io.open(p, encoding="utf-8", errors="replace").read()) if os.path.exists(p) else None
        _kv[slug] = H.unescape(m.group(1)).strip() if m else ""
    return [_kv[slug], page_name(slug)]


def fix(doc):
    n = 0

    def sub(m):
        nonlocal n
        head, slug, body, tail = m.groups()
        if not body.strip():
            return m.group(0)
        old = H.unescape(body)
        new = whole(old, page_names(slug))
        if new == old.strip() and body == body.strip():
            return m.group(0)
        n += 1
        return head + H.escape(new, quote=False) + tail
    return ROW.sub(sub, doc), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pages = rows = 0
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "/fda-decision/" not in doc:
            continue
        new, n = fix(doc)
        if n and new != doc:
            pages += 1
            rows += n
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"whole decision names: {rows} row(s) on {pages} page(s) {'would be ' if a.dry_run else ''}made whole")
    return 0


if __name__ == "__main__":
    sys.exit(main())
