# Comprehensive audit — how we keep moving SEO / AI citations / Bing
**2026-09-06 18:10 Pacific · live build `2026-09-06T22:37:31Z` commit `19e2485` · every claim checked live with `Cache-Control: no-cache`**
*Facts and build mechanics only — not investment advice.*

*Chrome is not connected this run, so Bing Webmaster and Search Console could not be re-read. Channel figures below are the 2026-09-05 read (Bing data through Sept 3, which is the latest Bing publishes anyway). The first Chrome-connected slot re-reads both.*

---

# 1. STATE OF PLAY — the day closed far better than it looked at 09:20

The builder's 09:00 slot **did not fail — it stalled between building and committing.** The work was salvaged, committed at 15:10 PT, deployed 15:37 PT, and acked at 15:13. **All seven 09:00 ORDER items are live and verified:**

| Item | Live evidence (18:00 PT) |
|---|---|
| Four stale slug pages | `/pdufa/MRK-keytruda`, `/pdufa/BIIB`, `/pdufa/ONC`: "under FDA review" **0**; ONC's banner links the deciding ticker `JAZZ-2026-08-25`. `/pdufa/NRXP`: retitled **"NRXP FDA goal date (ANDA): KETAFREE"**, body *"was under FDA review, with a goal date of July 29, 2026 that has passed with no public decision"* — the one remaining "under FDA review" hit is that past-tense sentence, which is correct |
| Calendar JSON-LD ItemList | **47 items = 47 unique rows, set difference empty both ways.** Machines and readers now see the same calendar |
| Asundexian | `/drug/asundexian` 200 — *"Bayer announced on May 19, 2026 that the FDA accepted the NDA… Priority Review… OCEANIC-STROKE"*, bayer.com linked, **no invented quarter** (`dp:"undisclosed"` shipped) |
| Zilurgisertib | one row, labelled INCY / MIRM; `/fda-this-month` and `/calendar` September triplets now equal |
| SRRK caveat | "Catalent Indiana" + "fill-finish" rendered with the Aug 21 release linked |
| `build-info.json` | now carries `commit` and `commit_at_build` — my step-3 check can finally discriminate deploys |
| `/pdufa-date-changes` | 200 — row 1 *"CAPR · Deramiocel — Goal date moved from Aug 22, 2026 to Nov 22, 2026, 92 days later, announced by Capricor"*, sourced |

**65 guards.** Two new: `test_no_past_target_pending_pages.py` (the check that would have caught camizestrant a day earlier) and `test_calendar_itemlist_matches_rows.py`.

**Currency gates green:** API `as_of` 2026-09-06 · 0 past-goal day PDUFAs undecided · 0 past Guided readouts without outcome · calendar lede sums.

## Two corrections I owe

1. **I wrote this morning that the `/calendar` explainer carried only "does not publish."** Wrong — my grep looked for "10 months" and the page says "10-month." The explainer is live and it is exactly the block I asked for: *"A standard review carries a 10-month goal from the FDA's acceptance of the application; a priority review carries a 6-month goal. If the sponsor submits a major amendment during review, the FDA can extend the goal date by 3 months. The FDA does not publish an official, forward-looking PDUFA calendar. Every date on this page comes from a company filing, press release or FDA notice, and each row links its source. Of the 32 FDA decisions…"* Those are the five sentences the Bing answer box was sourcing from five competitors. Hyphen-blind grep; my error.
2. **The builder's MIRM correction cuts my way, and I'm recording it against the builder's honest reversal:** Mirum in-licensed zilurgisertib from Incyte (May 6, 2026, $16M upfront, per the Q1 8-K exhibit). One application, two tickers — the row was never a mislabel. The builder said so unprompted.

---

# 2. WHAT ACTUALLY MOVES EACH CHANNEL — evidence from this month, not theory

Before the ORDER, the mechanism. Every item below is tagged with which of these it moves.

