# Full data sweep: every drug, company and date
**2026-09-09. Live API `as_of` 2026-09-09, 456 rows, build `c78438989`. Exhaustive checks on all 456 rows; primary-source verification on the near-term dated set.**
*Facts and build mechanics only. Not investment advice.*

> **Method, stated so the coverage claim is honest.** Two layers. Layer 1 is **exhaustive**: nine structural checks run against all 456 rows, no sampling. Layer 2 is **primary-source verification**, and it is not exhaustive: I verified the nearest dated PDUFAs against FDA, SEC and sponsor releases. Verifying all 456 against primary sources is a multi-day job and I will not imply I did it. Where I could not confirm something, it says so.

---

# 1. WHAT PASSED, EXHAUSTIVELY

All 456 rows, every row checked:

| Check | Result |
|---|---|
| Junk drug names (exhibit labels, "unspecified", empty, numeric) | **0** |
| Malformed `nct_id` (not `NCT` + 8 digits) | **0** |
| Duplicate `ticker + date + type` | **0** |
| `Decided` rows missing an outcome or a decision date | **0** |
| `outcome` set on a row that is neither Decided nor Reported | **0** |
| Decision date more than 120 days from the goal date | **0** |
| Day-precision decided PDUFAs | 32: **20 early, 9 on, 3 late** |

**That last line is the important one.** The published statistic on `/learn` and `/calendar`, "20 of 32 sourced decisions came early," reconciles exactly to the live API. 20 + 9 + 3 = 32. The number we put in front of readers is the number in the data.

---

# 2. WHAT FAILED

## 2.1 P0: 265 of 456 rows have no company name

**58% of the public dataset has a blank `company` field.**

| Type | Status | Count |
|---|---|---|
| Readout | Estimated | 261 |
| AdComm | Held | 2 |
| Readout | Reported | 1 |
| **PDUFA** | **Upcoming** | **1** |

The last row is the one that matters most: **CORT, relacorilant (GRACE resubmission), PDUFA 2026-12-17, day precision, Upcoming, no company name.** A live forward catalyst with a blank sponsor. Corcept Therapeutics appears correctly on other CORT rows, so the value exists and simply is not on this one.

The two AdComm rows are CAPR (Deramiocel, DMD, 2026-07-29) and REPL (RP1, melanoma, 2026-07-30), both status Held.

## 2.2 P0: 261 of 266 Estimated readouts are dated to the 15th of the month

Day-of-month distribution across all Estimated readouts:

```
day 15 → 261      day 30 → 2      day 31 → 3
```

No real distribution of clinical readout dates looks like that. **The 15th is a placeholder**, and the API serves it in the `date` field. The `date_precision` field honestly says `month`, so a careful consumer is warned. A careless one, or an AI summarising our API, reads `2026-06-15` and repeats a day the sponsor never gave.

These are the same rows as the null-company block: 261 estimated readouts with no company and a manufactured day. **That is 57% of what our public API serves.** For a site whose entire position is "facts only, every date sourced," this is the largest single integrity exposure we have, and it is in the endpoint we advertise on `/developers`.

Two honest options, and I do not think there is a third:
1. **Publish `date: null` when precision is `month`**, and put the month in `date_month` where it already belongs. A consumer then cannot mistake a placeholder for a date.
2. **Withhold the estimated readouts from the public API entirely** until they carry a sponsor-stated date, the way `conferences.json` withholds JPM 2027 rather than repeating an unverified third-party date.

The `_unannounced` discipline already exists in the conference data. This is the same problem and deserves the same answer.

## 2.3 P1: 44 of 52 forward dated PDUFAs cite pdufa.bio as their own source

| Set | Self-referential `url` |
|---|---|
| Forward day-precision PDUFAs | **44 of 52 (85%)** |
| All PDUFA rows | **75 of 85 (88%)** |

The site says "every date links its source." For most forward rows the API's `url` field is our own page. The page may still carry a source; the field does not.

I raised this on 2026-09-05 as "API `url` semantics are mixed" and the builder's position was that `url` is the page, not the source. That is a defensible schema choice, and it is also why the API cannot be quoted as sourced. **The fix is the `source_url` / `page_url` split already queued, and it should move up:** it is the difference between an API that documents its provenance and one that asks you to trust it.

## 2.4 P1: 15 tickers carry inconsistent company names

```
GSK    :: "GSK plc American Depositary Shares (Each representing two)" || "GSK plc"
AZN    :: "AstraZeneca PLC" || "AstraZeneca/Alexion"
RHHBY  :: "Roche Holding AG" || "Roche/Genentech"
MRK    :: "Merck & Co." || "Merck & Co., Inc." || "Merck"
GILD   :: "Gilead Sciences Inc." || "Gilead Sciences, Inc." || "Gilead Sciences"
MNKD   :: "MannKind Corporation" || "MANNKIND CORP"
...plus ARQT, LNTH, IONS, VTRS, REGN, NUVL, NVO, BBIO, PRAX
```

Most are cosmetic. **One is not: GSK carries an exchange listing description in the company field.** "American Depositary Shares (Each representing two)" is not a company name. That is the same ADR boilerplate the builder excluded from hub titles last night, still sitting in the data underneath.

## 2.5 P2: 9 forward PDUFAs have no indication

INCY 09-26, MIRM 09-26, VTRS 10-17, SMMT 11-14, VNDA 12-12, CORT 12-17, PRAX 2027-01-29, AXSM 2027-05-01, BBIO 2027-05-08.

The INCY and MIRM rows are the zilurgisertib pair, which the builder merged for display last week. The indication is fibrodysplasia ossificans progressiva and it is absent from both.

---

