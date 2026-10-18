# Audit: the site has not deployed since Saturday evening and nobody was told; every prior order is now verified actioned; where the moat is, measured against ten competitors
**2026-10-18, measured 17:17 to 17:45 Eastern = 21:17 to 21:45 UTC (Sunday).** *Per RULE 1 every time carries its zone. GitHub run times are UTC.*
**Live build `02162f254`, generated 2026-10-17T23:19:59Z (19:19 Eastern Saturday). API 475 rows. `as_of_eastern` 2026-10-18 (computed per request). `held_leads` []. Next decision GSK bepirovirsen 2026-10-26.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. P0: both Sunday rebuilds were blocked by a guard, and no one was notified

GitHub Actions, public API, read at 21:20 UTC:

| Run | Trigger | Commit | Result | Failed step |
|---|---|---|---|---|
| 39132717124 | schedule, 13:42 UTC | `be724e191` | **failure** | "CI guards — BLOCK the run (no commit, no deploy) if any hard-fails" |
| 39140611287 | schedule, 15:28 UTC | `be724e191` | **failure** | same |
| 39078180600 | dispatch, 10-17 23:13 UTC | `02162f254` | success | (this is what is live) |

`be724e191` is CI's own "chore: daily data refresh 2026-10-17" commit (300 files, 23:21 UTC Saturday), made by the successful run. The next two scheduled runs then failed their guards on that tree. **I cannot read the guard's name**: job logs need repository admin rights, and the Chrome GitHub tab is not signed in. The run page shows only "Process completed with exit code 1" and a `git` exit 128 warning.

