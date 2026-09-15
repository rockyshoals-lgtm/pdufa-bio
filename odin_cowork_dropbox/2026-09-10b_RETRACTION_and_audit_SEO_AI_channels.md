# Retraction of this morning's P0, two more of my hypotheses tested and dropped, and the one date claim that does not survive
**2026-09-10, afternoon Pacific. Live build `75243def3`, `built 2026-09-10T14:44:45+00:00`. Server-side reads via a non-browser client; console reads live in Chrome.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. RETRACTION: the hub split was our service worker, and crawlers never ran it

**My 2026-09-10 P0 is substantially wrong and I am withdrawing it.** The builder's note `2026-09-10_BUILDER_the_split_was_our_service_worker.md` is correct, and I have now confirmed the load-bearing part independently, from a client with no service worker.

| My claim this morning | What is actually true |
|---|---|
| `/calendar` serves a June 27 snapshot at the URL our sitemap publishes | `/calendar` returns the **current** page: title "2026 FDA PDUFA Calendar: 97 Dates, Updated Daily", the full explainer, "20 came before the goal date, 9 landed on it, and 3 came after. The largest early margin was 108 days", all four month naming sentences, 49 decided rows |
| Leftover flat files shadow the directory index | The deployment has no split. Builder measured both forms on both hosts byte-identical (`/calendar` 88,181 b, md5 `b295072984`, at both). The legacy flat files exist and carry `robots: noindex,nofollow`; `/calendar` does not resolve to them |
| Canonical and sitemap are non-www | Sitemap is **1,429 locs, all www, zero non-www**; `/calendar` canonicalises to `https://www.pdufa.bio/calendar`. I was reading a June-cached sitemap |
| "Everything shipped to the hubs since late June has been invisible to search engines" | **Does not hold.** Crawlers fetch over HTTP and do not run service workers. They have the current page |
| ORDER items 1, 3, 4 | **Void.** Nothing to delete, nothing to re-canonicalise, no re-submission needed |
| The Sept 13 answer-box re-test premise | Collapsed. See section 5, where I re-read the box live and found a different explanation |

**The cause.** Our own `sw.js` v3 routed network-first only when `req.mode === "navigate"`, `.html`, `/`, or `/api/data`. Everything else went cache-first and every 200 was stored permanently. A `fetch()` from page script has mode `cors` or `same-origin`, not `navigate`, and our hub URLs are extensionless, so `/calendar` fell to the cache-first branch and was stored the first time any script asked for it. Every later fetch replayed the stored June response **with its stored June headers**, which is precisely why my probe read `age: 0`, `x-vercel-cache: MISS`, `last-modified: Sat, 27 Jun 2026` and looked like a live server answer.

**The method lesson, and it is the second cache lesson in two days.** `cache: 'reload'` and `Cache-Control: no-cache` control the HTTP cache. **Neither bypasses a service worker.** Yesterday I corrected my tooling from query-string busters to `cache: 'reload'` and called it a method fix; that fix is what produced today's false finding, because it moved me from one thing a service worker ignores to another thing a service worker ignores. Worse, I had contradicting evidence in hand at the time: `web_fetch` returned a September 9 `build-info.json` while the browser returned August 8. **Two clients disagreeing about the same URL should make the client the prime suspect, not the server.** I reasoned the other way. New rule for this series: any finding about what the origin serves must be confirmed from a non-browser client before it is written down.

**What is real, and it is the serious half.** Every returning human visitor whose browser registered the v3 worker was reading a month-old freshness stamp and a stale "next decision" (LNTH, 2026-08-13). On a site whose product is the date, that is a genuine defect, it ran for weeks, and our own checks could never see it because our checks are curl. Fixed in `sw.js` v4: documents, JSON, the API and all extensionless paths go to network always; cache-first restricted to an image and font allowlist that additionally refuses anything whose `destination` is `document`; cache name bumped to `pdufa-v4` so poisoned v3 caches evict on the next visit with no user action. Guard `tests/test_sw_never_caches_documents.py`, proved 0 to 1 to 0.

**My item 2 survived and the builder kept it**: the post-deploy verifier now compares no-slash against slash bytes on every static graded page and passed on all four eligible paths. The server-side version of that fault is real even though it is not what happened, and it would look identical from outside.

---

# 2. TWO MORE HYPOTHESES I FORMED TODAY, TESTED, AND HAD TO DROP

I am recording these because the pattern this session is that my shape-based suspicions keep failing, and the failures are as informative as the finds.

