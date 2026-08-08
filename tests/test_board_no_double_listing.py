# -*- coding: utf-8 -*-
"""test_board_no_double_listing.py -- a catalyst cannot be both pending and decided.

Replimune appeared twice on the homepage at once: under "Next FDA decisions" reading "0 due", and
under "Recently decided" reading "Approved". Same screen, same company, contradicting itself.

The cause is worth naming because it keeps recurring in different code. The board excluded decided
catalysts by matching (ticker, date), where the slate holds the PDUFA GOAL date and the archive
holds the ACTUAL decision date. Those coincide only when the FDA acts exactly on its goal day.
REPL's goal was 2026-08-02 and the approval landed 2026-08-06, so the keys never matched. Moderna
was excluded correctly the same week purely because the FDA happened to act on its goal date, which
is what made the bug look like it worked.

Goal date is not decision date. Any code that assumes it is will be right most of the time and
wrong exactly when something interesting has happened.

    python tests/test_board_no_double_listing.py
"""
import os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.join(HERE, "pdufa_site_src", "index.html")


def tickers_in(segment):
    """Tickers named in a board section, read from the links each tile carries.

    The two sections link differently: upcoming tiles point at /pdufa/<T> or /ticker/<T>, decided
    tiles at /fda-decision/<T>-<date>. The first version of this only knew the former, so it read
    the decided section as empty and passed happily while REPL was sitting in both. A guard that
    cannot see one side of the comparison is worse than no guard, because it reports safety.
    """
    out = {m.group(1) for m in re.finditer(r'href="/(?:pdufa|ticker)/([A-Z]{1,6})"', segment)}
    out |= {m.group(1) for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-\d{4}-\d{2}-\d{2}"',
                                            segment)}
    return out


def main():
    if not os.path.exists(HOME):
        print("FAIL: homepage not found")
        sys.exit(1)

    html = open(HOME, encoding="utf-8", errors="replace").read()

    i_up = html.find('<div class="list">')
    i_dec = html.find('<div class="decs">')
    if i_up == -1 or i_dec == -1:
        print("SKIP: homepage board markers not present")
        sys.exit(0)

    upcoming = html[i_up:i_dec] if i_up < i_dec else html[i_up:]
    decided = html[i_dec:i_up] if i_dec < i_up else html[i_dec:i_dec + 20000]

    up, dec = tickers_in(upcoming), tickers_in(decided)
    both = sorted(up & dec)

    print(f"homepage board: {len(up)} upcoming, {len(dec)} recently decided")

    ok = True
    if both:
        ok = False
        print(f"\nFAIL: {len(both)} ticker(s) listed as BOTH pending and decided: {', '.join(both)}")
        print("   The board excludes decided catalysts by matching the slate's goal date against "
              "the archive's decision date. They differ whenever the FDA acts early or late, which "
              "is exactly when the row matters. Match by ticker over a window instead.")
    else:
        print("  PASS: no ticker appears in both sections")

    # A countdown that has gone negative means a past-dated catalyst is still being presented as
    # forthcoming, which is the same failure one step earlier.
    neg = re.findall(r"<b>(-\d+)</b>", upcoming)
    if neg:
        ok = False
        print(f"\nFAIL: {len(neg)} upcoming tile(s) show a negative countdown: {neg[:6]}")
        print("   A PDUFA whose date has passed is awaiting an outcome, not upcoming.")
    else:
        print("  PASS: no negative countdown in the upcoming board")

    print("\n  PASS: the board is internally consistent" if ok else "\n  see failures above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
