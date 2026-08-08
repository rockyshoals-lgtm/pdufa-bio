# pdufa.bio — Post-remediation audit
**2026-08-07 · Cowork session · Amendment 033 filing**
*Live origin checks + primary-source verification. Search Console unavailable this round (Chrome extension disconnected) — see §5.*
*Facts and historical statistics only — not investment advice.*

---

# 1. ✅ EVERY P0 AND P1 FROM THE 08-03 BRIEF IS SHIPPED

Verified live today:

| # | Item (from MASTER_BUILDER_BRIEF) | Verified state |
|---|---|---|
| 1.1 | False SELLAS CRL | **RETRACTED** — `/fda-decision/SLS-2025-02-20` now **308 → `/sls`**. Gone from `/ticker/SLS`. |
| 1.2 | 308 price-inferred pages presented as fact | **FIXED** — `noindex` present on 25/30 sampled decision pages (all price-only ones). |
| 1.2 | Headline stat blended verified + inferred | **FIXED, better than proposed** — `/decisions` now states: *"449 records · **Verified 142** with a primary source · **Unverified 307** inferred from price"* and **removed the approval rate entirely** (*"Why there is no approval rate here any more"*). Removing it is more honest than splitting it. |
| 5 | REPL PDUFA missing | **ADDED** — `pdufa_repl_2026-08-02`, Decided/Approved, **`decision_date 2026-08-06`**. Correctly models goal date ≠ actual date. |
| 5 | SLS REGAL readout missing | **ADDED** — REGAL Phase 3 (galinpepimut-S) topline + SLS009 Phase 2, both `Guided` 2026-12-31. |
| 5 | VKTX 404 | **CREATED** — `/vktx`, 858 words, `Organization` JSON-LD. |
| 3.1 | `/tickers` A–Z hub 404 | **BUILT** — 208 server-rendered ticker links. |
| 3.2 | `/screener` invisible to Googlebot | **FIXED** — was 0 `<tr>` / 0 ticker links; now **121 `<tr>`, 212 links (120 → `/ticker/`, 72 → `/pdufa/`)**. |
| 4.1 | Bare-ticker titles couldn't bind the entity | **FIXED** — e.g. *"Bristol-Myers Squibb Company (BMY) FDA Catalysts…"*, *"SELLAS Life Sciences Group, Inc. (SLS) FDA Catalysts"*, *"Viking Therapeutics (VKTX): VK2735 Phase 3 Readout Dates"*. |
| 4.2 | Thin ticker pages (179–209 words) | **IMPROVED** — `/ticker/BMY` 550w, `/vktx` 858w, **`/sls` 3,185w** with the full REGAL fact set (80th event, 78 as of 05-11, Q4 2026 guidance, NCT04229979, SLS009). |
| 7 | Future-dated timestamps | **FIXED** — API `as_of 2026-08-07`; sitemap newest `lastmod 2026-08-07`. No future dates. |
| — | Sitemap hygiene | **CLEAN** — 472 of 473 URLs return 200. |

**Accuracy verified against primary sources:**
- **MRNA** — mRNA-1010 approved **Aug 5 2026** as **mFLUSIVA** (adults 50+; full approval 50–64, accelerated 65+). Site: Decided/Approved, `decision_date 2026-08-05` ✓
- **REPL** — RP1 approved **Aug 6 2026** as **TUDRIQEV** (vusolimogene oderparepvec-wtpg, accelerated approval + nivolumab). Site: goal date 08-02, `decision_date 2026-08-06` ✓

**Correction to my own read this session:** I initially flagged `/bmy`, `/azn`, `/capr`, `/mrna` as blank 200-status pages (soft-404s). **That was wrong** — they correctly return **404**. Only `/sls` and `/vktx` were created as root slugs, both deliberate and both in the sitemap. No soft-404 bug exists.

---

# 2. 🔴 NEW — A drug BMY doesn't make is in BMY's entity title

**Live:** `<title>Bristol-Myers Squibb Company (BMY) FDA Catalysts: **Bevacizumab** | pdufa.bio</title>`
Meta description: *"…catalyst hub … we track for **Bevacizumab**, Camzyos (mavacamten) - (SCOUT-HCM), Nivolumab."*

Bevacizumab is Roche/Genentech (Avastin) and Outlook's LYTENAVA. **BMY does not develop or market it.** Camzyos and Opdivo (nivolumab) are correctly BMY.