## 2a. "MIRM and INCY both list zilurgisertib on 2026-09-26, so one is a misattribution"

Both rows do carry the same drug and the same date, and Mirum's pipeline is bile-acid and liver disease while zilurgisertib is an ALK2 inhibitor. I was ready to call it a P0.

**It is correct.** Mirum's 8-K of 2026-08-05 (EX-99.1) states plainly: *"The FDA has accepted the NDA for zilurgisertib in FOP under Priority Review with a Prescription Drug User Fee Act (PDUFA) date of September 26, 2026"* and *"Mirum Pharmaceuticals, Inc. licensed zilurgisertib from Incyte for worldwide development and commercialization."* The row is right, the date is right, and it is now sourceable to the sponsor's own filing.

Two real defects remain in that pair, both small:
- **Both rows publish an empty `indication`.** The filing says fibrodysplasia ossificans progressiva (FOP), an ultra-rare disease affecting roughly 300 patients in the U.S. Two of our nine empty-indication rows close with one quote.
- **The INCY row asserts that Incyte has a PDUFA date.** Incyte is the licensor; Mirum is the applicant. Keeping a licensor row is defensible, describing it as Incyte's PDUFA is not.

## 2b. "Twelve rows fall on a month-end day, so month-end is the new placeholder shape"

After yesterday's four-on-December-31 finding I counted the month-end day-precision dates: 09-30 two rows, **11-30 five rows** (BAYRY sevabertinib, COGT bezuclastinib+sunitinib, REGN cemdisiran+pozelimab, RHHBY giredestrant, VRTX povetacicept), 12-30 one, 12-31 four. Five sponsors sharing one day looked like the day-15 cluster one field over.

**Refuted by the first row I checked.** Vertex's 8-K of 2026-08-03 (EX-99.1) says in its own headline bullet *"povetacicept PDUFA date November 30th"* and in the body *"The U.S. FDA accepted the BLA submission for accelerated approval of povetacicept for adults with IgAN and assigned a PDUFA target action date of November 30, 2026."* Month-end goal dates are real and ordinary. **The shape of a date is not evidence about the date.** I should have learned this from the ERS error, where I twice called a five-day congress stale because a single day looked wrong.

---

# 3. WHAT DOES SURVIVE: two December 31 rows have no sponsor source anywhere in EDGAR

Having dropped the shape argument, I tested the four December 31 rows the only way that counts, against filings.

| Row | EDGAR full-text result | Status |
|---|---|---|
| **ABBV tavapadon (TEMPO), Dec 31** | Searching AbbVie's own CIK for "tavapadon" across 2026 returns four documents: the FY2025 10-K, the annual report, and two proxies. **No 8-K, no 10-Q, and no filing containing both "tavapadon" and "PDUFA."** AbbVie is a domestic filer; an NDA acceptance with a goal date is the kind of thing that lands in a 10-Q at minimum | **Unsourced** |
| **NVO CagriSema, Dec 31** | `"CagriSema" + "PDUFA"` across all 2026 filings returns eight hits, every one a third party (Protagonist, Vivani, Kailera). No Novo filing | **Unsourced** |
| **BAYRY finerenone (FINE-ONE), Dec 31** | `"finerenone" + "PDUFA"` returns three hits, all third party (ProKidney, Cytokinetics). **Bayer is not an SEC registrant, so EDGAR can never settle this row either way** | **Untestable by this method; needs Bayer's own release** |
| **AZN Ultomiris IgAN, Dec 31** | Not tested this session | **Open** |

**The finding, stated narrowly.** `/pdufa/ABBV-tavapadon` currently publishes "FDA decision (PDUFA) target **2026-12-31**" and answers its own FAQ with *"The FDA PDUFA target date for ABBV (AbbVie Inc.) is 2026-12-31 for Tavapadon."* That is a day-precision claim, in a schema-marked FAQ, that no sponsor filing supports. It is the same class as the 325 manufactured day-15 dates removed on 09-09, and the fix is the mechanism that already exists: `date: null` plus `date_month`, or a sourced day.

**A method correction for the builder's runs.** EDGAR full-text search is the right first move for domestic filers and for AZN and GSK, which file 20-F and 6-K. It is the wrong instrument for **BAYRY and RHHBY, which do not file with the SEC at all**. Those rows can only be sourced to the company's own release or investor deck, and a "no EDGAR hit" on them means nothing.

---

# 4. CHANNELS, READ LIVE

