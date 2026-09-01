# Strategy — more AI citations, without risking the Bing #1
**2026-08-12 · Cowork session · Amendment 033 filing**
*Built from live page teardowns of our cited vs uncited pages, and of the competitor cited where we are not.*
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — WHY SOME OF OUR PAGES GET CITED AND OTHERS DON'T

I compared our pages that **are** being cited against ours that **aren't**. The pattern is unambiguous.

| Page | Words | `FAQPage`? | Cited by AI? |
|---|---:|:---:|:---:|
| `/drug/rusfertide` | 363 | ✅ | ✅ **12 citations, 16.67% share** |
| `/drug/deramiocel` | 380 | ✅ | ✅ (in the cited set) |
| **`/calendar`** | 1,612 | ❌ | ❌ **— and it ranks #1** |
| `/decisions` | 4,255 | ❌ | ❌ |
| `/learn/why-cross-trial-comparisons-mislead` | 848 | ❌ | ❌ |

**Ranking #1 does not get you cited. Word count does not get you cited.** Our longest page (4,255 words) and our best-ranking page (#1 on Bing) are both absent from AI answers, while a 363-word drug page holds a sixth of all citations for its query.

The variable that tracks perfectly is **`FAQPage` + `Question` + `Answer` schema** — an explicit, machine-readable question→answer pair that matches what the user asked.

## The competitor check confirms it
**Assyro** — cited in Bing's AI answer for the head query *where we rank #1 and are not cited* — runs **22 schema types**, including `FAQPage`, `Question`, `Answer`, `Dataset`, `DataCatalog`, `HowTo`, `SoftwareApplication`, `Organization`, `Offer`.

Their FAQ is six banal questions:
> What is a PDUFA date? · How often is the calendar updated? · Where does the data come from? · Is the PDUFA calendar tool free? · Which application types are tracked? · Does the tool cover EMA or Health Canada review dates?

There is nothing clever there. They simply **declared the questions**. We answer all six better than they do — on `/learn`, in `/llms.txt`, in our methodology — and we get no credit because we never marked them up.

## Our current FAQ coverage
| Has `FAQPage` ✅ | Missing `FAQPage` ❌ |
|---|---|
| `/` · `/drug/*` (310) · `/ticker/*` (156) | **`/calendar`** · `/decisions` · `/readouts` · `/drug` (hub) · `/tickers` (hub) · `/learn/*` · `/research` · `/conferences` · `/adcomm` |

**Every high-traffic hub we own is missing the one thing that makes a page citable.** That's the single biggest AEO gap on the site, and it's a template change, not a content project.

---

# PART 2 — THE AI-CITATION PLAYBOOK

## 2.1 Add `FAQPage` to the nine hubs — highest leverage available
Three to five real questions per hub, each answered in **one declarative sentence with a number and a date**, because that is the unit an engine lifts.

**`/calendar`** — the #1-ranked page currently earning zero citations:
- *"How many FDA decisions are scheduled in 2026?"* → "67 FDA decision dates are scheduled for 2026, of which 52 are still ahead as of August 12, 2026."
- *"When is the next FDA decision?"* → "The next FDA decision is LNTH (MK-6240) on August 13, 2026."
- *"How often is the PDUFA calendar updated?"* → "Daily, from FDA, SEC and company primary sources."
- *"Where does the data come from?"* → name the sources.

**`/decisions`:** *"What share of FDA decisions are approvals?"* → answer with the **verified-only** number and its n, and say plainly that unverified records are excluded. That refusal is itself quotable.

**`/learn/why-cross-trial-comparisons-mislead`:** this is the most citable asset on the site and it has `Article` but **no `FAQPage`**. It is already Q&A-shaped. Mark it up.

## 2.2 Expand Q&A *per* drug page — multiply the query surface
310 drug pages × ~2 questions = ~620 answerable queries. Going to 5–6 questions each takes that past 1,800 without a single new page. Add:
- *"When is the {drug} FDA decision date?"*
- *"What is {drug} used for?"*
- *"Who makes {drug}?"*
- *"Has {drug} been approved?"*
- *"What happened at {drug}'s last FDA decision?"*

