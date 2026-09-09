# Builder ack, 2026-09-09 16:05 Pacific: item 3 shipped — the API no longer serves a day nobody announced
*Facts and build mechanics only; not investment advice. David approved option 1 (`date: null` + `date_month`) this afternoon.*

## Live build
Pushed `1046f1873`. Guards **78 green**, 0 failing. Verified against the live API after deploy.

## What changed
`date` now means one thing: **an announced day, or `null`.**

| date_precision | `date` | `date_month` | `days_to_decision` |
|---|---|---|---|
| `day` | the sourced day | the month | computed |
| `month` / `quarter` / `year` | **null** | `"2026-06"` | **null** |

Live check, `/api/v1/events?limit=500`, 456 rows:
- non-day-precision rows carrying a date: **0** (was 325)
- non-day-precision rows carrying `date_month`: **325**
- `days_to_decision` on those rows: null

`days_to_decision` had to go null with it. Counting down to a midpoint we invented is the same fabrication one field over, and `date_month` already states the granularity we hold.

## Why the comment was not enough
The old field carried a month midpoint and a source comment saying "never render `date` as a hard day unless date_precision === 'day'". That comment lives in our repository. It is not present in anyone else's parser, and it is certainly not present when a language model summarises the feed — which is the specific consumer this site exists to be correct for. 263 rows served the 15th, 62 more the 30th or 31st: **71% of the endpoint `/developers` advertises**.

## The breaking change is documented, in the same commit
New section on `/developers`, above the field list: the table above, the reason, the count, and the migration line — *"If you sorted on `date`, sort on `date_month` first, then `date`."* Filtering `date_precision === "day"` gives the dated calendar with nothing estimated in it. I did not add a `sort_date` field: a second date-shaped field is how the first one went wrong.

## Guard
`tests/test_api_no_manufactured_day.py` asserts the **shaping code**, not a sampled response, because the shape is what every consumer gets: `date` is gated on `date_precision === 'day'`; `date_month` is populated; `days_to_decision` is nulled without a day; `/developers` documents the rule. Proved 0 → 1 → 0 by restoring `date: e.d || null`, which fails with the 263-rows-on-the-15th message.

## Still open from your sweep
Item 5 (`source_url` / `page_url` split), item 7 (9 forward PDUFAs with no indication), item 8 (per-event re-stamp), and the CORT row's three remaining self-contradictions (readout-shaped id carrying the manufactured 15th, `ta: "Infectious"` for Cushing's syndrome, `source: "trial-estimate"` against its own review note citing Corcept's June 17 announcement).

Separately, David asked for a deeper conference-presenter mine; that is running against EDGAR now and will be a separate note with the rows and their filings.

*Informational and educational only; not investment advice. Builder, 16:05 PT.*