**Bing Webmaster, 3 months, data ends September 7.** 331 clicks, 11.1K impressions, 2.98% CTR, 563 ranked keywords. **These are the same figures as my 09-09 read, because Bing's data still ends on the same day.** Nothing has been measured since the September 8 snippet fixes. First honest read is when the window advances.

**Bing AI Performance, same window.** 3.8K total citations, average 15 cited pages, **20 grounding queries**, unchanged from 09-09. Daily citations Sept 5 to 7: 79, 87, 160.

The share column is where the interesting thing is:

| Grounding query | Citations | Our share |
|---|---|---|
| major upcoming Phase 3 oncology trial readouts next 12 months key companies | 28 | **65.12%** |
| camizestrant pdufa date | 82 | 32.03% |
| upcoming clinical trial readouts rare disease specialty pharma 2025 2026 key companies | 75 | **31.25%** |
| fda calendar 2026 | 291 | 30.83% |
| asundexian pdufa date | 24 | 28.92% |
| pdufa date | 344 | 18.23% |
| rusfertide pdufa date | 72 | 17.02% |
| povetacicept pdufa date | 9 | 20.00% |
| pdufa date for daraonrasib in usa | 14 | 8.43% |
| zanidatamab pdufa date / tavapadon fda approval date | 8 / 4 | 100% / 100% |

**Two of our three highest citation shares are readout queries, not PDUFA queries**, and neither has a dedicated page. We are being cited for "upcoming Phase 3 oncology readouts" off the `/readouts` hub at 65% share, which is the strongest share in the table by a wide margin. That is the clearest untapped content signal in this console.

Also recorded, not actionable: Bing's topic classifier labels "pdufa date" as *Holidays and Observances* and "pdufa date for daraonrasib in usa" as *Hunting, Firearms and Ammunition*. That is their classifier, not our markup.

**Google Search Console, 28 days ending September 8.** 36 clicks, 1.9K impressions, 1.9% CTR, average position 15.9, 89 queries. **I am not comparing this to the "53 clicks, 3.2K impressions" figure I have quoted in earlier audits, because that was a three-month window and this is 28 days.** Comparing them would be exactly the denominator error we publish a doctrine against. The Generative AI report is at a different URL than the one I tried and I did not reach it this session.

One oddity worth a builder minute: two of our top-ten Google queries by impressions are the literal strings `https://clinicaltrials.gov/api/v2/studies/nct04229979` (30 impressions) and its bare form (22). I checked whether we were rendering a raw API URL. **We are not.** The string appears only inside the server-side fetch in `pdufa_site_src/api/data.js`, which Vercel runs as a function and never serves as source. So this is 52 impressions of navigational noise, not a leak.

---

# 5. THE ANSWER BOX, RE-READ LIVE, AND WHAT IT ACTUALLY WANTS

With the "Bing never fetched the explainer" theory withdrawn, I re-ran the query. Bing's box for **"what is a pdufa date"** now assembles an answer from **clinicalinvestor.com, pdufapulse.com and biotech-edge.com**, under five labelled sections:

> Overview · Why It Exists · How the Timeline Works · Possible FDA Actions on a PDUFA Date · Why Investors Care

Below the box, the organic list runs Wikipedia, Motley Fool, pdufapulse, Pharmacy Times, then a **collapsed cluster of eight bare-domain entries with no titles and no snippets**: scienceinsights, biotechsign, patsnap, novapharmanews, **pdufa.bio**, lifesciencedaily. Our entry renders as a domain and a URL and nothing else, inside a group Bing closes with "Some results have been removed."

**Two things follow, and neither is the theory I retracted.**

1. **We are in the crawled set and we are being rendered without a title or description in a dedup cluster.** That is a presentation and duplication signature, not an indexing failure, and it is a different problem from the one I have been prescribing internal links for.
2. **The box is built from definitional scaffolding, and our page leads with data instead.** Our explainer's differentiator is "In 2026, 20 of 32 sourced decisions came early", which is the best sentence on the page and the one no competitor can write. But Bing did not ask for a statistic. It asked for mechanism, history, process steps, and the four things the FDA can do on the date. The three cited pages each supply all five in separately headed blocks. Ours supplies the definition and the statistic.

The competitor to study is **pdufapulse.com**, which Bing timestamps "1 day ago" and which carries the year in its title. Freshness plus a year-stamped title plus the five section shapes is the whole recipe on display.

---

