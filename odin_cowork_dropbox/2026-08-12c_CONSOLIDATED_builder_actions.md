# pdufa.bio — CONSOLIDATED BUILDER ACTIONS
**2026-08-12 · everything from today in one file · all claims re-verified live**
*Supersedes today's two earlier audit files. Read with `PLAIN_LANGUAGE_SPEC_AND_REDTEAM_PROTOCOL.md`.*
*Facts and historical statistics only — not investment advice.*

---

# 🔴 THE THREE THINGS THAT MATTER

| | What | Why now |
|---|---|---|
| ~~**1**~~ | ~~Bing API migration~~ **WITHDRAWN 2026-08-12 — this was my error.** See the correction note. `api.svc/json` is the surviving protocol, not the legacy one; SOAP/POX are what retire, and this file has zero of those. **No action.** | — |
| **1** | **`/calendar` publishes a number our own API contradicts** | It's inside `FAQPage` — we are actively feeding it to AI engines |
| **2** | **90%+ of the mined conference-presenter corpus is historical, not upcoming** | Publishing it as-is would put ~90 false statements live |

Everything else is upside.

---

# 1. SCORECARD — the builder's last pass

| § | Item | Status | Evidence (live, cache-busted, today) |
|---|---|---|---|
| 2.1 | `FAQPage` on 10 hubs | ✅ | `FAQPage=1` on all 10 + homepage (was 0/10) |
| 2.2 | Drug Q&A 2 → 5–6 | ✅ | rusfertide 5, deramiocel 5, zoryve 6, mk-6240 4 |
| 2.3 | `Dataset` schema | ✅ | `/research`=4, `/developers`=1 |
| 3 | Freshness | ✅ | `dateModified` **2026-08-12T18:00** sitewide (was 08-08 on `/calendar`) |
| 4.2 | Drug pages 400–600w | ✅ | 421–587w (was 337–380) |
| — | Plain-language spec | ✅ | fixed at source + CI **guard 41** |
| — | Conflict-marker guard | ✅ | CI **guard 42** |
| — | `BreadcrumbList` sitewide | ✅ | `bec2d6f` |
| ~~1.1~~ | ~~Bing legacy API~~ | ✅ **WITHDRAWN — my error** | `grep -c "api.svc/soap\|api.svc/pox"` → **0**. JSON is the migration *target*; the file was always compliant. |
| 4.1 | Per-event PDUFA URLs | ❌ | `/pdufa/LNTH-2026-08-13` → 404 |
| 4.3 | `/compare/` | ❌ | 404 |
| — | Patent cliff | ❌ | `/patent-cliff`, `/patents`, `/exclusivity` → 404 |

The freshness fix was implemented as relative tokens ("tomorrow") + live counts rather than "in N days". **That's better** — the page genuinely changes daily, so the stamp is honest rather than cosmetic.

---

# 2. 🔴 PAGE AND API STATE DIFFERENT NUMBERS

`/calendar` publishes, and marks up as a quotable `FAQPage` answer:

> *"67 FDA decision dates are on the 2026 calendar; 52 are still ahead as of August 12, 2026."*

Our own API, identical window:
```bash
curl -s "https://www.pdufa.bio/api/v1/pdufa?from=2026-06-01&to=2026-12-31&limit=500"
# meta.total = 64   (page says 67)   ·   Upcoming = 46   (page says 52)
# returned=64 — no truncation
```

**Two defects:**

**(a) The counts contradict.** The page's arithmetic is internally consistent (52 ahead + 14 decided + 1 lapsed = 67), so the page believes itself — but one of two public surfaces is wrong.

**(b) The FAQ drops the window.** Page body: *"covering **June 2026 to December 2026**."* FAQ: *"on the **2026 calendar**."* Half a year silently becomes a full year. That's a §1.4 spec violation — the number is right for its window and the window went missing.

**Fix:** derive the FAQ numbers from the same query the API answers, keep the window in the sentence, and add a CI guard asserting page count == API count for the same window. Mechanical, no judgement.

> This is the general risk the FAQ work introduces: a wrong sentence in `FAQPage` isn't just wrong on the page — it's *offered up* to be repeated.

---

# 3. 🔴 CONFERENCES — the data isn't stale, it's unfit to publish

You flagged conferences as stale. It's worse and better than that.

## 3.1 What's actually on the site

| | Repo | Live site |
|---|---:|---:|
| Conferences | **41** (`conferences.json`, verified 2026-08-03, runs to Jun 2027) | **14** (Aug 28 – Dec 12 2026 only) |
| Presenters | **102 rows** (`conference_presenters_mined.csv`) | **0** |
| Companies named | 102 | **0** — every API row has `company: null` |

