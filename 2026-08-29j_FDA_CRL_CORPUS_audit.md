# FDA CRL corpus — audit and build plan
**2026-08-29 · site checked live · both local CRL corpora compared against the FDA source**
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — 🔴 THE HEADLINE: we built the worse dataset, and the better one was already here

Two CRL corpora now sit in the repo. They are not equivalent.

| | **openFDA API pull** *(`CRL_corpus_openFDA_2026-06-22.json`, already in repo since June)* | **New PDF scrape** *(`_crl_letter_index.json`, 70 MB zip)* |
|---|---:|---:|
| Records | **439** | 364 |
| Year span | **2002 – 2026** | mostly 2024–2026 |
| Letter date missing | **0%** | **38%** |
| Company name missing | **0%** | **40%** — *plus 43% containing header junk* |
| Application number | **100%, typed** (`NDA 215344`) | 100%, **untyped** (55% unknown NDA/BLA) |
| Approval status | **100%** (`Approved` / `Unapproved`) | a `set` field only |
| Full letter text | **yes** | first ~60 chars only |
| Apps with >1 CRL | **79** | 26 |

**The FDA publishes this through an API** — [openFDA Complete Response Letters](https://open.fda.gov/apis/transparency/completeresponseletters) — and we pulled it cleanly in June. The new 70 MB PDF scrape re-derives the same data by regex and loses most of it.

Examples of what the PDF parse produces for `company`:
```
"COMPLETE RESPONSE DBV Technologies S.A. August 3, 2020"
"OMPLETE RESPONSE January 15, 2025 Atara Biotherapeutics, Inc."
"TE RESPONSE January 9, 2026 Pierre Fabre Pharmaceuticals Inc."
```
Truncated header words, embedded dates, no clean company field.

**Recommendation: retire `_crl_letter_index.json` as a data source. Refresh the openFDA pull instead** — it is two months stale and the FDA adds batches continuously. Keep the PDFs only as a local cache if you want offline text; **link FDA's own hosted URLs rather than rehosting 70 MB.**

---

# PART 2 — WHAT THE SITE DOES WITH CRLs TODAY

`/decisions/crl` **exists and is decent**: 776 words, 44 decision links, lede reads *"This page lists 47 Complete Response Letters covering January 2025 to June 2026."*

But across `/decisions`, `/decisions/crl`, `/decisions/approvals` and the individual decision pages:

```
fda.gov links : 0
.pdf links    : 0
FAQPage Q     : 0   (on both /decisions/crl and /decisions/approvals)
```

**We hold 439 actual FDA Complete Response Letters and link not one of them.** A CRL decision page currently says *"the FDA issued a CRL"* on our authority. It could say it on the FDA's, with the letter attached.

Minor: the lede says **47** CRLs; I count **44** decision links on the page. Worth reconciling.

*Good news elsewhere: `/decisions` is now **460 records, 305 sourced** (was 289), 109 inferred, **46 unsourced** (was 63). Sourcing keeps improving.*

---

# PART 3 — 🥇 THE MOAT: 309 letters where the answer was "yes, they came back"

This is the most valuable thing in the corpus and nobody publishes it.

```
approval_status:  Approved 309  ·  Unapproved 130
applications with more than one CRL: 79
```

**309 of the 439 letters belong to applications that were ultimately approved.** The single biggest question a retail holder asks after a CRL — *"is this dead, or do they come back?"* — has 309 documented answers sitting in a file we already have.

And **79 applications received more than one CRL**, with the full sequence and dates. That's the resubmission story, per drug, from the primary source.

**Build `/crl` as a real hub:**

> **What happens after a Complete Response Letter?**
> The FDA has published **439** Complete Response Letters. **309** of them went to applications that were **later approved**; **130** belong to applications still unapproved. **79 applications received more than one letter.**
>
> A CRL is not a rejection. It is the FDA telling the company what must be fixed before the application can be approved. This page lists every published letter, what it said, and what happened next.

Every number there is a count from a primary source with the letter attached. **No competitor can match it, because it requires joining the FDA corpus to an outcome archive — and we have the only sourced outcome archive.**

---

# PART 4 — WHAT TO BUILD, RANKED

## 1. Link the letter on every CRL decision page
47 CRLs on the site; the corpus covers 2002–2026. Join on company + date (and application number once we carry it).

> **The FDA's letter.** [Complete Response Letter, 9 October 2025 (PDF, FDA)] — the agency's own letter to Replimune for BLA 125827.

That takes a page from *"we say it was a CRL"* to *"here is the FDA's letter."* It is the strongest provenance upgrade available and it fits the sourcing model already published on `/decisions`.

## 2. Carry the application number in our own records
Our decision records have **no application-number field**, so an exact join is impossible today. Adding `application_number` (`NDA 215344` / `BLA 125827`) makes the join deterministic instead of fuzzy — and it's a citable identifier in its own right.

## 3. `FAQPage` on `/decisions/crl` and `/decisions/approvals`
Both are **Q=0** while every other hub carries one. Obvious questions, all answerable from the corpus:
- *"What is a Complete Response Letter?"*
- *"How many CRLs has the FDA published?"* → **439**
- *"Do drugs get approved after a CRL?"* → **309 of 439 letters belong to applications later approved**
- *"Can a drug get more than one CRL?"* → **yes — 79 applications did**

## 4. Per-letter pages
439 letters → 439 indexable URLs at `/crl/{application}-{date}`, each with the FDA link, the company, the date, the approval status, and what happened next. **This is the single largest indexable-content opportunity left on the site**, and every page is primary-source-backed.

*Caution consistent with the Google finding: these help Bing and AI citations immediately; Google will index them slowly while authority is the constraint.*

## 5. Plain-language: what the letters actually say
The corpus carries **full letter text**. The most-asked question after *"did they get a CRL"* is *"why?"* — and the answer is in the letter. Extracting the stated deficiency category (manufacturing / clinical / CMC / facility inspection) would be genuinely new public information.

**Red-team constraint:** categorise only what the letter states explicitly, quote the sentence, and never infer a reason the letter doesn't give. Same discipline as the sourced/inferred split on `/decisions`.

## 6. Fix the lede arithmetic
`/decisions/crl` says 47; the page links 44.

---

# PART 5 — WHAT NOT TO DO

- **Don't rehost 70 MB of PDFs.** Link FDA's URLs. They're authoritative, permanent, and free to serve.
- **Don't publish the PDF-parsed company names.** 43% contain header junk; several are truncated mid-word.
- **Don't compute a "CRL approval rate" over the corpus.** 309/439 is *not* "70% of CRLs end in approval" — the FDA publishes all letters for an application when it approves it, so approved applications are structurally over-represented. **Publish the counts, not a rate.** Same trap as the decision-timing selection bias, and the same fix: state the inclusion rule.
- **Don't call a CRL a rejection.** Guard 41 already enforces this; the new pages must inherit it.

---

# PART 6 — ORDER

| # | Action | Effort |
|---|---|---|
| 1 | Refresh the openFDA pull; retire the PDF index as a data source | hours |
| 2 | Add `application_number` to our decision records | hours |
| 3 | Link the FDA letter on all 47 existing CRL pages | 1 day |
| 4 | `FAQPage` on `/decisions/crl` + `/decisions/approvals` | hours |
| 5 | `/crl` hub — 439 letters, 309/130 split, 79 multi-CRL apps | 1 day |
| 6 | Per-letter pages `/crl/{app}-{date}` | 2 days |
| 7 | Stated-deficiency extraction, quote-only | 2 days |
| 8 | Reconcile the 47-vs-44 lede | minutes |

---

# BOTTOM LINE

**The most important finding is that the better dataset was already in the repo.** The openFDA API pull from June has 439 records with zero missing dates, zero missing company names, typed application numbers and full letter text. The new 70 MB PDF scrape has 364 records, 38% missing dates and 40% missing companies. **Refresh the API pull; don't parse PDFs.**

**We link none of the letters.** 439 primary-source FDA documents, and every CRL page on the site still asserts the outcome on our own authority. That's the cheapest provenance upgrade available.

**And the moat is the "what happened next" join.** 309 of these letters belong to applications the FDA later approved; 79 applications got more than one. *"Is this dead, or do they come back?"* is the question every retail holder asks after a CRL, and we are the only site that can answer it from primary sources — because we're the only one with a sourced outcome archive to join against.

Publish the counts, never a rate.

---
*openFDA corpus and site both verified 2026-08-29. Not investment advice.*

**Source**
- [openFDA — Complete Response Letters API](https://open.fda.gov/apis/transparency/completeresponseletters)
- [FDA — Real-time release of Complete Response Letters](https://www.fda.gov/news-events/press-announcements/fda-announces-real-time-release-complete-response-letters-posts-previously-unpublished-batch-89)