**Root cause:** `readout_bmy_2026-09-15` has `name: "Bevacizumab"`. This is almost certainly a CT.gov-derived record where the ingest captured a **comparator/combination arm** rather than the sponsor's own asset.

**Scope — 16 readout records carry comparator/standard-of-care names.** The clearly wrong ones:

| Ticker | Date | Stored name | Problem |
|---|---|---|---|
| **KYTX** | 2026-08-15 | **"Standard of Care Treatment"** | Not a drug at all |
| **BMY** | 2026-09-15 | Bevacizumab | Wrong sponsor |
| **KPTI** | 2026-12-15 | Rituximab | KPTI's asset is selinexor |
| **TLSI** | 2027-09-15 | Pembrolizumab | Not TLSI's asset |
| BYSI | 2026-11-15 | Docetaxel + Plinabulin | Plinabulin is theirs; docetaxel is the comparator |

*(BMY/Nivolumab, MRK/Pembrolizumab and OTLK/bevacizumab are legitimately those sponsors' own assets — not defects.)*

**Why it matters now more than before:** this data defect used to sit in a thin, unindexed readout row. The entity-title fix has **promoted it into the `<title>` and meta description** — exactly the fields that bind the entity for search. A good SEO fix is now amplifying a data bug.

**Do:**
1. Fix the CT.gov ingest to prefer the **sponsor's own intervention** (match against the company's pipeline / drop arms flagged as comparator, active_comparator, placebo_comparator). Reject non-drug strings like "Standard of Care Treatment" outright — you already have a `test_no_junk_drug_names.py` guard; extend it to readouts.
2. **Change the title template's drug selection**: prefer the drug attached to the **nearest upcoming PDUFA** (for BMY that's iberdomide/dara/dex — EXCALIBER RRMM, Aug 17), not the alphabetically-first name across all records. Alphabetical ordering is why the wrong drug leads the title.

---

# 3. 🟠 Brand names are missing from just-approved drugs

Both new approvals landed with development codes only:

| Record | Stored name | Should include |
|---|---|---|
| `pdufa_mrna_2026-08-05` | "mRNA-1010 - (P304)" | **mFLUSIVA** |
| `pdufa_repl_2026-08-02` | "RP1 (vusolimogene oderparepvec) + nivolumab" | **TUDRIQEV** · suffix **-wtpg** |

Retail and press search the **brand name** the moment it exists ("mFLUSIVA approval", "TUDRIQEV melanoma"). Publishing the same day but without the brand name forfeits most of the search demand from that decision — which is precisely the hot-name capture play in §6 of the 08-03 brief.

**Do:** on outcome capture, extract and store the brand name; render it first (`mFLUSIVA (mRNA-1010)`), and include it in the decision page `<title>`, `<h1>`, and meta description.

---

# 4. 🟠 Two source-provenance gaps on brand-new "verified" decisions

| Record | `url` field | Problem |
|---|---|---|
| `pdufa_mrna_2026-08-05` | `https://www.pdufa.bio/pdufa/MRNA` | **Self-referential** — no external primary source. It counts as "verified" without one. |
| `pdufa_repl_2026-08-02` | SEC 8-K `tm2621708d1` | That exhibit is the **Jul 30 AdComm** announcement, not the Aug 6 approval. |

Given you now publish "Verified 142 / Unverified 307" as a public integrity claim, the definition of *verified* has to hold. A self-link cannot satisfy it.

**Do:** add a guard that rejects a `pdufa.bio` URL (or any same-domain URL) in the `url` field of a record marked verified; point MRNA at the FDA/Moderna release and REPL at the FDA approval page or the Aug 6 8-K.

---

# 5. 🟡 Smaller items

- **`/sls` has no JSON-LD at all.** Your flagship page — 3,185 words, all the right facts — emits **zero** structured data (`/vktx` at least has `Organization`). Given Google's People-Also-Ask literally asks *"When is the SLS Phase 3 readout?"*, this is the single best `FAQPage` opportunity on the site. Add `FAQPage` + `Organization` + `Dataset`.
- **Bidirectional ticker linking is still incomplete.** `/screener` (120) and `/tickers` (208) now link to ticker pages, but **`/calendar` = 0, `/decisions` = 0**, homepage = 2. Adding `→ /ticker/{T}` to calendar rows and decision rows would push ticker pages well inside 3 clicks from every hub.
- **`/surges` is in the sitemap but returns 404** (the one bad URL of 473). Remove it or build it.
- **Sitemap is still flat** (473 URLs, no `<sitemapindex>`). Splitting by type (`-pdufa`, `-decisions`, `-tickers`, `-research`) is what lets you measure whether these fixes worked *per section* in GSC.

