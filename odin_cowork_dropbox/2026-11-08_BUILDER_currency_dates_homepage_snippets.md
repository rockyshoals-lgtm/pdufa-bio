# Builder note: unblocked rebuild, date audit, homepage "August", AI snippets
**2026-11-08, work 19:15-22:30 Pacific = 22:15-01:30 Eastern.** *RULE 1.*
*Facts only. Not investment advice.* Responds to "ensure the website is up to date, that all dates are correct, there is something on the home page that says data as of August, fix this, optimize for ai snippet, SEO".

## 1. The site was frozen since Nov 6
Six scheduled rebuilds failed (Nov 7-8, BLOCKED #63): `test_no_fabricated_conferences` -- conferences.json's verification stamp was 63 days old (limit 60). Every upcoming row (ACAAI Nov 12 through ADA Jun 2027) was re-checked against the organiser's own site: all dates and cities stand. JPM 2027 is now published by J.P. Morgan ("January 11-14, 2027 in San Francisco") and moved from _unannounced into the feed. Stamp 2026-11-08 (`apply_1108_conferences.py`).

## 2. "Data as of August" on the homepage
The visible text was current. Two things on the homepage still said summer:
- **Structured data.** The JSON-LD ItemList "Upcoming FDA PDUFA decisions" -- what search and answer engines read as the page's list of upcoming decisions -- held six Events dated Jul 29 - Aug 17, 2026, all marked Scheduled (CAPR on Jul 29, since moved to Nov 22; OTLK, VTRS, MRNA, LNTH, BMY all long decided). No builder owned it. New `sync_home_event_schema.py` rewrites it each run from the next 10 day-dated goals (Nov 14 .. Nov 30 today).
- **"Browse 2026 by month: July, August, September..."** -- static since July; in November it opened with four finished months and stopped at December. Now "Upcoming PDUFA dates by month": Nov 2026 through Jun 2027 with counts, an "All 2027 dates" chip, and the finished 2026 months as one quiet line.
- **Share image** (og.png on ~1,900 pages, also the card in Slack/X/AI answers): made 2026-07-25 for the pre-launch site, "COMING SOON · 2026", "live options", "Mobile app". Replaced with an evergreen card (`make_site_og.py`): every FDA PDUFA date with its source, updated daily, facts not advice; no counts or dates to go stale.

## 3. AI snippet
- Homepage FAQ gains a first, open question **"What are the next FDA PDUFA dates?"** answered in one sentence naming the next goal dates and drugs, mirrored exactly in the FAQPage schema (both rebuilt each run by `sync_home_event_schema.py`). The page's questions were all definitions; the question people bring to a PDUFA calendar had no sentence answering it.

## 4. Dates
- Every pending PDUFA row checked against the sentence in its own source: 51 of 62 already carried that sentence; 8 more were fetched and confirmed today (VRTX, CORT, GILD, PRAX x2, AXSM, BBIO encaleret, NVCR "Q4 2026"). CAPR's source (GlobeNewswire) refused the fetch (403); its Nov 22 date was confirmed on Nov 3 from SEC text.
- New from the EDGAR sweep Nov 5-8: **COGT bezuclastinib AdvSM, Jun 29, 2027** and **VSTM AVMAPKI FAKZYNJA blister-pack NDA, Feb 7, 2027** (both 8-K Nov 5).
- **Novo Nordisk, flagged for David**: the Q3 6-K (Nov 4) says the US review of denecimig (Mim8, now branded Frehemgo in the EU) "is still ongoing ... a US launch is expected in H1 2027", and for CagriSema only "preparing for the US launch ... in early 2027, subject to regulatory approval". Neither states a goal date. Our rows still show "2026" (Mim8) and "Dec 2026" (CagriSema); the source and quote now point to the Q3 6-K, but the window itself is not a sponsor statement. Decide whether to re-label them "date not announced".
- Held leads acked with reasons: #61 COGT and #68 MLYS (Q3 releases restating pending dates), #64-#66 (FDA approvals of Roche SC atezolizumab, Sanofi isatuximab and GSK belantamab matched our JAZZ/BMY rows on the words "formulation"/"dexamethasone").