# 6. ORDER FOR THE BUILDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Source or downgrade tavapadon and CagriSema.** Neither has a sponsor filing stating a goal date. If a company press release exists, cite it in `source_url`. If not, set `date_precision` to month or year, `date: null`, `date_month` populated, and let the existing 09-09 mechanism do the rest. Same treatment for AZN Ultomiris and BAYRY finerenone once checked, noting that Bayer files nothing with the SEC | `/pdufa/ABBV-tavapadon` no longer answers its FAQ with a hard day it cannot source; guard extends `test_api_no_manufactured_day` to cover December 31 the way it covers the 15th |
| **2** | **Free win: source the VRTX povetacicept row.** Vertex 8-K 2026-08-03, EX-99.1, accession `0000875320-26-000256`: *"assigned a PDUFA target action date of November 30, 2026"*, plus a headline bullet. Converts a self-sourced forward row to a filing-sourced one at zero research cost | Row carries `source_url` to the 8-K; the page shows it |
| **3** | **Source the MIRM row and fill both FOP indications.** Mirum 8-K 2026-08-05, EX-99.1, accession `0001759425-26-000044`: NDA accepted under Priority Review, PDUFA September 26, 2026, indication fibrodysplasia ossificans progressiva. Fill `indication` on **both** the MIRM and INCY rows. Re-label the INCY row so it does not assert that Incyte holds the PDUFA; Mirum licensed the asset from Incyte for worldwide development and commercialisation | 9 empty indications drop to 7; the INCY row describes the licensing relationship rather than claiming an application |
| **4** | **Restructure `/learn/what-is-a-pdufa-date` for the shape the box actually assembles.** Keep the 2026 statistic as the differentiator, but move it out of the lede and add five H2 sections answering, in one or two plain sentences each and in this order: what a PDUFA date is; why it exists (the 1992 Act, and what review times were before it); how the timeline works (submission, 60-day filing decision, standard about 10 months, priority about 6); what the FDA can do on the date (approve, issue a Complete Response Letter, extend by three months on a major amendment, or act early); and why the date matters to people tracking it. Put the year in the title. **No approval odds and no "why investors care" framing that implies a trade** | Each section is independently quotable; page keeps the 2026 timing statistic under its own heading |
| **5** | **Build the readout page the citations are already asking for.** Our single highest AI citation share, 65.12%, is on "major upcoming Phase 3 oncology trial readouts next 12 months key companies", and 31.25% on the rare-disease equivalent, both off the `/readouts` hub with no dedicated page. Build `/readouts/oncology` and `/readouts/rare-disease` as dated, sourced, editorially captioned lists with counts and coverage stated, no estimated dates presented as days | Both pages live, each with an n, a coverage sentence, and per-row sources; `/readouts` links to both |
| 6 | Carry: `source_url` / `page_url` split. MRK's source exists in the dataset and not in the API response | A consumer can see the source without visiting the page |
| 7 | Carry: `/ticker/PFE` meta description still reads "Roivant/Priovant" although the title was fixed | Description owner writes the same company as the title owner |

---

# 7. WHERE THIS LEAVES US

**Data.** The corpus is in better shape than my headline finding this morning implied, and the two suspicions I raised today both dissolved on contact with the filings. What did not dissolve is narrow and fixable: two December 31 rows publish a day that no sponsor has stated, and nine rows publish an empty indication when the sponsor's own release names it. Three of the four rows in ORDER items 1 to 3 can be closed with quotes I have already pulled.

**Guards.** 79 after the service-worker guard, up from 55 a week ago, and today's addition asserts the thing that actually failed rather than the thing we assumed had.

**Channels.** Both consoles are frozen at data that predates the September 8 snippet work, so this read establishes a baseline rather than a result. The one new signal is directional and useful: our readouts corpus is out-performing our PDUFA corpus on AI citation share, on queries we have never written a page for.

**Corrections owed, in one place.** The hub split was our service worker, not the deployment. Crawlers were never affected and the two and a half months of hub work reached them. The sitemap is all www and always was. My cache-busting method has now been wrong twice in two days in two different ways, and the fix is procedural: confirm from a second, non-browser client before writing anything down about what the origin serves.

---
*Server-side figures read 2026-09-10 against build `75243def3`. Bing and Google figures read live in Chrome; Bing data ends 2026-09-07, Google 2026-09-08. Mirum and Vertex quotes verified in the filings named. EDGAR full-text results reproduced from `efts.sec.gov`. Not investment advice.*
