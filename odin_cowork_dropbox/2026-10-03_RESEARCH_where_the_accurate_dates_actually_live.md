# 2026-10-03 — Where the accurate dates actually live (research note, tested not theorized)

**Classification: RESEARCH + BUILD DIRECTION.** From the trading-side research assistant.
David's question: *what do we need to mine to get the most accurate conference presenter
schedule and the most accurate readout dates?* This ranks the sources by how close they sit
to the truth, and I probed the top two today before writing a word.

## The finding that reframes everything

Today I pulled Xenon's Q2 2026 earnings transcript (2026-08-06) through the FMP tool we
already pay for. Management said, in plain English, that the **X-TOLE2 Phase 3 readout
already happened** — presented at AAN in April as a late-breaking podium — and that they
are now preparing the NDA, presenting more data at AES in December, running X-TOLE3 with
Japanese sites, and expecting the X-NOVA2 readout in **1H 2027**.

BiopharmaCatalyst's current file carries `XENE  azetukalner (X-TOLE)  Phase 3  2026-09-07`
as a *forward* catalyst. Last month I flagged that date as "pulled forward from 9/30 —
dangerous." The primary source says the event is in the past. One of BPC's few non-
placeholder phase-readout dates is a stale entry for a readout that already printed.

That is not a knock on BPC specifically. It is the structural problem with every
catalyst calendar that is *curated* rather than *mined from the people who set the date*:
the company says when, and everything downstream is a lossy copy of that. **The accuracy
ceiling is set by how close you sit to the company's own words.**

## Source ranking — readout dates

| rank | source | what it gives | status |
|---|---|---|---|
| 1 | **Earnings call transcripts** | Management guidance in their own words, every quarter, plus the *change* between quarters (a slip from "Q4" to "1H next year" is a signal). Also tells you what already happened. | **We have the tool (FMP earningsTranscript). Tested today. Not wired in.** |
| 2 | **Investor decks — "Anticipated Milestones" slide** | Tabular, dated, updated each quarter. | Not mined. IR pages are client-rendered (Candel IR fetched empty today); needs browser or the IR platform's JSON feed. |
| 3 | **CT.gov status TRANSITIONS** | `Recruiting → Active, not recruiting` = enrollment done, data lock typically 3–6 mo out. `→ Completed` = data lock happened. We read the PCD; we do not watch it *change*. A status flip is a leading indicator and it is free. | Partially mined (PCD only). Diff logic not built. |
| 4 | 10-K / 10-Q milestone tables | What we do in the deep pass. Quarterly, lagged. | Mined. |
| 5 | EDGAR 8-K guidance phrases | What `readout_scan.py` does. Catches ~190 tickers. | Mined. |
| 6 | Conference acceptance | Upper bound: data presented 10/23 is public by 10/23. | Mined (16 events). |
| 7 | Vendor calendars (BPC) | Convenient, 92% placeholders on phase readouts, and — per today — can carry stale events as forward. | Used as a cross-check and drift source only. |

**Honest note on #1:** my first-pass regex caught only 3 guidance sentences out of a
53,000-character transcript; the richer language ("we remain on track," "data from X in
the fourth quarter," prepared-remarks milestone lists) needs a proper extractor, not a
quick regex. The *signal* is unmistakably there. The extraction is the work.

## Source ranking — conference presenter schedules

| rank | source | what it gives | status |
|---|---|---|---|
| 1 | **The congress's own program / abstract book** | THE schedule: session date, time, hall, abstract number. Public, searchable by author affiliation. Released on a known calendar (ASCO titles ~late Apr, ASH ~early Nov, ESMO ~Oct, AACR ~Mar). | Not mined. This is the ground truth everything else approximates. |
| 2 | **Company IR "Events" page** | Every public biotech lists upcoming presentations with dates. Covers the newswire-only announcements we cannot see in EDGAR (GRI, LLY). | Not mined; client-rendered, needs browser/feed endpoint. |
| 3 | EDGAR 8-K/6-K | What `conference_miner.py` does. 16 events. | Mined. |
| 4 | Newswire (PRN/GNW/BW RSS + summary) | The lane added 09-06; summary field now persisted. | Mined; gain still unmeasured (task #172). |
| 5 | BPC conference column | Dated, but today's file promoted three NYE placeholders to congress dates. | Cross-check only. |

## What to build, in order of accuracy gained per hour spent

1. **Transcript guidance miner** (`transcript_guidance.py`). For every armed ticker: pull
   the latest transcript via the FMP tool, extract (drug/trial, timing-phrase, sentence),
   canonicalize the period with the `_norm_period()` we already have, and — the part no
   vendor does — **diff against the prior quarter's transcript** to flag slips and
   completions. Emits a `GUIDANCE` source for the gold pass at FIRM confidence (the company
   stated it) and a `DONE` flag that retires stale forward rows. XENE's X-TOLE2 would have
   been retired in April. Cost: one FMP call per ticker per quarter; ~385 armed names.

2. **CT.gov transition watcher.** We already poll CT.gov. Persist `overallStatus` +
   `primaryCompletionDate` per NCT daily and emit a row on any change. A `Recruiting →
   Active, not recruiting` flip on an armed name is the earliest public tell that a
   readout clock has started. Nearly free — it is a diff on data we already fetch.

3. **Congress program scrapers**, big five first (ASCO / ASH / ESMO / AACR / SITC).
   Each has a searchable online program; search by sponsor/affiliation for the armed
   list in the window between title release and the meeting. Output is GOLD by
   construction — it *is* the agenda. This also replaces the BPC conference column
   entirely and would have caught every ESMO presenter we are currently missing
   (CATX, KTTA, NBP, EVAX).

4. **IR events via the platform feed, not the page.** Most biotech IR sites run on Q4 Inc
   or Notified, which expose a JSON event feed behind the rendered page. Worth one
   afternoon to map the two or three feed shapes; then it is a per-ticker poll.

## What I am NOT recommending

- Fighting BusinessWire's Akamai block. Closed 09-07; the summary lane covers it.
- Buying more vendor data. The accuracy ceiling of a vendor is the vendor's lag from the
  company's own words; the sources above sit *at* the company's words.

## Scorecard honesty

Nothing above claims our dates are already more accurate than BPC's. The date-accuracy
scoreboard (09-07) measures *honesty* (we label buckets; they render NYE as a day). True
accuracy — whose date was right when the event hit — needs outcome tracking, which
`readout_date_drift.csv` is accumulating. The transcript miner is also the fastest way to
*build* that outcome record, because transcripts are where companies confirm what
happened.

*Informational only — not investment advice.*