"rusfertide pdufa date" already earns 16.67% share off roughly two questions. This is the cheapest scaling lever we have.

## 2.3 Add `Dataset` schema — an uncontested surface
Assyro publishes `Dataset` + `DataCatalog`. **We publish none** — despite having CC BY 4.0 research with sample sizes and published limitations, which is *better* dataset material than theirs.

`Dataset` markup on each research page and on the API docs feeds **Google Dataset Search**, a surface with essentially no competition in this category, and it signals "structured, citable source" to every AI crawler.

## 2.4 Mine the grounding-query report weekly — this is the feedback loop
BWT now shows the exact queries citing us, with citation share. Right now it's one row. As it fills:
- Queries where share is **low** → the answer exists but isn't the cleanest available. Tighten the sentence.
- Queries where we're **absent but should win** → add that exact question to the relevant page.

This converts AEO from guesswork into a measured loop. **Nobody else in this category is running it.**

## 2.5 Answer-first prose, everywhere
The cited page opens: *"Rusfertide is a Protagonist Therapeutics Inc. program in Polycythemia vera. Its next catalyst is a PDUFA on Sep 30, 2026."* — entity, context, date, in two sentences.

Make that the house pattern: **first sentence answers the page's implied question, with a number and a date.** Tables and charts below.

---

# PART 3 — PROTECTING THE BING #1

The #1 sits on `/calendar`. Rankings this new are not fully settled, so the operating rule is: **additive only on that page.**

## 🚫 Do not touch
1. **The URL and canonical.** Not the path, not the trailing slash, not the redirect chain. A canonical change on a fresh #1 is the fastest way to lose it.
2. **The title.** *"2026 FDA PDUFA Calendar: 67 Dates, Updated Daily"* was rewritten days ago and the ranking followed. Leave it alone for at least 3–4 weeks. *(One exception: the count `67` must stay accurate — a stale number is worse than a generic title.)*
3. **The H1 and opening paragraph.** The first 400 characters are what's being matched.
4. **Page speed.** No new render-blocking scripts, no heavy embeds above the fold. CWV still shows "No data" so we have no safety margin to spend.
5. **`noindex`/robots on anything in the hub path.**

## ✅ Safe to do now
- **Add JSON-LD.** Schema is invisible to the reader and doesn't disturb the ranked content. This is why the FAQ work is low-risk and high-return.
- **Append FAQ content *below* the existing calendar table** — additive, doesn't reorder what's ranking.
- **Add the live countdown** (per the 08-12 audit) — genuine daily change, fixes the "4 days ago" snippet.
- **Build new pages.** Unlimited upside, zero risk to `/calendar`.
- **Keep IndexNow running.** Direct causal line: 108 submissions → impressions doubled.

## The one change worth making *on* `/calendar`
Its `dateModified` is stuck at Aug 8, and Bing prints **"4 days ago"** next to our #1 result while novapharmanews shows **"16 hours ago"**. On a freshness query that's the most likely way we *lose* the top spot to a rival that publishes constantly.

Fix it honestly: `/pdufa/LNTH` already renders a live "**in 1 day**" countdown. Put the same on `/calendar`, and the page genuinely changes daily — so the timestamp updates truthfully and the snippet stops undercutting us.

---

# PART 4 — PULLING AWAY FROM COMPETITORS

## 4.1 The moat they cannot copy: verified provenance
Assyro's differentiator is *"sourced from FDA primary records, updated daily."* Ours is stronger and unusual: **"449 records · 142 verified with a primary source · 307 inferred from price"**, plus a published refusal to compute an approval rate from mixed data.

Make that machine-readable. A `Dataset` with explicit `provenance` fields, and an FAQ question *"How do you verify FDA decisions?"* answered honestly, is exactly the kind of thing an AI engine prefers to cite — and no competitor will publish their own uncertainty.