Every conference row carries `updated_at: 2026-07-11` — one batch, never refreshed.
**No 2027 events are live at all**, though the repo has ASCO GI (Jan 21), WORLDSymposium (Jan 31), ASCO GU (Feb 11), AACR (Apr 2), AAN (May 1), ASCO (Jun 4), EHA (Jun 10), ADA (Jun 18).

**And `/conference/ASH` is titled "Biotech Presenters & Dates" while naming zero presenters.** We promise presenters in the title and deliver none. That's the mismatch a reader notices.

## 3.2 I ran the miner. Then I read the sentences.

`conference_presenter_miner.py` is a good tool — SEC-gated, keeps the filing URL and the matched sentence. **Keeping that sentence is the only reason this was catchable.** I ran it fresh (`--days 240`): 9 new rows, 102 total.

Then I read all 102 matched sentences. **Fewer than 10% are about an upcoming conference.**

| Verdict | Count |
|---|---:|
| Manually verified forward-looking, correct edition | **9** |
| Historical, wrong edition, or non-conference noise | **~93** |

Real examples now sitting in the file:

| Row | Matched sentence | Reality |
|---|---|---|
| REPL → SITC 2026 | *"In **November 2023** we presented initial data from ARTACUS…"* | SITC **2023** |
| CRSP → AHA 2026 | *"In **November 2025**, we presented positive follow-up data…"* | AHA **2025** |
| CABA → ACR 2026 | *"Data … presented at **ACR Convergence 2025**"* | ACR **2025** |
| ZYME → ASCO GI **2027** | *"Late-breaking HERIZON-GEA-01 data presented at ASCO GI **January 8, 2026**"* | ASCO GI **2026** |
| GLUE → ASCO GU **2027** | *"Present updated data … at ASCO GU in **February 2026**"* | ASCO GU **2026** |
| LYEL → ASH 2026 | *"…necessary for the fair **presentation** of the Company's financial position…"* | **not a conference at all** |

## 3.3 Two distinct bugs

**Bug A — tense.** `PRESENT` matches `present|presented|presenting`. A 10-K Business section recites years of conference history in the past tense; every sentence matches.

**Bug B — edition mismatch (the worse one).** The miner matches a conference by **name**, then attaches the **next future occurrence**. It has no concept of *which edition* the sentence means. So a January 2026 ASCO GI reference gets filed under ASCO GI **2027**. This bug produces rows that look perfectly forward-looking and are wrong by a full year.

Source-type signal (useful, not sufficient):

| Filing type | good | bad |
|---|---:|---:|
| 10-K / 10-Q body | 5 | 40 |
| EX-99.1 press release | 13 | 19 |
| 424B prospectus | 1 | 4 |

10-K/10-Q Business sections recite history **by design**. Press releases announce.

## 3.4 The reframe that matters

**`/conferences` shows zero presenters because the pipeline never published this file — and that was the right outcome.** The gap you read as staleness is a safety valve that held.

**So: do not "fix the display" first.** Wiring `build_conferences.py` to the current CSV would ship ~93 false statements — "REPL is presenting at SITC 2026" when they presented in 2023 — onto pages titled *"Biotech Presenters"*, at the exact moment we're feeding `FAQPage` answers to AI engines. That's an S1 across ~93 rows.

## 3.5 Miner fix spec

1. **Anchor on the edition, not the name.** Require, within ±200 chars of the conference mention, either the conference's own year, or a month inside its date window with no conflicting year. **Reject on any other 4-digit year near the mention.** This alone kills Bug B.
2. **Require forward commitment in the same clause** as the conference name: `will present` · `will be presented` · `to be presented` · `selected for` · `accepted for` · `plans to present` · `expected to present` · `abstract accepted`.
3. **Reject past-tense governing verbs** in that same clause (`was/were presented`, `we presented`, `recently featured`).
4. **Require proximity.** LYEL matched "fair presentation" in accounting boilerplate — the verb must be near the conference name, not anywhere in the sentence.
5. **Down-weight 10-K/10-Q bodies**; prefer 8-K / EX-99.1.
6. **Require a ticker** — 14 rows have none (NewAmsterdam, BMY, Kiora, Humacyte, Inventiva, HUTCHMED, BriaCell…).
7. **Emit `edition_year` + `confidence`**, and have `build_conferences.py` publish only `high`.
8. Fix `pres_type`: "plenary **poster**" is being tagged `oral/late-breaker` (ENTX); "to be presented in an **oral** session" is being tagged generic `presentation` (XNCR).

**Then add a guard:** no presenter row publishes unless its `conf_start` year matches a year cited in its own matched sentence.

## 3.6 What you can publish today — 9 rows, hand-verified

`catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv` — I read every filing sentence individually.

