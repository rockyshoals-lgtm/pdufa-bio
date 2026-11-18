# Note for the pdufa builder: phone layout round 2 (2026-11-18)

From the mobile red-team thread. Already merged on main via PR; this is so your local copies match.

- inject_mobile_polish.py now also: colours links no rule colours with the site blue (`:where(a)`, zero specificity),
  and adds a "Jump to upcoming dates" link under the /calendar lede pointing at the first month with an open goal
  date (`<!--JUMP:...-->` markers). Still idempotent; build_sitemap.py strips both, so lastmod does not move.
- fix_decisions_order.py: the row regex now accepts tickers with digits or a dot (`[A-Z0-9.]{1,8}`). The header
  regex fix from the date thread (separator up to 12 chars) is kept as is.
- tests/test_mobile_layout.py adds: no CSS text under 10px, /decisions newest-first per year, screener filters are
  buttons and keep their date on phones.
- Hand edits (no builder writes this markup): /screener filters and date range, /research/conference-runup chart
  frame, homepage countdown labels 8-9px -> 10.5px. If you regenerate any of those pages from a template, carry
  the change into the template or the guard will say so.
- /_qa/phones.html is a temporary test page (noindex, out of the sitemap); it is removed in a follow-up PR.

Layout only: no fact, number, date or link target changes.