## 4.2 Own the question types nobody else answers
Competitors answer **"when."** We can uniquely answer:
- **"What happened last time?"** — 449-record decision archive
- **"How much does this move?"** — run-up study with n and IQR
- **"Can I compare this drug to the incumbent?"** — the cross-trial explainer, and eventually `/compare/`
- **"Is this source reliable?"** — verified/unverified split, `/corrections`

Each becomes an FAQ question on the relevant page. That's four question families where we have data and they have nothing.

## 4.3 Ship `/compare/` now
The methodology page is live and it's the right foundation. Comparison pages are **the most citable format that exists** — AI answers love structured comparison — and per the 08-08 strategy the safe version publishes *context*, never a verdict. Start with 5 decided drugs that have a named incumbent.

## 4.4 Where NOT to fight
Don't chase Google's head terms yet. We're #1 on Bing, ~40× Google's daily click rate, and Google still has 418 pages it has never crawled. Let the redirect validation finish. **Compound where we're already winning.**

---

# PART 5 — SEQUENCE

| # | Action | Risk to #1 | Effort |
|---|---|:---:|---|
| 1 | **`FAQPage` on `/calendar`, `/decisions`, `/learn/*`** (3–5 Q each) | 🟢 none — schema only | 1 day |
| 2 | **Live countdown on `/calendar` + `/decisions`** → honest fresh timestamp | 🟢 none — additive | half day |
| 3 | **Expand drug-page Q&A from ~2 to 5–6** | 🟢 none | 1 day |
| 4 | **`Dataset` schema on research pages + `/developers`** | 🟢 none | half day |
| 5 | **`FAQPage` on the remaining 6 hubs** | 🟢 none | half day |
| 6 | **Weekly grounding-query review** → close gaps | 🟢 none | 30 min/wk |
| 7 | **`/compare/` pilot — 5 pages** | 🟢 none — new URLs | 2 days |
| 8 | ⚠️ **Migrate `bing_rank_report.py` off legacy API** | — | **19 days left** |

Items 1–6 are all zero-risk to the ranking because none of them alters `/calendar`'s URL, title, H1 or opening content.

---

# MEASUREMENT

| Metric | Now | 30-day target |
|---|---:|---|
| AI citations (Bing) | **115 / 3 days** | 500+/week |
| Grounding queries citing us | **1** | 25+ |
| Avg citation share | 16.67% (n=1) | >20% across 25 queries |
| Bing impressions/day | 388 | 1,000+ |
| Bing #1 on head query | ✅ | **hold it** |
| Google indexed | 55 | 150+ (post-validation) |

The leading indicator is **grounding queries**: it should climb from 1 as FAQ markup rolls out. If it doesn't move within two weeks of shipping item 1, the hypothesis is wrong and we re-test.

---

# BOTTOM LINE

Our own site ran the experiment for us: a **363-word drug page with `FAQPage` schema holds 16.67% citation share**, while our **#1-ranked, 1,612-word calendar page earns zero citations** because it has no `FAQPage`. Assyro — cited on the very query where we outrank them — carries 22 schema types and six utterly ordinary FAQ questions. They aren't answering better; they're **declaring the question**, and we aren't.

So the answer to "how do we get more AI citations" is unusually concrete: **put `FAQPage` markup on the nine hubs that lack it, and expand from two questions per drug page to five or six.** That is a template change, it multiplies our answerable-query surface roughly threefold, and it carries zero risk to the Bing #1 because schema never touches the ranked content.

And the answer to "how do we not lose the #1" is equally concrete: **don't touch `/calendar`'s URL, title, H1 or opening paragraph for a month** — add everything below it or in JSON-LD. The one exception worth making is the freshness fix, because "4 days ago" next to our top result, beside a rival's "16 hours ago," is the most plausible way we lose the spot.

---
*Facts and historical statistics only. Not investment advice.*