| Channel | What moved it (observed) | What didn't |
|---|---|---|
| **AI grounding queries** (1 → 19 in 30 days) | **Being first to a fact on a drug entity.** `rusfertide pdufa date`: nonexistent Aug 27 → 72 citations by Sept 3, after the watcher caught MIMRYLO 33 days early. 10 of 19 queries are `{drug} pdufa date`. | Schema alone (FAQPage existed for weeks at 18 flat); more table rows |
| **AI citation depth** (115 → 3.3K) | Answer-format sentences on decision pages (437-page rewrite); `Drug` schema + `alternateName` with **brand first** | — |
| **Bing answer box** (cited on 0 of 3 head terms as of Sept 5) | Competitors won it with definitional prose, an honest FAQ answer, a dated changelog, captioned tables. **The explainer block shipped today is the direct counter — its effect is the first thing to test when Chrome is back.** | Rank (we were #1 organic beneath the box) |
| **Bing organic** (#1–2 on head terms) | Daily rebuild + freshness stamp + per-event answer pages | — (and novapharmanews has now copied the stamp) |
| **Bing CTR** | Position ≤2.5 → 27–38%; 3.2–4.4 → 0–13%; 6+ → 0.5%. Snippets in answer format (PTGX 15% → 20.6% at the same position) | Anything below position 4 |
| **Google organic** (57 indexed of 1,412; head terms at 68–81) | Entity queries convert 50–100% where we appear; nothing else does. **Authority** — links, David's lane | Content volume (indexed flat at 57 for three weeks) |
| **Google AI Overview** (cited on 0 head terms) | It reads *sentences with dates in them* off Pharmacy Times and BPIQ's changelog | Tables |

**The one-line model:** *first to the fact → sentence an AI can lift → entity markup so the AI knows what the sentence is about → authority so Google trusts it.* Everything in the ORDER serves one of those four.

---

# 3. THE ORDER — consolidated, including what survives from Gemini

Capped at five per slot per the cadence; here it is as three slots. Each item: **mechanism → acceptance check.**

## Slot A (tomorrow 08:20) — protect what's working, finish the answer-box play

| # | Item | Mechanism | Acceptance (I run it live) |
|---|---|---|---|
| A1 | **Table `<caption>` on every `/calendar` grid** + visible caption text ("Upcoming FDA PDUFA dates — {Month} 2026 — updated {date}") | Bing/Google AI extract tables as `Table_title:` — Assyro, CheckRare and MarketBeat get cited that way today; we have **0** captions | `grep -c '<caption' /calendar` = number of `.mhead` grids (7); each caption contains the month and "updated" |
| A2 | **Backfill brand names into `alternateName` for every historical approval** (the watcher does it for new ones; PASATRU, LYTENAVA, ZUSDURI etc. still absent per my Sept 3 check) — source: the Drugs@FDA brand harvest already built | Entity breadth. Drugs.com beats us on `rusfertide pdufa date` on Google with the brand in the title | Random 20 approved drug pages: ≥18 carry brand first in `alternateName`; `/drug/garetosmab` contains "Pasatru" |
| A3 | **Populate `/pdufa-date-changes` from the archive** — it has 1 row; the archive holds more moves (camizestrant's May extension, CORT's, every `prior_pdufa_date`, every readout watcher registry contradiction) | This is BPIQ's changelog shape that Google's AI Overview quoted. One row won't be cited; twenty will | ≥15 sourced rows, newest first, each with old date → new date → days → announcing party → source link; no forward-looking verb |
| A4 | **`/learn/what-is-a-pdufa-date` internal links** from every drug and event page on first use of "PDUFA" | Fourth audit at zero clicks from position 8 on our own core term. Bing shows Motley Fool for bare `pdufa`. Cheapest authority transfer we have | Random 20 `/drug/` + 10 `/pdufa/` pages: each contains an `<a href="/learn/what-is-a-pdufa-date">` |
| A5 | **SI study method sentence** (from the Gemini red-team) — state which FINRA settlement dates the published study used; if it was the April snapshot, recompute from `conf_study/si_panel_2017_2026.csv.gz` before the sentence goes up | Trust. `/research` claims "point-in-time"; the study page has no method sentence. This is the kind of thing a journalist checks before citing | `/research/short-interest-fda` contains a sentence naming the settlement-date rule (e.g. "nearest FINRA settlement on or before T-14") and the n at each point |

## Slot B (tomorrow 09:00) — the entity and changelog surfaces AI answers already reward

| # | Item | Mechanism | Acceptance |
|---|---|---|---|
| B1 | **`/company/{slug}` pages** for every sponsor with ≥2 tracked events — PDUFAs, readouts, decisions, CRL letters, patent cliffs in one dated list | `pfizer pfe pdufa dates fda approval decisions 2026 2027` — 82 impressions, **position 3.23, zero clicks**; Google PASF "FDA approval calendar stocks". Real demand, 404 today | `/company/pfizer` 200; title answers the query ("Pfizer (PFE) FDA decisions and PDUFA dates 2026–2027"); every row links its event page; in the sitemap |
| B2 | **CRL reason taxonomy over the 458 letters** — from Gemini, **reframed**: tag each letter CMC / efficacy / safety / labeling / other from its text; publish **counts** on `/crl` and a one-sentence tag on each linked decision page | New grounding-query family (`why did X get a CRL`, `CRL manufacturing`) that no one owns; sentence supply on a hub that exists. **Never** "recovery path," never a median-recovery figure, never Gemini's invented "4.2 months / 40%" | `/crl` contains "Of N letters since 2020, N cite manufacturing (CMC), N efficacy, N safety…" with n; each decision page that links a letter carries its tag; a `_crl_reason_tags.json` ledger with the quoted sentence that justified each tag |
| B3 | **"Positioning before the decision" block, phase 1: options** — from the 09-05c data discovery; recompute my 389-event PoC through the production pipeline | The single most-searched pre-catalyst fact; no free site has it; ~1,270 historical events. Sentence-shaped by construction | `/fda-decision/OMER-2025-12-24` contains "Two weeks before the decision, at-the-money options priced a move of ±X% through {expiry}. The stock closed +79.5%." — with both mandatory caveats verbatim on the page and no strategy verb anywhere (guarded) |
| B4 | **Shares-outstanding delta per event** — the fact-only remnant of Gemini's "dilution" idea, from `sec_shares_outstanding.json` (317 tickers) | Entity fact, low cost, answers a real question without a warning label | Event pages for tickers in the file carry "Shares outstanding rose/fell N% between {date} and {date} (SEC)"; **no** "dilution", "risk", "warning" tokens (guard) |
| B5 | **`Dataset` schema + CSV download on `/runup-by-year` and `/research/*`** | Google authority via citable objects; academics and journalists link datasets. CC BY 4.0 is already declared — make it machine-readable | Each study page carries `@type: Dataset` with `license`, `temporalCoverage`, `variableMeasured`; a `.csv` link resolves 200 |

## Slot C (week) — the 13F block, and what waits on David

| # | Item | Mechanism | Acceptance |
|---|---|---|---|
| C1 | **Positioning block, phase 2: specialist-fund 13Fs** — 878 events (49%) | Second sentence family only we can write; Q2-2026 filings landed mid-August | RVMD's Rasonque page: "As of the June 30, 2026 filings, N of the 10 largest biotech specialist funds held Revolution Medicines — Baker Bros. N shares (Δ), …" with the EDGAR link |
| C2 | **Monthly page for next month goes live on the 25th** (`/fda-this-month` already does this month; add `/fda-next-month` or pre-generate October) | Pharmacy Times' Aug 21 "8 dates to watch" piece was in Google's AI Overview by Sept 5. Publish ours before theirs each month | `/fda-decisions-october-2026` (or equivalent) 200 by Sept 25 with dated sentences |
| C3 | **JUVÉDERM PMA out of the drug-decision census** (archive-side) | Accuracy — a device supplement on a drug calendar is the kind of thing that gets screenshotted | `/calendar` and `/crl` census sentences exclude PMA; archive row tagged `application_type` |
| **David** | **`/terms`, `/privacy`, `/refund-policy`, `/contact`** — all 404 since August | Blocks the email list, the paywall, and Gemini's only sound UX idea (watchlist date-slip alerts). Nothing I can give the builder ships accounts without these | four URLs return 200 |
| **David** | **Links** — the Google gap is authority; the API (`/developers`) and the datasets (B5) are the link magnets to point people at | indexed 57 → moves |

## What I'm NOT including from Gemini, and why (one line each)
Dilution *probability* — a prediction · IRA countdown — implies every drug faces negotiation; almost none do · PBM formulary mapping — data we don't hold, no query asks for it · Anti-AI campaign — hindsight-as-foresight, defamation surface, glass house · Enterprise/Snowflake tier — monetization, not rank · Portfolio dashboard — blocked by the legal pages and doesn't move a single ranking signal until it exists.

---

# 4. THE TWO TESTS THAT MATTER MOST WHEN CHROME IS BACK

1. **Bing `pdufa dates 2026` — does the answer box now cite pdufa.bio?** The explainer shipped today carries the exact five sentences it was quoting from biomednexus, assyro, biotechsign, burns-media and guerilla-finance. If we're in the box within a week, the sentence-supply thesis is proven and B1–B3 get promoted. If not after two weeks, the box is an authority filter and we shift weight to Google-authority items.
2. **Sept 8 console read** — `/fda-decisions-today` (already 13.33% CTR at 3.77 on Sept 3), `/learn/what-is-a-pdufa-date` (zero clicks, four audits), grounding queries (19 → ?), and whether the 229 restored drug URLs re-index cleanly.

---

# 5. TARGETS (unchanged from 09-05b, restated so the ORDER has a scoreboard)

| Metric | Sept 3 | End-2026 | End-2027 |
|---|---|---|---|
| AI grounding queries | 19 | 50 | 150+ |
| AI citations / 3 mo | 3.3K | 10K | 50K+ |
| Bing answer box, 3 head terms | 0 / 3 | 2 / 3 | 3 / 3 |
| Bing clicks / 3 mo | 293 | 800 | 5,000+ |
| Google indexed | 57 | 400 | 1,400+ |
| Google page 1, `{drug} pdufa date` | ~5 drugs | 30 | every tracked drug |
| Approval → on-site latency | <24h (watcher, since Sept 5) | hold | hold |

---

# BOTTOM LINE

**The morning's "0 of 9" was a commit that never happened, not work that never happened.** By 15:37 PT every 09:00 item was live and verified: four stale pages fixed with the deciding ticker linked, the calendar's schema finally agrees with its rows, asundexian is published without an invented date, `/pdufa-date-changes` exists, and `build-info.json` carries a commit SHA. The `/calendar` explainer I said was missing has been live all day — my grep was hyphen-blind, and it is the exact block the Bing answer box was quoting from five competitors.

**The mechanism is now clear enough to build against:** first to the fact, in a sentence, with entity markup, on an authoritative page. Every measurable gain this month came from the first two — the watcher's MIMRYLO catch turned into 72 citations on a query that didn't exist a week earlier. The ORDER above is fifteen items that each serve one of the four, including three ideas salvaged from Gemini in fact-only form: a CRL reason taxonomy as counts, a populated date-change log, and shares-outstanding deltas.

**The two tests that decide the next month:** whether today's explainer puts us in the Bing answer box, and the Sept 8 console read. Chrome needs to be connected for both.

---
*Verified live 2026-09-06 18:10 PT against commit 19e2485. Channel figures from the 2026-09-05 console read (Bing data through Sept 3). Not investment advice.*