# 3. PRIMARY-SOURCE VERIFICATION OF THE NEAR-TERM SET

## TLX, September 11, two days out. Date right, description wrong.

**Verified correct:** TLX101-Px, Telix Pharmaceuticals, PDUFA **September 11, 2026**, recurrent or progressive glioma. Confirmed against Telix's April 10, 2026 release and its SEC Form 6-K.

**Three defects on the site's own next catalyst:**

1. **We call a diagnostic a treatment.** `/pdufa/TLX` reads: *"TLX101-Px is under FDA review **to treat** recurrent or progressive glioma."* TLX101-Px is **Pixclara**, a **PET imaging agent** (floretyrosine F 18), submitted for the *characterisation* of recurrent or progressive glioma versus treatment-related change. It does not treat anything. The confusion is understandable, because TLX101 without the suffix is a therapeutic candidate, but the page as written is factually wrong about what the drug is.
2. **The brand name Pixclara appears nowhere on the page.** Every press headline reads "TLX101-Px (Pixclara®)". It is the name a reader searches and an AI quotes.
3. **The page is stamped "Updated August 15, 2026"**, 25 days stale, on the decision that is two days away. `article:modified_time` agrees. The calendar rebuilds daily; this per-event page did not.

## RARE, September 19. Correct.

UX111, Ultragenyx, Sanfilippo syndrome type A (MPS IIIA), PDUFA **September 19, 2026**, BLA resubmission accepted after the July 2025 CRL on CMC and facility inspection. All correct. Missing: the INN **rebisufligene etisparvovec**, which is now in public use.

## MRK, September 21. Unverified from this evidence, and it needs a source.

Our row: **MRK, 2026-09-21, "WINREVAIR (sotatercept-csrk) - (HYPERION)", recently diagnosed pulmonary arterial hypertension.**

What I can confirm: the sBLA that received priority review was based on **ZENITH**, with a PDUFA of **October 25, 2025**. And **HYPERION was discontinued early** because of the positive ZENITH interim analysis. Merck has said HYPERION results would be submitted to regulators, so a HYPERION-based filing may well exist, but **I could not find an announcement of a September 21, 2026 goal date in two searches.**

I am not saying the date is wrong. I am saying **it is twelve days away, it is on the public calendar, its `url` points at our own page, and I cannot get from our data to a document that supports it.** That is the exact situation the sourcing discipline exists to prevent. It needs a primary source attached or the row needs a confidence downgrade.

---

# 4. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **MRK 2026-09-21 (HYPERION): attach the primary source or downgrade the row.** If no sponsor or FDA document states that goal date, it should not sit on the calendar as a day-precision fact. | the row carries an external `url` to a Merck release or SEC filing stating a September 21, 2026 action date, or the row is re-dated / re-precisioned with a note |
| **2** | **TLX: "to treat" → the truth.** It is a PET imaging agent for characterising glioma. Add **Pixclara**. Re-stamp the page. | `/pdufa/TLX` contains "imaging" and "Pixclara", does not contain "to treat", and shows a September stamp |
| **3** | **Estimated readouts: stop serving a manufactured day.** Either `date: null` with `date_month` carrying the month, or withhold them from the public API until a sponsor states a date. | no API row has `date_precision: month` with a day that is not sponsor-stated; `/developers` documents the choice |
| **4** | **Company name on all 265 blank rows**, CORT's Upcoming PDUFA first, then the two AdComms | 0 rows with a null company; guard added |
| **5** | **`source_url` / `page_url` split** on the API, with a version note | forward PDUFA rows carry a resolvable external `source_url`; `/developers` documents both fields |
| 6 | Normalise the 15 company-name variants; strip ADR boilerplate from GSK | one canonical name per ticker; guard asserts it |
| 7 | Indication on the 9 forward PDUFAs missing one; zilurgisertib is FOP | 0 forward PDUFAs with an empty indication |
| 8 | Per-event pages re-stamp on every build, not only when edited | `/pdufa/TLX` `article:modified_time` within 24h of `build-info.built` |

Items 1 and 2 are today. Item 1 is a forward date twelve days out that I cannot source. Item 2 is a wrong description of what a drug does, on the decision that lands in two days.

---

# BOTTOM LINE

**The structural integrity is good and the headline statistic is honest.** Nine exhaustive checks across all 456 rows return clean: no junk names, no malformed trial IDs, no duplicates, no decided row missing its outcome, no impossible date deltas. The "20 of 32 sourced decisions came early" that we put on `/learn` and `/calendar` reconciles exactly to the live data.

**The failures are all of one kind: we are publishing fields we have not filled.** 265 rows have no company. 261 estimated readouts carry a day the sponsor never gave, always the 15th, in the `date` field of the API we advertise. 44 of 52 forward dated PDUFAs cite pdufa.bio as their own source. Nine have no indication. None of that is a wrong fact; all of it is the appearance of a fact where we do not have one, which for this site is the more dangerous failure.

**Two live errors need fixing today.** Our next catalyst, two days out, tells readers a PET imaging agent is a treatment and never mentions the brand name FDA is reviewing. And a dated PDUFA twelve days out cites our own page as its source and I could not find a document supporting the date in two searches.

**What I did not do:** verify all 456 rows against primary sources. I verified the nearest dated PDUFAs. A full primary-source pass over the archive is a separate, larger piece of work, and if immaculate is the standard, it is worth scheduling deliberately rather than claiming by implication.

---
*Exhaustive checks run against the live API 2026-09-09. Primary sources: Telix release 2026-04-10 and SEC 6-K; Ultragenyx BLA resubmission acceptance; Merck ZENITH sBLA priority-review release. Not investment advice.*
