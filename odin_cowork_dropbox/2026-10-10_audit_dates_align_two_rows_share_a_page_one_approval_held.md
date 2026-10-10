# Audit: the withdrawal is fixed on every surface; two decisions share a page with another date; a three-day-old approval is sitting in quarantine
**2026-10-10, measured 12:16 to 12:30 Eastern = 16:16 to 16:30 UTC (Saturday).** *Per RULE 1 every time carries its zone.*
**Live build `6185363d0`, generated 2026-10-10T00:29:40Z (20:29 Eastern, Friday). API 460 rows, `as_of_eastern` 2026-10-10, `data_built_at` matches the build. `next_ticker` RHHBY 2026-10-15, `next_days` 5.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE P0 IS CLOSED, VERIFIED ON 12 SURFACES

The builder's 10-09 note is confirmed live, cache-busted, from the browser:

| Surface | Live |
|---|---|
| API `pdufa_mrk_2026-10-10` | `status: "Withdrawn"`, `withdrawn_date: "2026-09-25"`, `decision_date: null`, `days_to_decision: null`, `url` → the event page |
| `/build-info.json` | next RHHBY 2026-10-15; MRK gone |
| Homepage "Next FDA decisions" | RHHBY 5 days, IRD 7 days, VTRS 7 days |
| `/calendar` October sentence | "In October the FDA is due to decide on Bepirovirsen (GSK, Oct 26)." (was "Ifinatamab deruxtecan (MRK, Oct 10)") |
| `/fda-this-month` | "Withdrawn before a decision: Ifinatamab deruxtecan (I-DXd) (MRK): the application was withdrawn by the sponsor on September 25, 2026, before its October 10, 2026 goal date. No FDA decision was issued (sponsor release)." Still-ahead list starts at October 15 |
| Timing statistic | 31: 20 / 10 / 1 on `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing`, `/llms.txt`; the withdrawal did not enter it |
| Status vocabulary | API now serves "Withdrawn" as a thirteenth status |

The builder's own retraction, that its guard reported 0 while `/calendar` and `/ticker/MRK` still carried pending language, is the right kind of note: it found the two leaks on the live pages, named the cause (step order in CI; a `not in ("decided",)` filter), fixed both, and re-proved 0 → 2 → 0 on the live HTML. The watchers now classify withdrawal, extension/major amendment and refuse-to-file, and both silent large caps have an HTML newsroom reader. The 17-row sweep through 11-30 is in the builder's note with sources; I spot-checked Enspryng, bepirovirsen and INO-3107 again today and all three stand.

**One ruling the builder asked for:** NUVL/GSK neladalkib 11-27. No primary source read gives the 27th; GSK's 6-K says "November 2026". Ruling: widen the row to month precision (`date_month 2026-11`, `date` null) with the GSK 6-K as source, and note the former day with its Royalty Pharma origin in `date_history`. A day we cannot source is a day we should not publish.

---

# 2. CURRENCY, ALL ROWS

| Check | Live |
|---|---|
| Day-precision PDUFAs past goal, not Decided or Withdrawn | **0** |
| Rows carrying a `date` at non-day precision | **0** |
| `date_month` disagreeing with `date` | **0** |
| Conferences mislabelled against the Eastern date | **0** |
| Upcoming PDUFAs with a day date | 35, **35 with `source_url`** |
| Upcoming at month precision, unsourced | AZN Ultomiris (2026-12), NVO CagriSema (2026-12), NVO Mim8 (no month). Unchanged, David's items |

## 2a. Dates align on every event page, with two exceptions that are the same defect

I took every upcoming day-dated row (35), found its event page, and compared the page title against the API date. **33 of 35 titles carry exactly the row's date.** The two that do not:

| Row | API date | Page it resolves to | Page title date |
|---|---|---|---|
| `pdufa_rhhby_2026-12-18` Giredestrant (+ everolimus), evERA | **Dec 18, 2026** | `/pdufa/RHHBY-giredestrant` | Nov 30, 2026 (the lidERA row) |
| `pdufa_cogt_2026-12-30` Bezuclastinib (CGT9486), SUMMIT | **Dec 30, 2026** | `/pdufa/COGT-bezuclastinib` | Nov 30, 2026 (the PEAK/GIST row) |

