# Bing Webmaster: the two "Top Recommendations", and what I submitted today
**2026-10-17, ~18:15 Eastern = 22:15 UTC (Saturday).** Bing Webmaster console times are shown in local (Pacific) time. *RULE 1.*
*Facts and build mechanics only. Not investment advice.*

David signed back in to Bing Webmaster and asked for every Top Recommendation to be fixed. Of the two, one is a site change (builder), and one cannot be fixed by code.

## 1. Submitted today (URL Submission, manual)

**Today's quota before my batch:** the 06:32 Pacific CI batch (80 URLs) had already gone in, including:
- `/`, `/fda-decisions-today`, `/fda-approval-decisions-this-week`, `/calendar`, `/readouts`, `/conferences`, `/crl`, `/fda-approval-letters`;
- `/pdufa/RHHBY-enspryng`, `/pdufa/IRD-phentolamine-ophthalmic`, `/pdufa/MRK-ifinatamab-deruxtecan`.

So the ordered hub-first submission from the 10-13 note is working.

**I added 10 at 15:17 Pacific (18:17 Eastern), all decision pages not in the CI batch:**
- RHHBY-2026-10-15 (Enspryng)
- VTRS-2026-10-16 and IRD-2026-10-16 (RYZUMVI)
- IBRX-2026-10-14 (Anktiva)
- LLY-2026-09-23 (Onswik)
- TEVA-2026-09-25 (Degevma)
- PFE-2026-10-07 (Tukysa)
- AMGN-2026-10-09 (Repatha)
- TEVA-2026-10-08 (Weltruza)
- BMY-2026-09-30 (Camzyos)

Quota after: **90 used, 10 left**; it resets around 17:15 Pacific.

**Deliberately not submitted:** the 8 decided event pages whose descriptions still read as pending (10-17 audit §2a). The CI batch already resubmitted two of them (`/pdufa/RHHBY-enspryng`, `/pdufa/IRD-phentolamine-ophthalmic`) with the stale descriptions. **Fix those first; the next CI batch will carry them.**

## 2. Recommendation "Important pages using meta robots tag that need review" (Moderate, 2 pages)

| URL | Live robots | What the page holds |
|---|---|---|
| `/ticker/PBYI` | `noindex,follow` | 1 sourced row: neratinib readout, Oct 2026, "Completed per registry" (CT.gov link) |
| `/ticker/VYGR` | `noindex,follow` | 1 sourced row: VY7523 readout, May 2027, Estimated (CT.gov link) |

**Cause.** `enrich_ticker_hubs.py` marks a hub noindex when it has "no verified catalyst". A registry-sourced readout does not count as verified, so a hub whose only row is a sourced CT.gov readout gets noindex. Bing considers both pages important, which means they have inbound links or query demand.

**Fix, for the builder.** A hub that carries at least one row with a `source_url` is not thin; index it. Keep noindex only for hubs with no sourced row at all.
- Expected effect: these two, plus any others in the same state. The builder should print the count.
- Guard: no indexable-quality hub (≥1 sourced row) carries noindex. Prove it 0 → planted 1 → 0.
- Once live, submit `/ticker/PBYI` and `/ticker/VYGR` (2 of the 10 remaining slots, or the next CI batch).

## 3. Recommendation "Your site does not have enough inbound links from high quality domains"

This is not a code fix, and I will not suggest anything that manufactures links (directories, link swaps, paid placements). Bing penalises those, and they would undercut a facts-only source. The honest levers are ranked here by effort.

1. **A "Cite this" block on decision and research pages.** One line of plain-text citation with the URL and the date read. Journalists and AI answers that already use us (Bing cites `/fda-decision/VTRS-2026-10-16` for RYZUMVI) then link instead of paraphrase. Builder, small.
2. **`/research/fda-decision-timing` as a citable dataset.**
   - Add a CSV download, a stable DOI-style permalink per version (v32: 21/10/1), and a methods paragraph.
   - Original statistics are what trade press and academics link to.
   - Builder, small; David decides whether to send it to the reporters who covered the week's approvals.
3. **Free API listing.** `/developers` exists. Listing it on public API directories that are editorially curated (not link farms) is a legitimate high-quality referrer. David's call which ones.
4. **Corrections as a public page.** The 10-15 corrections pass (four non-approvals removed, Camzyos re-dated) is the kind of thing a data-journalism audience links to. A `/corrections` page with dated entries also helps trust signals. Builder, small.

None of these moves the Bing recommendation within weeks. It is a lagging measure of the site's reputation, and the work in the audits (being first and right on approvals) is what feeds it.

## 4. Carried for David

- After the builder fixes the 8 event-page descriptions, use URL Inspection → Request indexing on `/pdufa/RHHBY-enspryng`, `/pdufa/IRD-phentolamine-ophthalmic` and `/pdufa/IBRX-anktiva`. Or let the next CI batch carry them.
- Bing Webmaster sign-in drops every few days. If CI's Bing API key is in `.env` as the builder notes say, the console is only needed for reading reports, not for submission.
