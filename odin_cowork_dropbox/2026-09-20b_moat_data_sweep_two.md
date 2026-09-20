# Second data sweep: the best fact we own is sitting in a file we already publish half of
**2026-09-20, 22:10 UTC = 18:10 Eastern = 15:10 Pacific.** *Facts and file contents only. Not investment advice.*
**Scope note: I can read the connected folder `C:\Users\dcmoo\Documents\Python\9realms` and Google Drive. I cannot see the rest of the machine. Everything below is from those two places.**

---

# 1. BOTTOM LINE

**The single most valuable fact on this disk is one number, and we are already publishing the file it lives in.** `/crl` publishes 444 complete response letters by year with their PDFs linked. The corpus on disk holds **458 letters, and openFDA labels 309 of them as belonging to applications with an approved status.** That is **67%**. We have held the editorial line that a CRL is not a rejection since this project started. This is the number that proves it, from a federal primary source, and it is not on the site.

**Google Drive is settled and I am not going to raise it again.** It holds Google Docs of chat transcripts, research write-ups and strategy plans, plus two empty spreadsheets. Today's audit auto-synced there twenty minutes after I wrote it. Drive holds prose *about* the data. It does not hold data.

---

# 2. WHAT I VERIFIED FIRST-HAND

Everything in this section I opened and counted myself.

## 2a. The CRL corpus, and the 67% fact

`CRL_corpus_openFDA_2026-08-29.json`, 5.29 MB.

```
meta.last_updated            2026-08-26
meta.results.total           458
license                      https://open.fda.gov/license/   (openFDA, public domain)

approval_status "Approved"     309   (I grepped it)
approval_status "Unapproved"   149   (I grepped it)
                               ---
                               458   matches the file's own total exactly
```

Per record: `letter_date, letter_year, application_number, letter_type, approval_status, company_name, company_rep, company_address, approver_name, approver_center, file_name` and **the full letter text** (457 of 458 carry it).

**The first record in the file is Corcept, NDA 219398, complete response dated 01/28/2026 for relacorilant.** That is the same application whose resubmission is our live December 17, 2026 PDUFA. The FDA's own stated reasons are in our hands, in full: insufficient substantial evidence of effectiveness across CORT125134-455 and -456, and a drug-induced liver injury signal. We publish the date. We do not publish what the agency said.

**There is a second, earlier snapshot**, `CRL_corpus_openFDA_2026-06-22.json`, with 439 letters. Two dated captures of the same federal release, 439 → 458, is by construction a **"CRLs released per period" series** and the beginning of a real time series. Keep capturing it on a schedule.

**And 364 source PDFs are on disk**, 241 MB, in `odin_cowork_dropbox/approved_CRLs (2)/` (216 files) and `unapproved_CRLs (1)/` (148 files), named `CRL_NDA######_YYYYMMDD.pdf`.

**What `/crl` publishes today**, read live: *"FDA Complete Response Letters: 444 released CRLs, searchable by year ... 159 are from 2024 or later."* Each row links the FDA's own PDF. **The page contains no mention of 458, 309, 149, 67%, or openFDA.** So: the page exists, it is roughly fourteen letters behind the August capture, it does not use the letter text at all, and it does not carry the one statistic that makes the archive mean something.

**One caution before anything publishes.** `approval_status` is openFDA's field, and I am reading it as "the application associated with this letter now has an approved status." That reading should be confirmed against openFDA's own field documentation before it becomes a sentence on the site, because the claim is strong and the wording has to be exactly what the field means. The letter text is also OCR'd from scanned PDFs, with redactions rendered as `(b) (4)` and occasional garbled characters, so any quotation must be checked against the linked PDF rather than pasted from the JSON.

## 2b. AdComm: we publish 2 meetings and hold 140, but the 140 are thinner than they look

`/adcomm` says so in its own words: *"This page lists 2 FDA advisory committee meetings covering July 2026."*

`Odin Perfection/fda_adcom_historical_meetings_2020-2026.csv` holds **140 rows, 2020-01-06 onward.** I read the header:

```
pub_date,title,doc_num,fr_url,abstract
```

**That is meeting notices, and only notices.** There is no vote, no company, no drug, and no meeting-date column. The committee name is inside the `title` string and the meeting date is inside the `abstract` prose. The two votes on our page today (CAPR 3-9 against, REPL 10-3 favorable) did not come from this file and cannot come from it.

So the honest version: this fills a historical AdComm **calendar** with citable Federal Register URLs, after a parsing pass to pull committee and date out of text. It does not fill a vote history. Votes remain hand-sourced work. I am flagging this because the subagent inventory I commissioned reported `committee` and `meeting_date` as columns and they are not there, which is exactly why I open the file.