**Consequences visible now:**
- No deploy for 22 hours. `/fda-decisions-today` reads "No FDA decision… published today, **October 17, 2026**" on Sunday October 18. The freshness strip says "Data as of Oct 17, 2026 7:19 PM ET". Both are honest about the build time, which is the point: the build is a day old.
- No GitHub issue was opened. The quarantine system opens issues for held leads (#31 to #33 this week); a hard-failed guard opens nothing. This is the 09-28 freeze pattern again: the mechanism that stops a bad deploy is also the one that stops all deploys, silently. A 10-15 note already said "a held row was designed to freeze one row and let the site deploy; it froze every deploy." A guard hard-fail is the same shape with no notice at all.
- The 20:00 Eastern run tonight will fail too unless the tree changes.

**Two more items on the same run page:**
- GitHub annotation: *"The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026."* That is tomorrow. The workflow runs on `ubuntu-latest`. Pin it to `ubuntu-24.04` before the migration adds a second unknown on top of the first.
- The builder's 10-17 note: `VERCEL_TOKEN does not authenticate ("User not found")`, so the post-push CDN purge is not running. **David: re-create the token** (vercel.com/account/tokens) and update the repo secret. I do not handle the token.

**Order 0:** read run 39140611287's guard output, fix the tree or the guard, dispatch, and confirm `/build-info.json` `built` advances. Then: **a hard-failed guard run must open or update one GitHub issue** ("BLOCKED: run {id} failed {test names}") so a freeze is never silent again. Guard the guard: a replay that fails a test must produce the issue body.

---

# 1. LEDGER: EVERY ORDER FROM 10-04 TO 10-17, VERIFIED LIVE TODAY

| Audit | Item | Live state 10-18 |
|---|---|---|
| 10-04 | Exclusivity stylesheet | 1,412-char hub stylesheet. **Done** |
| 10-04 | `/adcomm` one count | "187 … 2 votes". **Done** |
| 10-04 | 13F headed table | On 436 pages. **Done** |
| 10-04 | Freshness strip Page/Data split | "Page updated Oct 17 … Data as of Oct 17, 2026 7:19 PM ET". **Done** |
| 10-04 | Chart caption FDA day | "Announced 9/28/26 (FDA action 9/25/26)". **Done** |
| 10-04 | ⌘K pill mobile | 44px icon below 480px per builder; not re-rendered today. **Accepted** |
| 10-06 | Tecentriq status sentence | Decided pages now carry rewritten meta. **Done** |
| 10-06 | `fda approval decision biotech` page | `/fda-approval-decisions-this-week`, lede "for biotech and pharma". **Done** (see §3 on why clicks are still 0) |
| 10-08 | MRK withdrawn, watchers hear withdrawals/extensions | Withdrawn on all surfaces; `OTHER_OUTCOME` classifier. **Done** |
| 10-08 | MRK/RHHBY feeds | HTML newsroom readers; gene.com caught Tecentriq and Enspryng. **Done** |
| 10-10 | Remibrutinib published; 2.5-day latency explained | NVS feed added, 4th watcher pass. **Done** |
| 10-10 | One page per pending row (evERA, SUMMIT) | Both live. **Done** |
| 10-10 | API `url` → event page | **Done** |
| 10-10 | Enspryng copy, Event schema | **Done**, then decided meta rewritten 10-17 |
| 10-10 | Neladalkib month precision | "Nov 2026". **Done** |
| 10-11 | Miner R1 to R6 fixes; R7 merge rule | Builder note documents each; 131 registry rows held back. **Done, pending David's ruling on the 131** |
| 10-11 | Past readout windows resolved | 2 bare "Window passed" of 340; 79 dated "no topline". **Done** |
| 10-11 | `/readouts` starts current month, full-sentence description | **Done** |
| 10-11 | Conference pages with organiser dates | 38 pages, AASLD verified. **Done** |
| 10-11 | Strip real time; `/crl` title | **Done** |
| 10-13 | `/fda-decisions-today` Eastern "today" | **Done**, and `TZ` at job level. Today's "October 17" is the freeze (§0), not the clock |
| 10-13 | Prioritised submission | CI log shows hubs 2nd and 3rd, HTTP 200. **Done** |
| 10-13 | lastmod churn | Hash regex fixed. **Done** |
| 10-13 | VTRS/IRD partner page | One page, canonicalised. **Done** |
| 10-16 | Enspryng published, unsourced FDA day | **Done** |
| 10-16 | Calendar month sentences ordered/counted | **Done**; 11 contradicting calendar rows also fixed |
| 10-16 | September backfill (Onswik, Degevma, Welireg+Lenvima, Olumiant) | Pages live. **Done** |
| 10-16 | `/calendar` title "FDA Calendar 2026" | **Done** |
| 10-17 | Decided event pages: meta rewritten, Event dropped | 10 of 10 I re-swept clean (two 404s are retired slugs that redirect). **Done** |
| 10-17 | Brand-first RYZUMVI titles, 154-char descriptions | **Done** |
| 10-17 | Bing accepts hubs each run | CI log quoted. **Done** |
| 10-17b | PBYI/VYGR noindex | **Not done**: both still `noindex,follow` |
| all | `goal_date_held` field | **Not done**: absent from API and `/developers` |
| all | Jaypirca SUPPL-5 date, RXC-005 aliases | Aliases gone (**done**); page still says Dec 3, 2025 (ruling pending) |
| all | AZN Ultomiris, NVO CagriSema, NVO Mim8 sources | Still the only 3 unsourced upcoming rows (David) |

**31 items verified done, 2 open for the builder (PBYI/VYGR noindex, `goal_date_held`), the rest David's.** Currency outside the freeze is clean: 0 past-due, 0 non-day dates, 0 conference mislabels, 31 of 31 day-dated upcoming rows sourced, 32: 21/10/1 consistent.

---

# 2. THE MOAT, MEASURED

I profiled ten competitors today (fetched live; detail in the research notes). The honest picture:

## 2a. Where we are ahead, and by how much

| Capability | pdufa.bio | Nearest competitor |
|---|---|---|
| **FDA action date distinct from the sponsor announcement, from Drugs@FDA letters** | 32 decisions with both dates sourced; pages refuse to state an FDA day the record lacks (Enspryng, RYZUMVI) | regardsofwallstreet shows "FDA acted" vs target for ~6 rows; biopharmsignal and trialfriend both call Roche's Oct 16 press date the "decision date". **Nobody else separates the two at scale.** |
| **Outcomes current within hours** | Enspryng, RYZUMVI, Anktiva each live same day or next morning | theraradar still shows Enspryng **pending** three days later, page "updated 2026-08-02"; dansfera has five past events "Outcome Not Yet Recorded"; novapharmanews lists June dates as upcoming |
| **Decision-timing statistic from a census** | 32 sourced, four surfaces, `/llms.txt` | bioradar/dansfera publish base-rate "probability" numbers, not measured outcomes |
| **Withdrawn / extended as first-class outcomes** | Withdrawn status, `date_history` on extensions | regardsofwallstreet shows "Was: {date}"; nobody else |
| **Readout windows resolved after they pass** | 79 dated "no topline as of", 6 sponsor releases, 14 Reported | nobody does this |
| **Volume** | 475 rows: 91 PDUFA, 340 readouts, 42 conferences, 187 AdComm notices, 458 CRLs, 82 letters | biopharmsignal ~8 PDUFAs/month; regardsofwallstreet ~6 upcoming; theraradar 34 |
| **AI grounding** | 16.2K Bing AI citations, 56 grounding queries, 653 citations on 10-16 (series high) | not measurable for them, but Bing's "this week" answer is built from our today page |

## 2b. Where competitors have something we do not

| Feature | Who has it | Our state | Verdict |
|---|---|---|---|
| **Per-ticker / per-condition alerts** (email, webhook) | biopharmsignal (Slack/Discord webhooks), trialfriend (email per condition), bioradar | Pro has webhooks per `pro_features`; no free email alert | **Build the free version.** "Email me when the FDA decides on {drug}" is the single most-wanted thing on a decision page and the thing that brings a reader back. It also builds a first-party list, which no AI answer can disintermediate. Needs SMTP (David's carried item) |
| **Free JSON/CSV export with per-row source and licence** | regardsofwallstreet (CC BY 4.0) | API exists (anonymous tier, 500 rows); export is Pro | Keep the API; add a **CSV of the decided-2026 census** (goal, FDA day, source URLs, margin) under CC BY 4.0 on `/research/fda-decision-timing`. A citable dataset earns the links Bing says we lack, and the 10-17b note already asked for it |
| **.ics calendar feed** | theraradar (free) | `.ics` is Pro | Consider a free `.ics` of **goal dates only** (no run-up data). The run-up series is the paid asset; the dates are public facts and the feed is a subscription that re-fetches us daily |
| **Historical outcomes database with filters** | biopharmawatch (5+ years), bioradar | `/decisions` 477 tracked; `/crl` 458; by-year pages? | Make `/decisions/2026`, `/decisions/2025` first-class with counts, outcomes, and the margin column; title "FDA decisions 2025: {n} approvals, {n} CRLs, dated from FDA letters" |
| **Stock move context on each row** | marketbeat (30-day sparkline), bioradar | cohort medians in API; run-up charts per event | Already have more than they do; **surface the cohort median in the row text** on hubs (one sentence), since AI answers lift sentences not charts |
| **Public API + MCP connector** | biopharmawatch ($99/mo, PoA field) | Free API; MCP for 9realms is internal | A **public read-only MCP server** over the free API is cheap given the internal one exists, and would make pdufa.bio the default tool an agent calls. That is the citation channel of 2027 |
| **Extension tracking shown inline ("Was: Aug 22")** | regardsofwallstreet | `date_history` exists in API; event pages show it? | Show "Goal date moved: {old} → {new} ({source})" on the event page and calendar row for every row with `date_history` |
| **Probability of approval** | bioradar, biopharmawatch, dansfera | None, by rule | **Keep refusing.** It is the thing that makes their pages unquotable by a careful reader and liable when wrong. Our line is the measured statistic |

## 2c. Accuracy as the moat: what to publish about it

Every competitor I read today carries at least one visibly wrong or stale fact (theraradar's pending Enspryng, dansfera's NUVL after the GSK acquisition, novapharmanews's June dates, rttnews's Welireg row pending beside Merck's approved row). We have had our own (the 10-15 correction pass removed four false approvals). The difference we can make visible:

1. **`/corrections`**, dated, one line per fix, linking the page. Nobody else has one. It is proof of method and a page people link to.
2. **A "verified against" line on every decision page**: "FDA day: Drugs@FDA letter {date} · Announcement: {sponsor} {date} · Goal: {source} {date}". Three dates, three sources, one line. That is the sentence an AI answer quotes when it wants to be right about "October 15 or 16".
3. **Enspryng specifically**: Genentech's gene.com release is dated October 15 (South San Francisco); Roche's roche.com release is dated October 16 (Basel). biopharmsignal and trialfriend took Roche's date; we took Genentech's. Both are announcement dates; neither is the FDA's. The page should name both datelines so the "15–16" ambiguity Bing shows resolves to us.

---

# 3. SEO, BING AND AI CITATIONS

## 3a. Bing AI Performance, data to October 16

| | Oct 12 | Oct 13 | Oct 14 | Oct 15 | **Oct 16** |
|---|---|---|---|---|---|
| AI citations | 618 | 520 | 618 | 577 | **653** |
| Cited pages | 57 | 50 | 50 | 58 | 51 |

Totals **16.2K** (14.9K on 10-16), **56 grounding queries** (50). Five of the last five weekdays are above every day before October 12. New rows: **`fda approvals today` 72 citations at 46.75% share**, `fda pdufa calendar` 102 at 36.43%. Oncology-readouts share 50.09% (was 55.48%, then 51.48%): still slipping, see order 6.

## 3b. Bing web, data to October 16

**928 clicks / 39.1K impressions / 2.37%.** Oct 15: 23 / 954; Oct 16: 13 / 790. `pdufa calendar` 177 impressions / 23 clicks (13%). `sabirnetug` 52 / 8.

**`fda approval decision biotech`: 659 impressions, 0 clicks, position 6.7.** It has grown every read (172 → 250 → 387 → 453 → 477 → 659) and never converted. I now think the impressions are the AI answer box: Bing's "this week" answer cites pdufa.bio eight times for this query family, and a citation in the answer counts as an impression with no click. If so, this query is working as intended (we are the source) and the click will never come. The weekly page should still carry the phrase, but stop treating this as a lost click.

## 3c. Google, 28 days to October 16

27 clicks, 2.98K impressions, 0.9%, position 7.7. Flat. Google is a second-order channel for us until the link profile changes (10-17b §3).

---

# 4. ORDER (specific, for the builder)

| # | Item | Acceptance |
|---|---|---|
| **0** | **Unblock Sunday's runs** (§0): read the guard output, fix, dispatch. Pin `runs-on: ubuntu-24.04`. Hard-failed guards open/update a "BLOCKED" issue naming the tests | `built` advances past 2026-10-17T23:19Z; next scheduled run green; a replay with a planted guard failure produces the issue |
| **1** | **Three-dates line on every decision page** (§2c-2), and both Genentech/Roche datelines on Enspryng | Line present on all decided pages; guard: every decided page states its sources per date |
| **2** | **`/corrections` page** from the 10-15 and 10-16 passes, dated, linked; added to the sitemap and footer | Page 200 with ≥15 entries; new corrections append automatically from a `_corrections.json` |
| **3** | **Free email alert per decision page** ("Email me when the FDA decides"): double opt-in, one message per decision, unsubscribe link. Blocked on SMTP secrets (David) | Form live; a test subscription receives the Enspryng-style message on a planted decision |
| **4** | **Census CSV** on `/research/fda-decision-timing` (CC BY 4.0; goal, FDA day, announcement day, margin, three source URLs), versioned "v32" | Download link; Dataset schema `distribution`; cited in `/llms.txt` |
| **5** | **Goal-date moves inline**: "Goal date moved {old} → {new}" on event pages and calendar rows from `date_history` | Every row with `date_history` shows it; guard |
| **6** | **Oncology readouts share** (50% and falling): the grounding query is "major upcoming Phase 3 oncology trial readouts next 12 months key companies". Make `/readouts/oncology` (or the TA filter page) say exactly that in title and lede with the count and the next five dated rows | Page titled "Phase 3 oncology trial readouts, next 12 months: {n} dated"; share re-read next audit |
| **7** | PBYI/VYGR: index hubs with ≥1 sourced row (10-17b §2) | Both `index,follow`; count printed |
| **8** | `goal_date_held` on the API and `/developers` (carried since 10-04) | Field present |
| 9 | Free `.ics` of goal dates only; `/decisions/{year}` pages; public read-only MCP over the free API (§2b): David's call on scope and order | |
| 10 | David: VERCEL_TOKEN; SMTP; 9realms MCP restart; `SEC_USER_AGENT`; the 131 registry rows; the 3 unsourced rows; Jaypirca SUPPL-5 ruling | |

---

# 5. BOTTOM LINE

**Everything ordered since October 4 has shipped and holds live**, with two small exceptions the builder can close in an hour. The site's data is the most accurate of the eleven I compared today, and it is the only one that keeps the FDA's day separate from the sponsor's press date.

**And it has not deployed since Saturday evening**, because a guard stopped it and nothing told anyone. The fix for that is the first job. The guard did its work; the silence is the defect.

**The moat is accuracy plus speed, and the way to widen it is to make the accuracy visible and reusable**: three dated sources on every decision, a corrections page, a citable census dataset, and an alert that brings readers back. Competitors sell probabilities and alerts; we can give away the facts and the alert, and keep the run-up data as the paid layer.

---
*Site read from Chrome with `cache: 'reload'`, 2026-10-18 21:17 to 21:45 UTC, against build `02162f254`. GitHub Actions and Issues read via the public API (job logs not readable without admin rights). Ten competitor sites fetched live 2026-10-18. Bing Webmaster AI Performance and Search Performance (data to 2026-10-16) and Google Search Console (28 days to 2026-10-16) read live. Not investment advice.*
