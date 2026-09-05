# -*- coding: utf-8 -*-
"""'Positioning before the decision' block on /fda-decision pages.

Audit 2026-09-05c section 7: each historical dataset becomes one dated sentence on
the event page it belongs to. This injects the ORATS sentence -- what the options
market priced before THIS decision, and what happened -- onto every decision page
whose event is in implied_moves.json. The competitors can copy the sentence; the
number inside it comes from a 2,714-snapshot chain archive they do not have.

Discipline:
  - Idempotent, marker-bounded (<!--POSITIONING:BEGIN/END-->), safe on every rebuild.
  - The caveat travels IN the block: the priced figure is the move through the first
    expiry after the decision, not "the event-implied move".
  - Matching is exact-first (event goal date near the decision date), same-ticker
    within 45 days otherwise -- one event max, or nothing. A wrong number on a
    decision page is worse than no number.
  - No strategy verb, ever.
"""
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
SRC = os.path.join(HERE, "implied_moves.json")
MATCH_DAYS = 45


def esc(s):
    return html.escape(str(s), quote=False)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f'{["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.month]} {d.day}, {d.year}'


def build_block(e):
    a5 = e.get("actual_5d_pct")
    iv = e.get("atm_iv_pct")
    parts = [
        f"On {esc(pretty(e['snap']))}, {e['days_before']} days before the decision "
        f"date, at-the-money options priced a move of "
        f"<b>&plusmn;{e['priced_pct']:.1f}%</b> through {esc(pretty(e['expiry']))} "
        f"(the first listed expiry after the decision"
        + (f"; ATM implied volatility {iv:.0f}%" if iv else "") + "). ",
        f"The stock closed <b>{e['actual_pct']:+.1f}%</b> at the first close across "
        f"the decision"
        + (f" and <b>{a5:+.1f}%</b> five trading days on" if a5 is not None else "")
        + ". ",
        "A straddle priced weeks out covers ordinary movement plus the event, so "
        "this is the move the options market priced through that expiry, not the "
        'event-implied move alone. <a class="lit" href="/research/implied-vs-actual">'
        f"How this compares across 1,000+ decisions</a>.",
    ]
    return ("<!--POSITIONING:BEGIN-->"
            '<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
            'padding:14px 16px;margin:16px 0">'
            '<b style="color:#e3ba5e">Positioning before the decision</b>'
            '<div style="color:#9db3d4;font-size:13.5px;margin-top:6px;line-height:1.65">'
            + "".join(parts) +
            "</div></div><!--POSITIONING:END-->")


def main():
    data = json.load(io.open(SRC, encoding="utf-8"))
    by_tk = {}
    for e in data["events"]:
        by_tk.setdefault(e["t"], []).append(e)

    droot = os.path.join(SITE, "fda-decision")
    n_done = n_skip = 0
    for slug in sorted(os.listdir(droot)):
        m = re.match(r"^([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, ddate = m.group(1), dt.date.fromisoformat(m.group(2))
        cands = [(abs((dt.date.fromisoformat(e["pdufa"]) - ddate).days), e)
                 for e in by_tk.get(tk, [])]
        cands = [c for c in cands if c[0] <= MATCH_DAYS]
        if not cands:
            n_skip += 1
            continue
        cands.sort(key=lambda c: c[0])
        if len(cands) > 1 and cands[1][0] == cands[0][0]:
            n_skip += 1                     # ambiguous: two events equally near -> nothing
            continue
        e = cands[0][1]
        p = os.path.join(droot, slug, "index.html")
        t = io.open(p, encoding="utf-8", errors="replace").read()
        block = build_block(e)
        if "<!--POSITIONING:BEGIN-->" in t:
            t2 = re.sub(r"<!--POSITIONING:BEGIN-->[\s\S]*?<!--POSITIONING:END-->",
                        lambda _m: block, t)
        else:
            # after the closing of the first .note div (the chart's note) or, failing
            # that, before the Questions/FAQ heading; last resort: before </body>.
            anchor = re.search(r'<div class="note">[\s\S]*?</div>', t)
            if anchor:
                t2 = t[:anchor.end()] + block + t[anchor.end():]
            elif "<h2" in t:
                i = t.index("<h2")
                t2 = t[:i] + block + t[i:]
            else:
                t2 = t.replace("</body>", block + "</body>", 1)
        if t2 != t:
            io.open(p, "w", encoding="utf-8").write(t2)
            n_done += 1
    print(f"positioning blocks: {n_done} decision page(s) written/updated, "
          f"{n_skip} without a computable or unambiguous chain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