---

# 3. THE REST OF THE INVENTORY

**Reported by the subagent sweep, not individually opened by me. Treat counts as indicative until the builder confirms them.**

| Path | What it is | Scale | Publishable fact it could produce |
|---|---|---|---|
| `_orange_book/products.txt`, `patent.txt`, `exclusivity.txt` | FDA Orange Book full release | 48,501 products · 22,130 patents · 2,340 exclusivity rows | We already run `/patent-cliff` from this. **`exclusivity.txt` looks unused**: regulatory exclusivity expiry is a different and earlier cliff than patent expiry |
| `odin_catalyst_database.json` | Raw Drugs@FDA + 510(k) + PMA harvest | 46 MB · 2011-2026 · 13,281 PDUFA / 14,974 510(k) / 14,232 PMA | Device decisions (510(k), PMA) are a category no PDUFA competitor covers at all |
| `ctgov_t1_dataset.csv` | ClinicalTrials.gov trial design | 18,524 trials × ~117 columns | Per-readout design facts: randomised or not, masking, arms, enrolment, endpoint class |
| `v382_checkpoints/phase1_god_tier_holdings.json` | 13F holdings | **48,361 records**, larger than the 18,375 catalogued on 09-05 | The specialist-fund sentence from the 09-05 note, on more events |
| `fmp_insider_cache.json` · `form4_transactions.json` | Insider transaction bodies | 37 MB / 319 tickers · 40 MB / 502 tickers | Actual buys and sells, not just the Form 4 index we catalogued |
| `pdufa_t120_study/iv_cache.zip` | Per-ticker implied volatility history | 325 MB · 325 tickers | Supports the implied-vs-actual study from 09-05 |
| `price_cache_pdufa_6yr.json` | Daily close and volume | 41 MB · 674 tickers · through 2026-04-29 | Run-up coverage beyond the current universe |
| `daily/NEW_*.csv` | Newly discovered catalysts, one file per day | **51 files, 2026-07-15 → 2026-09-19** | A genuine change log. This is `/pdufa-date-changes` material and it is already being written every day |
| `catalysts_out/conference_presentations_history.csv` | Conference presentations with source URLs | 786 rows, each with `source_url`, `snippet`, `confidence` | Already sourced, row by row. The hard part is done |

**Empty, confirmed:** no earnings-call transcripts, no drug labels or DailyMed/SPL, no AdComm votes or briefing documents anywhere in the tree, no production EDGAR text corpus (one two-company test cache), no biotech analyst rating history, and no ClinicalTrials.gov protocol-change snapshots. `ctgov_t1_dataset.csv` is a single point-in-time pull, so we cannot show how a trial's design or completion date moved over time.

---

# 4. TWO RISKS TO ACT ON BEFORE ANYTHING ELSE

**`full database.xml` is DrugBank, 1.94 GB, exported 2026-01-04.** DrugBank is licensed CC BY-NC with a separate commercial licence required. **pdufa.bio sells a Pro tier at $10 per month, which makes the site commercial.** Nothing derived from that file should reach the site, or the API, or a model whose output reaches either, until someone has read the licence. I am not a lawyer and this is not legal advice; it is a flag that the file's terms have to be checked before use, not after.

**`Odin Perfection/adcom_baserate_v1.json` is a hand-authored assumption file.** It carries per-committee `yes_rate` values tagged `"rule_based_v1_baserate"`. Those are estimates somebody typed, not observed vote tallies. If that file ever reaches a page it publishes a fabricated approval probability, which breaches the no-odds doctrine at its most load-bearing point, and it would do so on a page about advisory committees where a reader would most reasonably assume the number was counted. Recommend it is renamed or moved out of any directory a build script walks.

---

# 5. DATA-INTEGRITY DEFECTS FOUND IN PASSING

- `Odin Perfection/smart_money_v2_cache.json`, 109.8 MB, is **truncated**: JSON parsing fails with an unterminated string near the end of the file. Whatever wrote it did not finish.
- `ctgov_t1_raw_studies.json` is **0 bytes**.
- `Odin Perfection/fda_adcom_federal_register.json` is **mis-scoped**: it contains FEMA and Federal Railroad Administration notices, and its `meeting_date` field holds document numbers such as `"2026-08265"` rather than dates. Unusable. The CSV in section 2b is the clean version of the same idea.
- `daily/readouts_~0,8.csv` is a junk filename in an otherwise clean daily series.
- `odin_bruteforce_all.csv` is **93.9 GB** of feature-search output. On 09-05 the disk was dominated by a 79 GB log file. One derived artifact again accounts for most of the volume.

