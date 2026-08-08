# P1-3 — Ticker hubs shipped 2026-07-18

The backlog's ⭐ "biggest SEO item left." Built, verified, deployed, confirmed live.

## What shipped
**210 `/ticker/{TICKER}` hub pages** — one per company we hold any FDA event for
(52 with both upcoming + past, 17 upcoming-only, 141 history-only). Each aggregates:
- **Upcoming FDA catalysts** — driven by the CURRENT slate (api/data.js), linked to the matching
  /pdufa detail page by drug token, else to /calendar.
- **FDA decision history** — every /fda-decision/{TICKER}-{date} page, newest first, with an
  Approved/CRL badge.
- Cross-links to /calendar, /decisions, /readouts + the standard chrome, footer, disclaimers.

Generator: `build_ticker_hubs.py` (idempotent, `--dry-run`). Sitemap: 336 → **546 URLs**.

## Why it's the lever
pdufa.bio won't out-authority BiopharmaWatch/BPIQ on the head term this year; the tail is the
winnable path. These are ~210 near-zero-competition pages ("MNKD catalysts", "SRPT FDA history")
built entirely from data we already own, and they are the internal-link spine — the one link
every event page couldn't previously make (to a company hub) now has a target.

## Integrity — the hub invents nothing
- **Links to existing pages only.** 459 internal links, **0 dead** at build; a random sample of
  live outbound links all resolve 200. A hub that links to a 404 manufactures exactly the GSC
  "Not found" errors we just cleaned up — so every target is verified against a real file.
- **No scores/probabilities.** The no-score CI scan finds nothing outside the footer's *negation*.
  `test_seo_invariants` and `test_si_display_cap` both pass across all 880 HTML files.
- **Self-canonical, index,follow, 0 non-www** in the sitemap.

## Two bugs the build caught (fixed)
1. **Stale /pdufa slug pages resurrecting swept catalysts.** First render drove "Upcoming" off
   the /pdufa/{slug} directories — but those are stale static pages. /pdufa/MRK-keytruda still
   says "target 2026-08-17" for a drug the FDA approved 2026-07-10. Listing them would have put
   decided-as-pending phantoms back on the site. Fix: Upcoming is now slate-driven (authoritative);
   MRK correctly shows only 09-21 + 10-10, no Aug-17 keytruda.
2. **"price-only" placeholder labels** leaking as drug names (SRPT). Suppressed → "FDA decision".

## Found, NOT fixed — flagged for follow-up
- **Stale /pdufa/{slug} pages for swept/decided catalysts.** MRK-keytruda, GSK-tebipenem-hbr,
  AZN-truqap, SPRO, VRDN, IONS-olezarsen, CELC, CORT (and any other swept this cycle) still render
  as *pending* on their standalone /pdufa pages, even though they're decided. Same decided-as-
  pending class we've been fixing on the calendar/archive — but on the /pdufa detail pages, which
  have no generator. The hubs no longer link to them, so nothing is amplified, but these pages are
  live and indexed. Recommend: 301 each swept /pdufa/{slug} to its /fda-decision page, or
  regenerate them as decided. Their own build path is the same "no generator" debt as the calendar.
- **Event-page → hub backlinks.** The hubs link OUT to events and are in the sitemap; the reverse
  link (each /pdufa and /fda-decision page linking UP to its /ticker hub) would complete the
  PageRank loop. That's a 560-page additive edit — the natural next pass, lower-risk done on its own.

## Deploy
Vercel → Ready, aliased www.pdufa.bio. Verified live: /ticker/MNKD, /MRK, /SRPT, /BIIB, /CELC all
200 + self-canonical; live sitemap shows 210 hubs / 546 URLs.
