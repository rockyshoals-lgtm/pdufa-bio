# pdufa.bio — OPEN ITEMS (single reference)
**Last verified live: 2026-08-12 ~13:00 ET · every item below re-checked against the live site today.**
*Supersedes the open-item lists in all prior audits. Closed items are in §6 so nothing gets redone.*
*Facts and historical statistics only — not investment advice.*

---

## HOW TO USE THIS FILE
One file, current status, ordered by impact ÷ effort. Every claim has a verification command so you can confirm the fix yourself.

**Ground rule that governs everything below:** we are **#1 on Bing** for "fda calendar 2026 pdufa dates". That ranking lives on `/calendar`. **Do not change `/calendar`'s URL, canonical, title, H1, or opening paragraph for ~4 weeks.** Everything in this file is either additive, schema-only, or on other pages — deliberately.

**⭐ COMPANION SPEC — read before writing any new copy:** `PLAIN_LANGUAGE_SPEC_AND_REDTEAM_PROTOCOL.md` (same folder). It is the house writing standard: *"Simplify the language. Never simplify the fact."* It contains the 24-term jargon→plain-English translation table **with a "what NOT to say" column** (the tempting simplification that would make us wrong), the number rules, the quotable sentence pattern, and the red-team protocol I will audit every new page against. **Every item in §2, §3 and §4 below that produces reader-facing prose must conform to it** — in particular the new `/compare/` and `/patent-cliff/` surfaces, where a confident-but-wrong sentence is the main risk.

---

# 1. ✅ CLOSED — "Bing API migration" was my error, not a defect

## 1.1 ~~Migrate `bing_rank_report.py` off the legacy Bing API~~ — **WITHDRAWN 2026-08-12**

**The builder was right. I was wrong, and I repeated it for five days across six documents.**

What actually retires on Aug 31, 2026 is the **SOAP** (`api.svc/soap`) and **POX** protocols. The **JSON/HTTP (REST)** protocol at `api.svc/json` is the **migration target** — it survives, with the same API key, quotas and functionality. Microsoft's own guidance to affected users is to search their codebase for `api.svc/soap` or `api.svc/pox`.

`bing_rank_report.py` uses `BASE = "https://ssl.bing.com/webmaster/api.svc/json"`, has **zero** SOAP/POX references and **zero** SOAP/XML machinery. **It has always been on the surviving protocol.**

My verification command was the error:

```bash
grep -c "api.svc/json" bing_rank_report.py    # I expected 0 — WRONG, that string is compliance
```

**Correct exposure test — adopted:**
```bash
grep -c "api.svc/soap\|api.svc/pox" bing_rank_report.py    # exposure = >0 ; currently 0 ✅
```

**Why I got it wrong, because the pattern matters:** my command encoded my hypothesis instead of testing it. I grepped for the endpoint I had assumed was legacy and treated its presence as proof of exposure — so every re-run "confirmed" the finding. It is the same failure as the conference miner's edition-mismatch: a check that looks rigorous while confirming the wrong thing. I also never verified the underlying Microsoft claim until the builder forced it, on the third asking.

**No action. Nothing on this site currently has an external deadline.**

---

# 2. 🟠 HIGHEST LEVERAGE — AI citations (zero risk to the Bing #1)

**Why this is the top non-deadline priority:** our own pages prove the mechanism. `/drug/rusfertide` — **363 words, has `FAQPage`** — holds **16.67% citation share** for "rusfertide pdufa date". `/calendar` — **1,612 words, ranks #1, no `FAQPage`** — earns **zero** AI citations. Assyro, cited on the query where we outrank them, runs 22 schema types and six banal FAQ questions.

**Schema is invisible to readers. None of §2 can affect the ranking.**

## 2.1 Add `FAQPage` to the 10 hubs that lack it
Verified today — **all ten have `FAQPage=False`, `Question=0`**:

`/calendar` · `/decisions` · `/readouts` · `/drug` · `/tickers` · `/research` · `/conferences` · `/adcomm` · `/learn/why-cross-trial-comparisons-mislead` · `/developers`

3–5 questions each. **Answer in one declarative sentence containing a number and a date** — that is the unit an engine lifts.

Starter set for `/calendar`:
| Question | Answer shape |
|---|---|
| How many FDA decisions are scheduled in 2026? | "67 FDA decision dates are scheduled for 2026; 52 are still ahead as of {date}." |
| When is the next FDA decision? | "{TICKER} ({drug}) on {date}." |
| How often is the PDUFA calendar updated? | "Daily, from FDA, SEC and company primary sources." |
| Where does the data come from? | name them |

`/decisions`: *"What share of FDA decisions are approvals?"* → answer with the **verified-only** figure and its n, and state that unverified records are excluded. The refusal is itself quotable.

