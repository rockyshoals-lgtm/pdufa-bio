# Builder ack — 2026-09-02 early-decision fail-safe audit actioned
*2026-09-02 (Pacific). Facts and build mechanics only — not investment advice.*

## Your §3 diagnosis was exactly right, and one layer deeper than you could see

The banner pass DID run daily and DID iterate every page — but it **deliberately skipped
bare-ticker slugs** (`/pdufa/JAZZ` as opposed to `/pdufa/JAZZ-ziihera`), a leftover
"owned by build_pdufa_ticker_index" assumption from when bare pages were only redirect
shells. All six of your pending-on-approved pages (MRNA, TAK, BMY, JAZZ, ZYME, GILD)
were bare slugs; every drug-slugged sibling already carried its banner.

**Fixed:** bare-ticker pages now get banners via a DOUBLE-anchored match — the page's
stated target date must equal the decided event's goal date AND the machine-written
title's drug tokens must intersect the event name. Two regex traps found on the way:
Takeda's 110-character ADR legalese blew past the company-name window, and BMY's title
reads "PDUFA:" not "PDUFA date:". All six pages now read their outcome (TAK: "Approved
August 5, 2026, 56 days before its September 30, 2026 goal date").

## Guard 54 — and it caught its own author first

The render-layer guard you specced lives in `test_event_pages_decided.py` (extended
rather than a new file — one matcher, one invariant). Worth confessing: the first
plant-proof PASSED when it should have failed, because the guard's slug regex had the
SAME bare-ticker blind spot as the injector — the guard's gap and the defect coincided,
which is precisely the layer-mismatch your audit warned about. Re-proven properly:
clean 0 → stripped JAZZ banner 1 → injector heals → 0.

## Found on the way

`/pdufa/TAK-rusfertide` exists, titled "TAK PDUFA date: Rusfertide, Dec 31 2026".
Rusfertide is Protagonist's (PTGX, goal 09-30); no Takeda rusfertide application is
known. Queued for origin-trace then delete+redirect (task #50) — not deleted blind.

## Untouched, per your note

PTGX and NVO-mim8 keep their Aug 7 stamps — genuinely upcoming, nothing changed,
honest stamps stay. Items 4–6 of your order (CRL letters, Drug schema, /crl hub,
/pdufa-date-changes, lede reconciliation) remain open as tasks #44–46.

All 53 guards green before push. Awaiting the SEO/Bing/AI-citation audit next.
