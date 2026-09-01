# Two expansions: drug-vs-incumbent comparisons, and the patent-cliff tracker
**2026-08-12 · Cowork session · Amendment 033 filing**
*Includes a working Orange Book prototype built and run today.*
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — DRUG VS INCUMBENT: I agree, and I think I under-sold it

To be direct: **I said yes on 08-08 and I still say yes — this is the strongest content expansion available to us.** Re-reading my note, I led with risk and buried the endorsement, which made a "yes, here's how" read like a "maybe, be careful." That was my error in emphasis, not in judgment.

Your instinct is right and the "factually of course" qualifier *is* the whole design. Let me be concrete instead of cautious.

## Why it wins
- It answers the question retail actually has. **Approval ≠ commercial success.** "Will it be approved?" is the current product; "is it any better, and will it sell?" decides whether the stock holds its gains.
- **No competitor answers it.** Assyro, BiopharmaWatch, FDA Tracker all stop at the date.
- It's **evergreen** — a PDUFA date expires, a comparison doesn't.
- Comparison tables are **the most citable format that exists**, and we now have proof that citations follow structured Q&A on our pages.

## The one hard rule
**Never compare efficacy numbers across separate trials.** Different populations, endpoints, eras, statistical plans. That's not caution, it's arithmetic — and publishing naive cross-trial tables would make us the thing we currently stand against. You already built `/learn/why-cross-trial-comparisons-mislead`; that page is the licence to do the rest properly.

## What each comparison page publishes — all sourced, no verdict
1. **Head-to-head, only where an active comparator actually existed.** If the pivotal trial randomised against a real drug, the comparison is a fact. Report comparator, endpoint, result, p-value.
2. **Trial design as the comparator.** Single-arm vs randomised. Objective, and *the* thing FDA itself weighted for REPL and CAPR. Nobody surfaces it.
3. **Label vs label.** Once approved the label is primary source. Gwyn Lo's BMI < 30 restriction vs the incumbent's — factual, commercially meaningful, zero interpretation.
4. **What it would displace.** Name the standard of care, don't rank it.
5. **Structural differentiators** — route, dosing frequency, cold chain, REMS, oral vs infused. These predict uptake better than efficacy deltas, and they're label facts.
6. **The "why these aren't comparable" module**, linking the explainer.

Start with **5 decided drugs that have a named incumbent**. Prove the format, then scale.

---

# PART 2 — PATENT CLIFFS: this is the better idea, and it's buildable today

I like this more than the comparison work, for three reasons: it's **pure public record** (no interpretation at all), it's **evergreen and forward-looking**, and the **M&A framing is genuinely differentiated** — nobody aggregates it for a retail audience.

## ⚠️ First, the thing that would sink it

**PatentsView alone cannot do this.** PatentsView tells you about patents; it does **not** tell you which patent covers which drug. If we infer drug↔patent linkage from assignee names or titles we will publish wrong cliffs, and a wrong patent-expiry claim is materially worse than a wrong date.

**The authoritative linkage is the FDA Orange Book** (small molecules) and the **Purple Book** (biologics). Those are the spine. PatentsView becomes an *enrichment* layer — claims, family, continuations, litigation context — not the source of truth.

## I built it today to check — it works

Downloaded the live FDA Orange Book data file and ran the aggregation:

```
patent.txt       22,131 rows   Appl_No · Patent_No · Patent_Expire_Date_Text ·
                               Drug_Substance_Flag · Patent_Use_Code · Delist_Flag
exclusivity.txt   2,341 rows   Appl_No · Exclusivity_Code · Exclusivity_Date
products.txt     48,502 rows   Ingredient · Trade_Name · Applicant_Full_Name · Approval_Date
```
Join on `Appl_Type + Appl_No + Product_No`. Free, no key, refreshed monthly by FDA.

**Output, computed live today:**

| | |
|---|---:|
| Brand NDAs with unexpired listed patents | **1,319** |
| Losing exclusivity 2026–2031 | **427** |
| Cliffs in the next 17 months | **83** |

**Cliffs by year:** 2026: 19 · 2027: 64 · 2028: 80 · 2029: 87 · 2030: 75 · **2031: 102**

**Top companies, drugs losing exclusivity 2026–2031:**
AbbVie 14 · Takeda 11 · Novartis 11 · Bayer 10 · Merck 10 · Azurity 8 · ViiV 8 · Boehringer 7 · Salix 6 · AstraZeneca 6

**Nearest named cliffs:**
| LOE | Brand | Ingredient | Company | # patents |
|---|---|---|---|---:|
| 2026-09-28 | SPRYCEL | dasatinib | Bristol Myers Squibb | 12 |
| 2026-09-22 | SENSIPAR | cinacalcet | Amgen | 6 |
| 2026-10-06 | SAPHRIS | asenapine | AbbVie | 21 |
| 2026-10-12 | ANDROGEL | testosterone | Besins | 24 |
| 2026-12-07 | PROTONIX | pantoprazole | Wyeth | 2 |
| 2026-12-12 | CORLANOR | ivabradine | Amgen | 4 |

That's your exact spec — which companies, which drugs, when — from a free, authoritative, citable source, running in about a minute.