`/learn/why-cross-trial-comparisons-mislead`: already Q&A-shaped, has `Article` but no `FAQPage`. Most citable asset on the site. Mark it up.

```bash
curl -s https://www.pdufa.bio/calendar | grep -c '"FAQPage"'   # expect ≥1
```

## 2.2 Expand drug-page Q&A from 2 → 5–6
Verified today: `/drug/rusfertide`, `/deramiocel`, `/mk-6240`, `/semaglutide` **all have exactly 2 Questions**.

310 drug pages × 2 = ~620 answerable queries. At 5–6 that's **1,800+ — with zero new pages.** Add:
- "When is the {drug} FDA decision date?"
- "What is {drug} used for?"
- "Who makes {drug}?"
- "Has {drug} been approved?"
- "What happened at {drug}'s last FDA decision?"

## 2.3 Add `Dataset` schema — uncontested surface
Verified: **`Dataset=False` on all 10 hubs.** We publish none, despite CC BY 4.0 research with n and IQR — better dataset material than Assyro, who *does* publish `Dataset` + `DataCatalog`.

Add to each research page and `/developers`. Feeds Google Dataset Search (no competition in this category) and signals "structured, citable source" to AI crawlers.

## 2.4 Weekly grounding-query review
BWT → AI Performance → *Grounding Queries* now shows the exact queries citing us with citation share. Currently **1 row** ("rusfertide pdufa date", 12 citations, 16.67%).

Weekly: low share → tighten the answer sentence; absent-but-winnable → add that exact question to the relevant page. **This is a measured feedback loop no competitor is running.**

---

# 3. 🟠 FRESHNESS — the one change worth making on `/calendar`

**The problem:** Bing prints **"4 days ago"** next to our #1 result while novapharmanews shows **"16 hours ago"**. On a freshness-driven query this is the most plausible way we lose the top spot.

Verified today:
| Page | `dateModified` |
|---|---|
| `/` | 2026-08-12 ✅ |
| `/readouts`, `/drug`, `/tickers` | 2026-08-11 |
| **`/calendar`** | **2026-08-08** ← the #1 page |
| **`/decisions`** | **2026-08-08** |

The stamp is *honest* — the build only bumps on real content change, which is correct and should stay. **Don't fake it.**

**Fix it truthfully instead:** `/pdufa/LNTH` already renders a live "**in 1 day**" countdown (verified). `/calendar` and `/decisions` have **no countdown tokens at all**. Add the same countdown / "next decision in N days" line, and the page genuinely changes daily — so the stamp updates honestly and the snippet stops undercutting us.

✅ Additive, appended content — no risk to the ranking.

```bash
curl -s https://www.pdufa.bio/calendar | grep -oE "in [0-9]+ days?"   # expect a match
```

---

# 4. 🟡 STRUCTURAL / CONTENT

## 4.1 Per-event PDUFA URLs
Verified 404 today: `/pdufa/LNTH-2026-08-13`, `/pdufa/CAPR-2026-08-22`.

All events for a ticker still share one `url` in the API (e.g. all three LNTH records → `/pdufa/LNTH`). The **acute** problem is fixed — `/pdufa/LNTH` is now a proper hub leading with "Upcoming Aug 13 · in 1 day · MK-6240" — so this is no longer urgent. But **AI engines cite specific URLs**, and one URL representing three events limits what can be cited and linked.

Give each PDUFA its own page (`/pdufa/{TICKER}-{date}`), keep `/pdufa/{TICKER}` as the hub, and point each API record's `url` at its own event.