| Conference | Date | Ticker | Company | Drug | Evidence |
|---|---|---|---|---|---|
| ESC | Aug 28 | IONS | Ionis | — | "results **will be shared** … at ESC Congress in **August 2026**" |
| WCLC | Sep 12 | BNTX | BioNTech | — | "**expected to be presented** at the IASLC **2026** WCLC, Seoul" |
| EASD | Sep 28 | IBIO | iBio | Activin E | "full data **will be highlighted** … at the **2026** EASD Annual Meeting" |
| EASD | Sep 28 | SANA | Sana | — | "**will be presented** at the EASD Annual Meeting **2026** on October 2" |
| EASD | Sep 28 | IPSC | Century | CNTY-813 | "**selected for oral presentations** … EASD **2026**, Milan, **Presentation #225**, Oct 2" |
| ASBMR | Oct 9 | ENTX | Entera Bio | EB613 | "**selected for a plenary poster presentation** at ASBMR **2026**" |
| ESMO | Oct 23 | XNCR | Xencor | XmAb819 | "**to be presented in an oral session** at ESMO **2026**" |
| ESMO | Oct 23 | ZLAB | Zai Lab | ZL-1310 (zoci) | anticipated-milestones table, initial Ph1 at ESMO |
| CTAD | Nov 16 | CRVO | CervoMed | — | "**look forward to reporting** additional biomarker data … at CTAD in November" |

**Rejected on review: MOLN/ESMO** — the captured sentence never establishes an ESMO 2026 presentation. Unverifiable ⇒ not published.

The IPSC row is the shape to aim for: **abstract number, room, date, and time**, straight from an 8-K.

## 3.7 Also publish the calendar you already have
Push all **41** conferences live, including the 2027 block. `conferences.json` is organiser-verified and already carries the right disclosure discipline — JPM 2027 is deliberately omitted with a stated reason. **Say on the page that the presenter list is built from company filings and is not the organiser's programme.** That sentence is both honest and quotable.

---

# 4. RED TEAM — plain language holds

Never-say sweep across `/`, `/calendar`, `/decisions`, `/drug/rusfertide`, `/drug/deramiocel`, `/drug/zoryve`, `/ticker/RARE`, `/adcomm`, `/glossary`, `/learn/why-cross-trial-comparisons-mislead`:

```
CRL…rejection | rejection letter | FDA rejected | was rejected
| denied approval | cure rate | success rate     →  0 hits, all 10 pages
```

`/decisions` is the best sentence on the site — keep it verbatim:
> *"We do not publish an overall approval rate. 307 of the 457 records are price-inferred, and a rate computed over unverified outcomes would be false precision."*

**On guard 42:** conflict markers were live on the homepage for a day, through 41 guards, and the *owner* caught it. The general lesson is worth keeping: **guards that assert what must be true never catch what should never appear.** Both kinds are needed.

### My own corrections this session (protocol §2.5)
1. **I reported the public API as failing — wrong.** The 400s were my own cache-buster param. All five documented endpoints return 200. The strict validation is good design (names the bad param, lists valid ones, links docs, returns `request_id`).
2. **A calendar regex of mine produced 32 phantom page-vs-API discrepancies** by crossing row boundaries. Discarded. The 67-vs-64 finding does not depend on it.
3. **My first "clean" conference set was itself contaminated.** I applied a year-based filter, got 26 rows, then read them and found most were wrong-edition. I cut it to 9 by hand. **A filter I trusted for one pass was wrong** — which is the argument for keeping the matched sentence in the CSV permanently.

### Minor, real
`/api/v1/dataset.mjs` returns HTTP 500 on 5/5 probes. **S4** — nothing links it (`/developers`, `/llms.txt`, `/research`, `/sitemap.xml` = 0 refs). Route it away or 404 it.

---

# 5. INFORMATION ARCHITECTURE

## 5.1 The nav is full

```
Calendar · Decisions · Readouts · Run-up · Stocks · Drug Index · Conferences ·
Advisory Committees · Screener · Research · API · SLS tracker · Account · Pro
```
**14 items.** Patents makes 15. Past ~7, a nav stops being navigation. Regroup:

| Group | Contains |
|---|---|
| **Calendar** | Calendar, Decisions, Readouts, AdComm, Conferences |
| **Explore** | Drug Index, Stocks, Screener |
| **Patents** ⭐ | patent-cliff hub |
| **Research** | Research, Run-up, **Learn, Glossary, Methodology** |
| **API** | Developers |

`SLS tracker` is a campaign, not a section — homepage, not permanent nav. **14 → 5.**

## 5.2 Patents: yes, its own tab

Different clock (years, not days-to-catalyst), different question (revenue and M&A, not approval), different source and cadence (Orange Book, monthly), and big — **1,319 brand NDAs, 427 losing exclusivity 2026–2031.**

