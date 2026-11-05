# Builder note: currency + UX / SEO / Bing / AI-citation audit
**2026-11-05, work 00:40-03:30 Pacific = 03:40-06:30 Eastern.** *RULE 1.*
*Facts only. Not investment advice.* Responds to "ensure currency and everything is working, audit UX, SEO, BING, ai citations, etc, and continue to optimize".

## 1. Currency
- CI: last 5 rebuilds green; 0 open issues at start. Next decisions: CYTK, SMMT, TEVA (Nov 14), NVCR (Q4).
- EDGAR sweep of 8-K/6-K exhibits Nov 3-5 for "PDUFA": one new date, **URGN UGN-103, June 14, 2027** (UroGen 8-K Nov 4, LG-IR-NMIBC). SMMT, MLYS, CORT, QURE, HRMY, AQST filings restate dates already on the site.
- Bing's AI answer for "pdufa dates 2027" cites a competitor (assyro.com) and lists Sarepta AMONDYS 45 / VYONDYS 53 for Feb 28, 2027. Sarepta's own filings (Q2 10-Q, 8-Ks to Sept 23) state no such date; not added. Re-check after Sarepta's Q3 filing.

## 2. Data errors found and fixed
- **CYTK aficamten (Nov 14, the next decision on the site)**: the row, event page, ticker, drug and this-month pages said *non-obstructive* HCM. The application is the MAPLE-HCM sNDA, aficamten vs metoprolol in **obstructive** HCM (Cytokinetics 8-K 2026-05-05). Bing's #1 result for "aficamten pdufa date" was showing the wrong indication.
- **INBX Apr 14, 2027** was labelled INBRX-106 / head and neck cancer. Inhibrx's 8-K (2026-06-15) is **ozekibart (INBRX-109), conventional chondrosarcoma**. Page moved to /pdufa/INBX-ozekibart (301 kept).
- **CGEM Feb 27, 2027** named only "CLN-081"; now "Zipalertinib (CLN-081), relapsed EGFR ex20ins NSCLC" per Cullinan's 8-K. Two 2027 calendar rows carried rel="nofollow" to live pages; removed.

## 3. UX
- **Mobile nav on 1,209 pages** (every /pdufa event page, /fda-decision, /drug, /ticker, patent pages): at phone width the nav rendered as 18 stacked links and the h1 started below the fold, because those pages never got the homepage's menu button. `inject_mobile_nav.py` applies the homepage's own `style#navpolish` + `button.pd-burger`, verbatim (workflow + chain, after rebuild_nav). Verified on a live page at 375 px: header, burger, h1 and key facts on the first screen; menu opens and closes. Nav chrome added to the sitemap BOILER so it does not move lastmod.
- **2027 had no entry point.** /calendar ends at December 2026 and linked no 2027 month, while 35 sourced 2027 dates sat on month pages. New `build_calendar_year_hub.py`: **/calendar/2027** (one quotable sentence, rows by month, CollectionPage schema) and an "Already set for 2027" block with month chips on /calendar. Event pages for 2027 dates now link that year and month instead of "the full 2026 calendar".
- Homepage lede said "tracks 25 upcoming FDA decision dates" (the /calendar window). Now "25 ... through December 2026, 35 more already set for 2027 and later" (`build_hub_lede.py`; the 25 still matches /calendar, as the guard requires).
- Homepage badge "Data through Nov 5" beside "Data as of Nov 4, 9:03 PM ET": the badge read the UTC date of each row's updated_at. Now Eastern (RULE 1).

## 4. AI citation / trust
- **Event pages showed no source.** The builder linked a source only when the row's `url` was off-site, a convention retired months ago; rows carry `_d.source/source_url/source_quote` and no page rendered them. `inject_event_page_source.py` (workflow + chain) writes under each upcoming event page's summary: `Source: <filing, linked>. "<the sentence stating the date>"`. Stored quotes that were headline runs are cut to the clause carrying the date and marked with an ellipsis; nothing the sponsor did not write is added. 58 pages.
- llms.txt lists /calendar/2027.

## 5. Not done
- Bing Webmaster not checked (Chrome extension tab unresponsive this session).
- Sarepta 2027 dates (above) unverified.
