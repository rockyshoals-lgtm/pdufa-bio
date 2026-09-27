# Builder, 09-27: the FDA's own drugs feed had Atebrioz first, and now we read it — while fda.gov refuses us
**2026-09-27, written ~14:30 Pacific = 17:30 Eastern = 21:30 UTC.** *Per RULE 1 every time carries its zone. Facts and file contents only; not investment advice.*

Reply to the 09-27 audit ("the numbers are now the FDA's own, and we lost the answer box on packaging, not accuracy"). Your re-derivation of 29 / 18 / 10 / 1, median −3, matches the build row for row. Items 1–5 are done and guarded, with one thing you need to know first.

---

## 0. fda.gov is refusing every non-browser client we have, CI included

Every fetch of fda.gov HTML or RSS this weekend returns **HTTP 401** (the FDA's "apology" page) — from this machine, from the sandbox, and from the GitHub runner. Three User-Agents tried, all 401. `api.fda.gov` (Drugs@FDA, openFDA) is unaffected. The consequence I had not seen until today: the existing drug-page watch has been printing **"0 press items scanned"** in CI (16:32 UTC run) — the FDA press-feed pass is blind right now, and it said so only as a zero. The new watcher records its last successful read in `_watch_health.json` and prints **`BLIND: last successful read ... never`** rather than a quiet zero; a 401 is never a lead and never blocks. If this persists into the week it needs a decision (a browser-backed fetch, or reading the FDA pages another way); I have not tried to work around the block.

## 1. Item 1 — the FDA's "What's New: Drugs" feed (`watch_fda_drugs_feed.py`)

The CDER News & Events page links **"RSS Feed for What's New"**: `fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml`. Read through a fetch that the FDA does serve, it carries the Atebrioz item verbatim — *"FDA Approves Third Treatment for Fibrodysplasia Ossificans Progressiva … FDA has approved Atebrioz (zilurgisertib) tablets …"*, **pubDate Fri, 25 Sep 2026 14:46:15 EDT** — which is where the drug is named: in the summary, not the headline. The watcher matches armed drugs (brand or INN) against headline + summary with an FDA-decision headline, blocks like the other passes, and lists FDA approval notices naming nothing we track (on 09-25: **Gazyva for idiopathic nephrotic syndrome** — not on our calendar). In CI after the sponsor-feed step.

**Acceptance, replayed:** `tests/test_fda_drugs_feed_replay.py` runs the 09-25 feed excerpt (kept as `tests/fixtures/fda_drugs_whatsnew_2026-09-25.xml`) against MIRM and INCY as they stood that afternoon: both raise a lead from the **14:46** item; Gazyva is reported untracked; the AdComm notice and the "Notable Approvals" index item raise nothing. Live it is blind until section 0 clears.

## 2. Item 2 — fact-first snippets on FDA-sourced pages

`/fda-decision/MIRM-2026-09-25` and `INCY-2026-09-25` now read:

- **title:** "Atebrioz (zilurgisertib) FDA Approval Announced Sep 25, 2026 | MIRM FDA Decision"
- **description (154 chars):** "On Sep 25, 2026, the FDA announced its approval of Atebrioz (zilurgisertib) for fibrodysplasia ossificans progressiva (ages 12+), the third FOP treatment."

"The third FOP treatment" is the FDA's own headline ("FDA Approves Third Treatment for …"), held on the row as `fda_framing` / `fda_notice_title`; the margin caveat stays in the body. The rule in `rewrite_decision_snippets.py`: a row whose action day is unstated but whose source is on fda.gov leads with "the FDA announced its approval"; "announced by the sponsor" is kept only where the sponsor is the only source. Guard **`tests/test_fda_notice_pages_fact_first.py`** (proven: planted "announced by the sponsor" on INCY → FAIL → OK). One self-inflicted bug caught on the way: the title parser read "…) FDA Approval Announced" as drug "Atebrioz (zilurgisertib) FDA", which wrote "FDA FDA" into the next title; fixed and stripped.

## 3. Item 3 — sponsor feeds for the next 60 days

Hand-verified and added (each parses and carries current releases): **VTRS** (Viatris newsroom RSS), **IRD** (Opus Genetics `ir.opusgtx.com/press-releases/rss`), **GSK** (`gsk.com/en-gb/media/rss/`), **ABBV** (AbbVie newsroom RSS); **INO** was already in. **Merck and Roche/Genentech: no public news-release RSS found** — merck.com refuses non-browser clients, Genentech's only feed is "Stories", roche.com lists none; recorded in `_sponsor_feeds.json` with that note. Coverage 8 of 33 armed sponsors. MRK's Oct 10 and RHHBY's Oct 9 / Oct 15 decisions rest on the FDA feeds (see section 0) and EDGAR.

## 4. Item 4 — `/fda-approval-letters`

Live from the chain and CI: **38 FDA actions** (35 approval letters from Drugs@FDA, 1 CBER notice, 2 released CRLs; co-listed partner rows merged, so GSK/SPRO, JAZZ/ZYME and PFE/ROIV are one row each), newest first, each linking the FDA document, the application/supplement, the sponsor, the announcement day where it differs (**7 of 38** were announced later than the FDA acted), and our decision page. Dataset + FAQPage schema; linked from the timing study and `/llms.txt`. Guard **`tests/test_fda_letters_hub.py`**: the n in the h1 equals the rows, equals the distinct FDA actions in the dataset (proven 0 → planted 39 → FAIL → 0).

## 5. Item 5 — AASLD and SABCS: complete, and orphaned

Both `/conference/AASLD` (Nov 5–9, Denver; MNPR; 20 past presentations by 14 companies) and `/conference/SABCS` (Dec 8–11, San Antonio; OLMA; 11 by 10) carry dates, location, sourced presenters and a four-question FAQ ("When is AASLD 2026?"). **But no page on the site linked to either** — nor to any of the 14 per-conference pages. The Bing queries you saw could only land on the hub. The hub cards now link their pages (12 upcoming linked); guard **`tests/test_conference_pages_linked.py`** (proven 0 → old hub → 12 failures → 0).

## 6. Your Google read

Agreed, and it changes priorities: on Google the head terms sit at positions 55–78 while drug-name queries sit at 1–7, so per-drug decision pages are the Google strategy and their first sentence is the product. Item 2's rule is the general version of that.

## Files
`watch_fda_drugs_feed.py`, `tests/fixtures/fda_drugs_whatsnew_2026-09-25.xml`, `tests/test_fda_drugs_feed_replay.py`, `rewrite_decision_snippets.py`, `fix_meta_lengths.py`, `tests/test_decision_snippets.py`, `tests/test_fda_notice_pages_fact_first.py`, `_sponsor_feeds.json`, `build_fda_letters_hub.py`, `tests/test_fda_letters_hub.py`, `build_conferences.py`, `tests/test_conference_pages_linked.py`, `build_early_decisions.py`, `build_llms_txt.py`, `.github/workflows/pdufa-rebuild.yml`, `_chain_0919.bat`.

## 7. Appended 13:40 Pacific = 16:40 Eastern = 20:40 UTC: RETRACTION of part of section 0

Section 0 said the GitHub runner is refused too. **It is not.** The dispatched run of this push (36348139742, green) logged `FDA drugs feed: 20 item(s) read; 0 unreviewed lead(s) on armed events; 2 FDA approval notice(s) naming no tracked drug` at 20:29 UTC. The 401s are real, but only from this machine and the sandbox. I inferred the runner was blocked from the drug-page watch's `0 press items scanned` line; that zero has another cause I have not yet found (it may simply be an empty window, or a different fetch path). What stands from section 0: our local and sandbox clients are refused by fda.gov, and the new watcher reports BLIND rather than a silent zero. What is withdrawn: "CI included," and "the FDA press-feed pass is blind right now."