## 4.2 Drug pages are thin
Verified: 337–380 words each. They rank (#5 on Bing for "monalizumab fda decision date", ~1 day old) and they get cited — so this is a ceiling issue, not a defect. Target 400–600 words: mechanism, sponsor, indication, every catalyst with dates and outcomes, linked decision pages, cohort context.

*Note: do §2.2 (more Q&A) before §4.2 (more prose). Q&A drives citations; prose drives ranking.*

## 4.3 `/compare/` pages
Verified 404. The methodology page shipped first, which was the right order. Comparison tables are the most citable format that exists.

Per the 08-08 strategy: publish comparative **context**, never a verdict — head-to-head only where an active comparator actually existed, trial design as the comparator, label-vs-label, what it displaces, structural differentiators (route/dosing/REMS), and the "why these aren't comparable" module. **Start with 5 decided drugs that have a named incumbent.**

## 4.4 Bing URL submission quota underused
Bing allows ~100/day; we used 12% on the day I checked. IndexNow is a **separate, uncapped** channel (verified: submitting via IndexNow did not decrement the manual quota). Keep IndexNow as the automated path — the causal line is clear, 108 submissions → Bing impressions doubled — and spend the manual 100 on anything IndexNow hasn't covered.

---

# 5. ⏳ WAITING — no action

- **Google redirect-error validation** — status *Started* since Aug 9 (19 URLs). Typical 1–2 weeks. All 19 resolve 200; the fix is correct. Just waiting on Google's queue.
- **Google indexing** — 55 indexed / 418 "Discovered – currently not indexed", flat since Aug 10. Should move once validation completes. **Don't chase Google head terms in the meantime** — compound on Bing.
- **BWT "URLs not indexed due to NOINDEX"** — ✅ **already investigated, no action.** Verified `/`, `/calendar`, `/decisions`, `/drug`, `/tickers`, `/screener`, `/research`, `/learn`, `/drug/rusfertide` and sourced decision pages are all `noindex=0`. The warning refers to the intentionally noindexed price-only decision tier. Working as designed.

---

# 6. ✅ CLOSED — do not redo

| Item | Closed |
|---|---|
| False SELLAS CRL published | Retracted; `/fda-decision/SLS-2025-02-20` → 308 |
| 308 price-inferred pages shown as verified | `noindex` + `/decisions` now publishes "449 records · 142 verified · 307 unverified" and **removed the approval-rate stat entirely** |
| Google never re-reading sitemap (stuck Jul 27) | Sitemap ping automated; last read now current |
| robots.txt blocking the API `/llms.txt` advertises | `Allow: /api/v1/` |
| API mirror lagging the pages | VTRS/OTLK/CAPR all correct |
| `/decisions` sort + year counter | Date-descending, counter correct |
| Event schema "94% not eligible" | `startDate` time+TZ; GSC Events 14 valid / 2 invalid |
| 11 legacy URLs redirecting into 404s | All 13 resolve 200 with topical mappings |
| `/tickers` A–Z hub missing | Built, 208 links |
| `/screener` invisible to Googlebot | Server-rendered: 121 `<tr>`, 212 links |
| Bare-ticker titles couldn't bind entity | "SELLAS Life Sciences Group, Inc. (SLS)…" etc. |
| `dateModified` missing / mixed format | Full ISO-8601 + offset sitewide |
| `/drug/` pages didn't exist | 310 live, 2-click crawl path via nav |
| `/drug/miplyffa`, `/drug/galinpepimut-s`, `/drug/dtx401` 404 | All live |
| Conference names published as drugs | `aasld-the`, `acr-convergence` removed |
| `/pdufa/LNTH` → wrong drug's CRL | Now a hub leading with the upcoming catalyst |
| REPL PDUFA missing; AdComm→PDUFA linkage | Added, `decision_date 2026-08-06` correct |
| VKTX had no page | `/vktx` live |
| `/calendar` title not click-worthy | "2026 FDA PDUFA Calendar: 67 Dates, Updated Daily" |
| Cross-trial explainer missing | `/learn/why-cross-trial-comparisons-mislead`, 848w, `Article` schema |

---

# 7. SUGGESTED ORDER

| # | Item | § | Risk to Bing #1 | Effort |
|---|---|---|:---:|---|
| ~~1~~ | ~~Migrate Bing API off legacy~~ **WITHDRAWN — my error, see §1.1** | 1.1 | — | **no action** |
| 2 | `FAQPage` on `/calendar`, `/decisions`, `/learn/*` | 2.1 | 🟢 none | 1 day |
| 3 | Countdown on `/calendar` + `/decisions` | 3 | 🟢 none | half day |
| 4 | Drug-page Q&A 2 → 5–6 | 2.2 | 🟢 none | 1 day |
| 5 | `Dataset` schema | 2.3 | 🟢 none | half day |
| 6 | `FAQPage` on remaining 7 hubs | 2.1 | 🟢 none | half day |
| 7 | Weekly grounding-query review | 2.4 | 🟢 none | 30 min/wk |
| 8 | `/compare/` pilot (5 pages) | 4.3 | 🟢 none | 2 days |
| 9 | Thicken drug pages to 400–600w | 4.2 | 🟢 none | 1–2 days |
| 10 | Per-event PDUFA URLs | 4.1 | 🟢 none | 1 day |

---

# 8. WHERE WE STAND (for context)

| Metric | Current |
|---|---|
| **Bing rank, head query** | **#1** (from #3 on Aug 7) |
| Bing clicks / impressions | 18 / 776 over 3 days (Aug 8–10) — impressions doubled, clicks 5× |
| **AI citations** | **115 in 3 days** (8 → 35 → 72) — 9× in 48h |
| Grounding queries citing us | 1 — "rusfertide pdufa date", 16.67% share |
| Google | 38 clicks / 1,610 impressions over 90 days · 55 indexed · 418 never crawled |

Bing is running at roughly **40× Google's daily click rate.** Treat it as the primary channel.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