---

# 6. THE STANDING GAP, AND IT IS THE REAL FINDING

On 2026-09-05 I identified five datasets no competitor has and wrote an ORDER: an options implied-versus-actual block, a 13F holdings block, a short-interest rebuild, Form 4 counts, and shares-outstanding deltas, all rendered as dated sentences on event pages.

**Fifteen days later, none of it has shipped.** I read three decision pages today in the course of the accuracy audit: BAYRY, TLX and RARE. Each carries the run-up chart and the cohort move. None carries a positioning block, a fund-holdings sentence, a short-interest sentence or an insider count.

That is not a criticism of the builder, who has spent those fifteen days closing genuine P0s in the date layer, and the date layer had to come first. But it should be said plainly: **the moat work has been queued behind the accuracy work for two weeks, and the accuracy work is now largely done.** The corpus passed nine of ten structural date invariants this morning and 43 of 48 upcoming rows carry a source. The reason to hold the moat items back is weaker than it was.

---

# 7. ORDER, RANKED BY MOAT PER HOUR

| # | Item | Why it ranks here |
|---|---|---|
| **1** | **Put the 67% on `/crl`, and refresh the page to 458.** One sentence, one primary source, and it is the empirical proof of an editorial position we already hold and competitors do not. Confirm the `approval_status` field definition against openFDA's documentation first, then write it as the field defines it. Add a plain-language paragraph: what a complete response letter is, and the fact that most of the ones the FDA has released went to applications later approved | Highest citation value per hour of work on the whole list. Answers "is a CRL a rejection" with a counted number |
| **2** | **Use the letter text.** 457 letters carry the FDA's own words. On each `/fda-decision/` page for a CRL, and on the drug page, publish the agency's stated deficiency categories, quoted against the linked PDF rather than pasted from OCR. Start with the CRLs already on our site: ACHV, LNTH, UNCY, and Corcept's relacorilant, whose resubmission decides December 17 | No competitor publishes the reasons. This is the deepest part of the moat and it is already on disk |
| **3** | **Schedule the CRL capture.** Two snapshots exist, 439 and 458. A dated capture per month turns a static archive into a series and gives us "CRLs released this quarter" that nobody else can compute | Costs almost nothing and compounds |
| **4** | **Parse the 140 AdComm notices into a historical calendar** with committee and meeting date extracted from the text, each row citing its Federal Register URL. **Publish it as a meeting calendar and do not imply vote coverage we do not have.** Votes stay hand-sourced | Takes `/adcomm` from 2 rows to a real archive, honestly scoped |
| **5** | **Ship one 09-05 dataset as a proof.** My recommendation is the 13F block, because the filings are quarterly and public, the sentence is purely factual, and it needs no caveat about what a price implies. Options implied-versus-actual is the bigger asset but carries the two caveats from 09-05 and should follow, not lead | Breaks the two-week queue with the lowest-risk item |
| 6 | Orange Book `exclusivity.txt`, apparently unused: regulatory exclusivity expiry is an earlier and different cliff than patent expiry | `/patent-cliff` already exists; this widens it |
| 7 | `daily/NEW_*.csv`, 51 daily files already being written, into `/pdufa-date-changes` | The data is accruing daily whether or not we use it |
| 8 | Quarantine `adcom_baserate_v1.json`; check the DrugBank licence; delete or archive the 93.9 GB bruteforce file; fix the three integrity defects in section 5 | Housekeeping and risk |

---

# 8. BOTTOM LINE

**Drive is a mirror of our writing, not a second warehouse. The disk is the asset, and the best thing on it is not the exotic data, it is a count.** Four hundred and fifty-eight complete response letters, three hundred and nine of them on applications that went on to be approved, published by the FDA itself, sitting in a file whose front half we already put on the site.

We have spent months insisting that a CRL is not a rejection, in copy, in style rules, and in how we describe every decision. **We can now show it, with a denominator.** That sentence is the kind an answer engine lifts whole, on a question people actually ask, and the only reason it is not live is that nobody has written it down.

Everything else on this list is real and most of it is useful. But if only one item ships this week, it is the first one.

---
*CRL corpus opened and counted 2026-09-20: 309 and 149 grepped independently, summing to the file's declared 458. `/crl`, `/adcomm` and three decision pages read live from a non-browser client the same day. AdComm CSV header read directly. Google Drive enumerated via the connector. All other inventory items are from a commissioned subagent sweep and are labelled as such, not independently opened. Not investment advice.*
