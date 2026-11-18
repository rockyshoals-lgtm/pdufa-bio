# Note for the pdufa builder: mobile round 3 (2026-11-18)

From the mobile/UX thread. Layout only; no fact, number, date, link target or text changed.

Live test at 320, 375 and 414px (24 pages, real browser) found three pages wider than the phone and charts
with labels about 3px tall. Changes:

- inject_mobile_polish.py
  - 11: `.grid>*{min-width:0}` on phones. A long company name made every /tickers row 403px wide on a 320px
    phone; /readouts rows were 339px.
  - 12: `wrap_charts()`: an inline SVG chart at least 700 units wide whose smallest label would draw under 10px
    in a 330px column is wrapped in `<!--CX:B--><div class="pd-cx" style="--cxw:NNNpx">...</div><!--CX:E-->`
    and drawn on phones at the width that makes its smallest label 11px (sideways scroll). Today: /calendar,
    /readouts, /sls, /research/sls-deep-dive. Idempotent; wider screens unchanged.
- build_sitemap.py: BOILER strips the CX markers, so the sweep does not move any page's lastmod.
- screener/index.html (static page): the From and To date fields may wrap on phones (they made the page 428px
  wide at every phone width).
- tests/test_mobile_layout.py: self-checks for the chart box and the screener date row.

Your local chain already runs inject_mobile_polish.py before build_sitemap.py; nothing to change there.
