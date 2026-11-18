# Note for the pdufa builder: new site-wide step, inject_mobile_polish.py (2026-11-18)

From the mobile red team (David, 2026-11-17: "ensure that the site works on all mobile devices and maintains immaculate UX").

What changed in the chain:
- `_chain_0919.bat` now runs `inject_mobile_polish.py` right before `build_sitemap.py --no-state`.
- `.github/workflows/pdufa-rebuild.yml` runs it before the final sitemap step too.
- `tests/test_mobile_layout.py` fails the build if a page is not at its mobile-polish state. Fix: `python inject_mobile_polish.py`.

What it does (layout only; no fact, number, date, link or text changes):
- adds `<style id="mobilepolish">` before `</head>` on every public page;
- wraps any `<table>` with no scrolling parent in `<!--TW:B--><div class="pd-tw">...</div><!--TW:E-->`;
- hides the closed phone menu (no stray line or shadow, links not tabbable);
- 16px form fields on phones (no iPhone zoom-on-focus), notch padding, anchor offset, row spacing.

`build_sitemap.py` strips both the style block and the wrappers before hashing, so the sweep does not move lastmod.
It is idempotent: a second run changes 0 pages. If a builder writes a new page with a bare table, the next chain run wraps it.
