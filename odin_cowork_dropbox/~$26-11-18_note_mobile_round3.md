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
  - 13: new module `phone_charts.py`, called from `apply()`. Every narrower inline SVG chart (under 700 units)
    whose smallest label a phone would draw under 11px gets a second, phone-sized drawing of the same chart
    beside it, in `<!--PH:B--><div class="pd-ph">...<svg class="pd-phs">...</svg></div><!--PH:E-->`. The phone
    drawing is 320 units wide so every label renders at 11px or more in a 290px column; labels are re-placed so
    they do not collide. CSS shows it only under 640px; desktop sees the original. 606 charts today (run-up
    charts on /pdufa, /fda-decision, /ticker pages and the studies). Same data points, same label text.
- build_sitemap.py: BOILER strips the CX and PH markers and the phone drawing, so the sweep does not move any page's lastmod.
- screener/index.html (static page): the From and To date fields may wrap on phones (they made the page 428px
  wide at every phone width).
- tests/test_mobile_layout.py: self-checks for the chart box, the phone drawing (planted run-up chart must get
  an 11px drawing, and a stripped one must be caught) and the screener date row.
- .github/workflows/pdufa-rebuild.yml: the push-retry loop now runs `git rebase --autostash origin/main`, so a
  merge landing during a run can't fail the rebase over an uncommitted generated file.

Your local chain already runs inject_mobile_polish.py before build_sitemap.py; nothing to change there,
but phone_charts.py must sit beside inject_mobile_polish.py (it is imported).