## The methodology that keeps it honest
**Loss of exclusivity ≠ last patent expiry.** Publishing "patent expires 2027 → generic in 2027" would be the patent-world equivalent of a cross-trial comparison. Real LOE is the **later of**:
- the last unexpired **Orange Book listed patent** (excluding delisted), and
- the last **regulatory exclusivity** (NCE 5yr, orphan 7yr, pediatric +6mo, biologics 12yr)

My prototype already does `max(last patent, last exclusivity)`. What it deliberately does *not* model — and what we must disclose rather than guess:
- **Patent term extensions** (Hatch-Waxman restoration)
- **Paragraph IV litigation and settlements** — frequently the real generic-entry date, and not in the file
- **Authorised generics**, at-risk launches
- Biologics, which live in the **Purple Book**, not here

So the honest label is **"earliest date no listed patent or exclusivity blocks generic entry"** — not "the day it goes generic." Same discipline as verified/unverified: state precisely what the number is and what it isn't.

## One real data gap
**Orange Book has no therapeutic-area field.** Columns are Ingredient, DF;Route, Trade_Name, Applicant, Strength, Appl_No, TE_Code, Approval_Date, RLD, RS, Type. So "what family — cancer, diabetes" needs a mapping layer.

Three options, cheapest first:
1. **Reuse our own TA tags** — we already assign therapeutic areas across the catalyst dataset; join on ingredient.
2. **ATC classification** via RxNorm/RxClass (free NIH API) — the standard, and gives a clean hierarchy.
3. Manual for the top 200 by relevance.

I'd do (1) for coverage we already have and (2) to fill gaps.

## What to build
```
/patent-cliff                         hub — by year, by company, by therapeutic area
/patent-cliff/2027                    "83 drugs lose exclusivity in 2027"
/patent-cliff/company/abbvie          AbbVie's 14 cliffs
/patent-cliff/oncology                TA view
/drug/{name}  → add an "Exclusivity"  block to the 310 pages we already have
```

**The `/drug/` integration is the highest-value piece** — it deepens 310 existing pages (which we already know need to go from ~350 to 400–600 words) with genuinely new factual content, and it creates internal links into the new hub.

## Why this fits the brand better than almost anything else
It is **entirely public record**. No probabilities, no interpretation, no "how good is it." The only judgement is methodological, and we publish the methodology. It also extends the franchise from "what happens next month" to "what happens over five years" — the same shift that makes the M&A angle work.

## The M&A framing — factual, not speculative
State the facts and let readers draw conclusions:
> *"AbbVie has 14 products losing exclusivity between 2026 and 2031."*

That's a fact. Pair it with our decision archive ("here's what they have in the pipeline") and the reader does the rest. **Don't** publish "AbbVie needs to acquire" — that's a prediction and it breaks the rule that makes us citable.

---

# PART 3 — SEQUENCING

Both are good. If you're choosing, **do patent cliffs first:**

| | Patent cliffs | Drug comparisons |
|---|---|---|
| Source | Single free authoritative file | Multiple, per-drug |
| Interpretation needed | **None** — public record | Careful framing per page |
| Scales | Automatically, all 1,319 NDAs | Manual, ~5 to start |
| Refresh | Monthly FDA file | Per approval |
| Brand risk | **Very low** | Low if disciplined |
| Prototype | ✅ **already running** | Not started |

Patent cliffs are more automatable, lower risk, and I've already proven the pipeline. Comparisons need per-page judgement, so they scale with effort.

**Suggested order:** patent-cliff hub + `/drug/` exclusivity blocks → TA mapping → 5 `/compare/` pilots → scale whichever draws more citations.

**One caveat on timing:** the open-items file has FAQ/schema work as the top non-deadline priority, and that lifts *everything* including these new pages. Ship the FAQ markup first — it's a day — then build these on top so they launch citable rather than needing a retrofit.

---

# BOTTOM LINE

On comparisons: **yes, and I under-sold it last time.** The discipline isn't a reason to hesitate, it's the design — compare what's genuinely comparable (trial design, labels, route, what it displaces) and publish why the efficacy numbers aren't.

On patent cliffs: **this is the better of the two, and I'd start here.** But not via PatentsView as the spine — the Orange Book is the authoritative drug↔patent link, it's free, and I ran it today: **427 drugs losing exclusivity 2026–2031, 83 inside 17 months, AbbVie leading with 14.** Keep the PatentsView key for enrichment. The one thing that would break it is publishing "patent expiry = generic entry"; the honest framing is "earliest date no listed patent or exclusivity blocks entry," with settlements and PTE disclosed as unmodelled.

The therapeutic-area cut you want isn't in the Orange Book — it needs our own TA tags or ATC via RxNorm. That's the only real build gap.

---
*Facts and historical statistics only. Not investment advice. Verify against primary FDA filings.*

**Sources**
- [FDA Orange Book — Approved Drug Products with Therapeutic Equivalence Evaluations](https://www.fda.gov/drugs/drug-approvals-and-databases/approved-drug-products-therapeutic-equivalence-evaluations-orange-book) · data file downloaded and parsed live 2026-08-12
- [Orange Book Data File Download Instructions (FDA)](https://www.accessdata.fda.gov/drugsatfda_docs/ob/OrangeBookDataFileDownloadInstructions.pdf)
- [Patent Listing in FDA's Orange Book — Congressional Research Service](https://www.congress.gov/crs-product/IF12644)