```
/patent-cliff                 hub — by year · company · therapeutic area
/patent-cliff/2027            "64 drugs lose patent protection in 2027"
/patent-cliff/company/abbvie  AbbVie's 14
/drug/{name}  →  "Patent protection" module on the 310 existing pages
```

**Hub *and* inline module — the module is the higher-value half.** Jargon in URL/title because it's the query; plain English in the subtitle:

> # 2027 Patent Cliff
> **64 drugs lose their patent protection in 2027.** This is the earliest date a generic could enter — not a guarantee one will.

That second sentence is non-negotiable on every cliff page. Guard 41 already has it dormant-armed.

## 5.3 Drug explanations: the page exists and nobody can reach it

`/glossary` is live — **1,525 words, 14 `DefinedTerm`s + `DefinedTermSet`**. Genuinely good. But:

```
inbound nav links:  /glossary 0   ·   /learn 0   ·   /methodology 0
/drug/rusfertide links /learn/* but NOT the glossary
```

Three explainer surfaces, all orphaned. And coverage is regulatory-only:

| Covered | **Missing — every clinical term** |
|---|---|
| CRL, accelerated approval, breakthrough, orphan, surrogate | control arm, single-arm, randomized, double-blind, placebo-controlled, primary endpoint, ORR, PFS, OS, median, hazard ratio, confidence interval, non-inferiority, 505(b)(2), Pearl Index |

**"Control arm" is not on the site.**

**Priority:**
1. **Inline, at point of use.** Readers land on `/drug/rusfertide` from search and never visit a glossary. Write the plain wording *into* the generated sentence — *"the main study gave the drug to 140 patients with **no comparison group**"*. Not a tooltip: a tooltip is a link with extra steps, and on mobile a coin flip.
2. **`/glossary` canonical**, per-term anchors (`/glossary#single-arm`) so drug pages deep-link and each definition is individually citable. Add the 15 clinical terms. Add `FAQPage` beside `DefinedTermSet` — *"what is a control arm?"* is a real query with a one-sentence answer.
3. **`/learn/{topic}`** long-form only where the misunderstanding is expensive. Two or three more at most.

**And put Glossary in the nav.**

---

# 6. ORDER OF WORK

| # | Item | Why now | Effort |
|---|---|---|---|
| ~~1~~ | ~~Bing API migration~~ — **withdrawn, my error** | no action | — |
| 2 | **Fix 67-vs-64 + restore the window** | live in FAQ schema | hours |
| 3 | Guard: page count == API count | prevents recurrence | hours |
| 4 | **Miner fix (edition + tense + proximity)** | unblocks all conference work | 1 day |
| 5 | Publish 41 conferences + the **9 verified** presenters | data already verified | half day |
| 6 | Nav regroup 14 → 5; surface Glossary/Learn/Methodology | unblocks Patents, fixes 3 orphans | half day |
| 7 | Glossary: +15 clinical terms, anchors, `FAQPage` | "what is a control arm" is a real query | 1 day |
| 8 | Inline plain language on drug pages | 310 generated pages, no new URLs | 1 day |
| 9 | `/patent-cliff` hub + `/drug/` module | prototype already runs | 2–3 days |
| 10 | `/compare/` pilot (5) | needs per-page judgement | 2 days |
| 11 | Per-event PDUFA URLs | deferred, still right | 1 day |

**4 before 5.** Publishing presenters before fixing the miner is the one action today that could do real damage.

---

# 7. BOTTOM LINE

The builder shipped the entire citation program and the plain-language spec in a day, and the spec **held under adversarial sweep** — zero violations across ten pages.

Three things need attention:

**Correction: the Bing migration item was mine and it was wrong.** `api.svc/json` is the protocol Microsoft is migrating people *to*; SOAP and POX are what retire, and this codebase has never used either. Withdrawn. **Nothing on the site has an external deadline.**

**We publish a number our own API contradicts, inside FAQ schema.** The FAQ work was right and well executed — it just raises the cost of every stale figure, because those sentences are now offered up to be repeated.

**Conferences look stale but are actually gated.** We have 41 verified conferences and 102 mined presenter rows, of which **9 are true**. The pipeline that "failed" to publish them is the reason we don't have ~93 false statements live. Fix the miner, then open the gate.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*

**Artifacts**
- `catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv` — 9 hand-verified rows, each with filing URL + matched sentence + review note
- `catalysts_out/conference_presenters_mined.csv` — 102 raw rows (**do not publish unfiltered**)
- `conferences.json` — 41 organiser-verified conferences to Jun 2027
- `patent_cliff_prototype.py` — Orange Book LOE aggregation, runs today