---

# 6. ⚠️ Search Console unavailable this round — 3 things still unverified

The Claude-in-Chrome extension disconnected mid-audit, so I could not check:
1. **Whether Google has re-read the sitemap** (last known read: **Jul 27**). This was P0 §2.1 in the 08-03 brief and is the single highest-leverage open question — everything above is invisible to Google until it re-reads.
2. **Current indexed / not-indexed counts** (last known: 36 indexed · 522 not · 478 "Discovered – currently not indexed").
3. **No new indexing requests were submitted this round.**

**Queue when Chrome is back** — all now safe to submit, since the SLS false CRL is retracted:
`/sls` · `/vktx` · `/tickers` · `/screener` · `/ticker/BMY` *(after §2 title fix)* · `/fda-decision/MRNA-2026-08-05` · `/fda-decision/REPL-2026-08-02` · **resubmit `sitemap.xml`**

---

# 7. BUILD ORDER

| # | Action | § | Effort |
|---|---|---|---|
| 1 | Fix `readout_bmy_2026-09-15` + the 4 other mis-attributed readouts; extend the junk-drug-name guard to readouts | 2 | 1 hr |
| 2 | Title template: pick the nearest-PDUFA drug, not alphabetically-first | 2 | 30 min |
| 3 | Add brand names (mFLUSIVA, TUDRIQEV) to the two new approvals + to outcome capture going forward | 3 | 1 hr |
| 4 | Guard against same-domain URLs on "verified" records; fix MRNA + REPL sources | 4 | 1 hr |
| 5 | `FAQPage` + `Organization` JSON-LD on `/sls`, then roll to all ticker pages | 5 | half day |
| 6 | Ticker links from `/calendar` + `/decisions` rows | 5 | 2 hr |
| 7 | Remove/build `/surges`; split sitemap into an index | 5 | 2 hr |
| 8 | Confirm sitemap ping is firing on deploy; re-check GSC counts | 6 | — |

**Bottom line:** this was the strongest remediation cycle so far — both credibility P0s are closed, the crawl-structure work (tickers hub, server-rendered screener, entity titles) is genuinely done, and the two approvals that landed this week were captured same-week with correct dates, including the subtle goal-date-vs-actual-date distinction on REPL. The new findings are second-order: a data-quality defect that the SEO fix has promoted into a title, missing brand names on fresh approvals, and two provenance gaps that matter now that "Verified 142 / Unverified 307" is a public claim.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*

## Sources
- Moderna mFLUSIVA (mRNA-1010) FDA approval, Aug 5 2026 — [BioSpace](https://www.biospace.com/press-releases/moderna-receives-u-s-fda-approval-for-influenza-vaccine-mflusiva) · [Healthcare Dive](https://www.healthcaredive.com/news/moderna-fda-approve-mflusiva-seasonal-influenza/827180/) · [AJMC](https://www.ajmc.com/view/fda-approves-moderna-s-mrna-flu-vaccine-after-phase-3-success)
- Replimune TUDRIQEV (vusolimogene oderparepvec-wtpg) accelerated approval, Aug 6 2026 — [FDA](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-grants-accelerated-approval-vusolimogene-oderparepvec-wtpg-combination-nivolumab-melanoma) · [BioSpace](https://www.biospace.com/fda/third-times-the-charm-for-replimune-as-melanoma-drug-earns-fda-greenlight) · [StockTitan](https://www.stocktitan.net/news/REPL/replimune-announces-fda-accelerated-approval-of-tudriqevtm-in-bb647t7h04wb.html)
- SELLAS REGAL status (78 events as of 2026-05-11; Q4 2026 topline guidance) — [SELLAS Q1 2026](https://www.globenewswire.com/news-release/2026/05/12/3293399/0/en/sellas-life-sciences-reports-first-quarter-2026-financial-results-and-provides-corporate-update.html)