Two drugs each have two pending applications a few weeks apart, and the site has one event page per drug slug. The Dec 18 and Dec 30 rows exist in the API, on `/calendar` and on the ticker hubs, but no page on the site states either date in a title or lede; a reader who follows the giredestrant link from the December calendar lands on a page that says November 30. The body of `/pdufa/COGT-bezuclastinib` contains no "Dec 30" at all. **Fix:** slug event pages by row, not by drug, when a drug has more than one pending row (`/pdufa/RHHBY-giredestrant-evera`, `/pdufa/COGT-bezuclastinib-summit`), and make each page name the other. Guard: every upcoming day-dated row resolves to a page whose title contains its date, 35/35.

## 2b. The API `url` field points most upcoming rows at a hub, not the event

For the Tecentriq decision the row's `url` is the decision page. For MRK it is now the event page. For **every other upcoming row** it is `/ticker/{T}` or `/pdufa/{T}`: the Enspryng row links `/ticker/RHHBY`, whose title carries no date. Anyone building on the API, and any AI agent reading it, is sent to a hub and has to find the event. Set `url` to the event page for every row that has one. This is a one-line change in `_lib.mjs` and it matters for citations: the page we want quoted is the one with the date in its title.

## 2c. A three-day-old approval is in quarantine, unpublished

`/build-info.json`: `held_leads: [{row_id: "drug:remibrutinib", source: "drug_pages", first_seen: 2026-10-10T00:27:35Z}]`, `held_since` the same. Primary source: **Novartis, October 7, 2026**, "Novartis Rhapsido (remibrutinib) receives FDA approval as first treatment for symptomatic dermographism (SD)". Healio, AJMC, Dermatology Times and Dermatology Advisor have all carried it. We have no row for it (the only remibrutinib row is a 2027 readout estimate) and `/drug/remibrutinib` lists no FDA actions.

Two things to look at. First, publish it the Jaypirca way: `/fda-decision/NVS-2026-10-0X` with the FDA day from the Drugs@FDA supplement letter (NDA 219139, if the letter is up) or the FDA record if any, `goal_unsourced`, no margin, and the drug page carries "FDA action". Second, **why did the lead arrive 2.5 days after the release?** The approval was announced Wednesday morning Basel time; the drug-page watcher first saw it Friday 20:27 Eastern. Either the Novartis feed is not in `_sponsor_feeds.json`, or the drug-page watch only runs in the nightly build. The note should say which, because the quarantine is working but the clock in front of it is slow.

---

# 3. SEO, BING AND AI CITATIONS

## 3a. Bing AI Performance, data to October 8

| | Oct 5 | Oct 6 | **Oct 7** | **Oct 8** |
|---|---|---|---|---|
| AI citations | 384 | 337 | **482** | **469** |
| Cited pages | 40 | 37 | **58** | **58** |

Totals **12.6K** citations (11.6K two days ago), **25** average cited pages (24). October 7 and 8 are the two best weekdays in the 60-day series after the Sep 28 spike (553), and 58 cited pages ties the series high. `pdufa date` is **1.1K citations at 22.98%** (958 / 22.87% on 10-08): the share has stopped drifting down. `fda calendar 2026` 374 at 26.45% (26.58%), still drifting. Oncology readouts query 217 at **56.81%**.

## 3b. What the next decision looks like in Bing today

`enspryng thyroid eye disease pdufa date`: **biopharmsignal first, pdufa.bio second** (event page), trialfriend third, our `/drug/enspryng` fourth. No answer box on this phrasing. Our snippet: *"RHHBY's FDA PDUFA target is Oct 15, 2026 for Enspryng (Thyroid eye disease (TED)). Date, company and indication, each linked..."* biopharmsignal's: *"FDA assigned an October 15, 2026 PDUFA goal date to the ENSPRYNG supplemental BLA for thyroid eye disease."* Theirs reads like a sentence a person would quote; ours leads with a ticker possessive and a parenthetical inside a parenthetical.

