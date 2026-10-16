# -*- coding: utf-8 -*-
"""mark_calendar_period_rows.py -- month- and quarter-dated calendar rows learn their decisions (2026-10-16).

mark_calendar_decided.py only reads rows that carry a DAY ("ABBV · 2026-12-31"). Rows dated to a month or quarter
("ABBV · Dec 2026", "PFE · Q4 2026 (est.)") were never checked, so on 2026-10-16 /calendar still listed three
approvals as pending: Tavapadon (JUVMO, approved 2026-09-28), Kerendia in type 1 diabetes (2026-09-16) and Tukysa
HER2CLIMB-05 (2026-10-07).

A period row is marked only when a decision in the /decisions archive (same ticker, any ticker in the label):
  * names the same drug: a drug-name word (the part before ':' or ' - ') is shared, AND
  * names the same use: an indication word is shared, or the row states no indication; AND
  * falls inside the period or up to 180 days before its end (the same early bound as mark_calendar_decided).
The indication test is what keeps "Gazyva: Systemic Lupus Erythematosus" from taking the Gazyva idiopathic nephrotic
syndrome approval. When several decisions qualify, the latest wins. Idempotent; --dry-run prints what it would do.
"""
import argparse
import datetime as dt
import glob
import html as H
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mark_calendar_decided as M  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
MON = {m: i for i, m in enumerate(["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
STOP = {"with", "plus", "and", "the", "for", "approved", "injection", "tablets", "oral", "therapy", "combination",
        "patients", "adults", "disease", "treatment", "outcomes", "resubmission", "label", "update", "expanded"}
ROWP = re.compile(r'<a class="row"(?![^>]*data-dec)([^>]*)>\s*<div class="t">' + M.TKLABEL + r'\s*' + M.SEP +
                  r'\s*((?:[A-Z][a-z]{2}|Q[1-4]|H[12]) (\d{4}))(\s*\(est\.\))?\s*</div>\s*<div class="d">(.*?)</div>\s*</a>',
                  re.S)


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", H.unescape(str(s or "")).lower()) if w not in STOP}


def period_end(p, year):
    y = int(year)
    head = p.split()[0]
    if head in MON:
        m = MON[head]
        return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
    if head.startswith("Q"):
        m = int(head[1]) * 3
        return dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
    return dt.date(y, 6, 30) if head == "H1" else dt.date(y, 12, 31)


def split_drug(text):
    t = H.unescape(re.sub(r"<[^>]+>", " ", text))
    parts = re.split(r"\s*:\s+|\s+-\s+", t, 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def page_indication(tk, date):
    p = os.path.join(SITE, "fda-decision", f"{tk}-{date}", "index.html")
    if not os.path.exists(p):
        return ""
    m = re.search(r"<span>Indication</span><b>(.*?)</b>", io.open(p, encoding="utf-8", errors="replace").read(), re.S)
    return H.unescape(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""


def find(by_tk, label, body, end):
    dname, dind = split_drug(body)
    dn = toks(re.sub(r"\([A-Z0-9 -]+\)", " ", dname)) or toks(dname)   # drop a trial tag like (TEMPO)
    di = toks(dind)
    hits = []
    for tk in [x.strip() for x in label.split("/")]:
        for date, outcome, drugtext in by_tk.get(tk, []):
            dd = dt.date.fromisoformat(date)
            # inside the period, or before its end by no more than the early bound plus the period's own span
            if not (end - dt.timedelta(days=M.EARLY_WINDOW + 92) <= dd <= end) or outcome == "crl":
                continue
            if not (dn & toks(drugtext)):
                continue
            hits.append((date, outcome, tk, toks(page_indication(tk, date)) | toks(split_drug(drugtext)[1])))
    if di:
        # the row states a use: the decision must state an overlapping one (no stated use = no evidence)
        hits = [h for h in hits if h[3] & di]
    elif len({h[0] for h in hits}) > 1:
        return None                      # no use on the row and more than one candidate: a human decides
    if not hits:
        return None
    best = max(hits)
    return best[0], best[1], best[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    by_tk = M.load_decisions()
    pages = [os.path.join(SITE, "calendar", "index.html")] + sorted(glob.glob(os.path.join(SITE, "calendar", "2026", "*", "index.html")))
    total = 0
    for p in pages:
        doc = io.open(p, encoding="utf-8").read()
        n = [0]

        def repl(m):
            attrs, label, period, year, est, body = m.groups()
            hit = find(by_tk, label, body, period_end(period, year))
            if not hit:
                return m.group(0)
            date, outcome, tk = hit
            n[0] += 1
            print(f"  {'WOULD MARK' if a.dry_run else 'MARKED'} {os.path.relpath(p, SITE)}: {label} {period}"
                  f"{est or ''} '{H.unescape(re.sub(r'<[^>]+>', ' ', body))[:50]}' -> /fda-decision/{tk}-{date}")
            body_now = M.strip_marker(body)
            return (f'<a class="row" data-dec="1" href="/fda-decision/{tk}-{date}"><div class="t">{label} &middot; '
                    f'{period}{est or ""} <span style="color:{M.GREEN};font-weight:700">✓</span></div>'
                    f'<div class="d"><span style="color:{M.GREEN};font-weight:700">Approved</span>: {body_now}</div></a>')

        new = ROWP.sub(repl, doc)
        if n[0] and not a.dry_run:
            io.open(p, "w", encoding="utf-8").write(new)
        total += n[0]
    print(f"period rows {'to mark' if a.dry_run else 'marked'}: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