The Enspryng page itself, five days before the decision: `article:modified_time` **2026-09-02**, no Event schema (only a `WebPage` with `dateModified` 2026-09-02), no SatraGO trial names, no "status as of" sentence. **Sixty-plus upcoming event pages share that 09-02 timestamp and lack Event schema**, while the pages regenerated since 09-18 (VTRS MR-141, giredestrant, VTRS MR-107A-02, neladalkib) carry `startDate` and a current timestamp. Two generators are producing two kinds of page. This is the 10-06 item 2 and the 10-08 item 5, still open, and it now has a deadline of Thursday.

**Copy for `/pdufa/RHHBY-enspryng`, from Genentech's June 29 release (the row's source), ready to paste:**

> Description: "Roche's Enspryng (satralizumab) sBLA for thyroid eye disease has an FDA goal date of October 15, 2026, under Priority Review, per Genentech's June 29, 2026 release. Decision tracked here."
>
> Body: "The sBLA is supported by SatraGO-1 and SatraGO-2. Per Genentech, in SatraGO-2 53% of patients on Enspryng achieved a proptosis response at week 24 versus 23% on placebo, meeting statistical significance; in SatraGO-1 the figures were 49% versus 31%, which did not meet statistical significance."

Every number is a quotation from the source already on the page.

## 3c. Carried from 10-08, unchanged

`fda approval decision biotech`: 250 impressions, 0 clicks, no page of ours titled for it (item 4 of the 10-08 order). Google Search Console: 29 clicks / 3.11K impressions, position 7.3, flat. Bing's "NOINDEX" recommendation: not yet listed.

---

# 4. UX

The 10-04 order, items 2 to 10, remains unworked: `/patent-cliff/exclusivity` first `<style>` block 373 characters, `/adcomm` lede "2 meetings", RVMD 13F as a paragraph, freshness strip without the Page/Data split. Six days. The builder's last two passes were a P0 and an approval, both correctly prioritised; the stylesheet is a one-hour fix and should be the first thing after section 2c.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Remibrutinib SD approval (Novartis, Oct 7):** publish from the FDA record, `goal_unsourced`, no margin; release the hold; explain the 2.5-day lead latency | `/fda-decision/NVS-…` 200, FDA-dated; `held_leads` []; note names the slow link |
| **2** | **One page per pending row.** Giredestrant evERA (Dec 18) and bezuclastinib SUMMIT (Dec 30) get their own event pages; each page names its sibling. Guard: 35/35 upcoming rows resolve to a page whose title carries the row's date | Guard 0 → planted 1 → 0; both pages 200 with the right date in title, lede and schema |
| **3** | **API `url` → event page for every row that has one** | Enspryng row `url` ends `/pdufa/RHHBY-enspryng` |
| **4** | **Enspryng by Wednesday 10-14:** the copy in 3b; Event schema and current `modified_time` on every upcoming event page from one generator | Page carries SatraGO sentence, `startDate` 2026-10-15, timestamp this week; a count of upcoming pages still on the 09-02 timestamp, target 0 |
| **5** | **Ruling, neladalkib:** month precision, GSK 6-K source, former day in `date_history` | Row at `2026-11`, `date` null |
| **6** | 10-04 UX order, stylesheet first | Phone render of `/patent-cliff/exclusivity` styled |
| 7 | `fda approval decision biotech` weekly page; NOINDEX list; carried rulings (`goal_date_held`, Jaypirca letter date, RXC-005 aliases) | |
| 8 | David: SMTP secrets; Google Drive exclusion; AZN Ultomiris, NVO CagriSema, NVO Mim8 sources | |

---

# 6. BOTTOM LINE

**The withdrawal is gone from every surface I can reach, the watchers now hear the outcomes they were deaf to, and the AI layer cited us on 58 pages a day for two days running.** Dates align on 33 of 35 upcoming event pages, and the two that do not are one defect: a drug with two pending applications gets one page. Fix that, point the API at the event pages, and give Enspryng a sentence worth quoting before Thursday. A real approval is sitting in quarantine from Wednesday; publishing it is the first job.

---
*Site read from a browser client with `cache: 'reload'`, 2026-10-10 16:16 to 16:30 UTC, against build `6185363d0`. Bing Webmaster AI Performance (data to 2026-10-08) read live. Bing SERPs for Enspryng and remibrutinib read live; Novartis release of 2026-10-07 confirmed on novartis.com via Bing. Not investment advice.*
