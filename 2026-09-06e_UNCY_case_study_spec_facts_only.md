# UNCY / oxylanthanum carbonate — a case study in why pdufa.bio publishes facts, not approval odds
**Spec for the builder · 2026-09-06 · every fact below is from an FDA letter we hold, an SEC-filed release, or our own price series — sources named inline**
*Facts and build mechanics only — not investment advice.*

---

# 0. THE ANSWER TO DAVID'S QUESTION

**Yes — this can be published inside the facts-only mandate, and it is the strongest case we have.** The reason it works is that we don't need to argue anything: **FDA's own two letters do the arguing.** We hold both (NDA 218607, dated 06/27/2025 and 06/29/2026) in the openFDA corpus, and the only deficiency section in either is *FACILITY INSPECTIONS*. Everything else — labeling, carton, proprietary name — is boilerplate "we reserve comment until the application is otherwise adequate."

**The rule that keeps it inside the mandate:** the page states what FDA wrote, what the company disclosed, and what the stock did. It then states *our editorial policy* in one sentence. It never says what a model would have predicted, never names a competitor, and never says what happens next.

---

# 1. THE FACTS — in order, each with its source

| Date | Fact | Source |
|---|---|---|
| — | Application: **NDA 218607**, oxylanthanum carbonate (OLC), hyperphosphatemia in CKD patients on dialysis, 505(b)(2) pathway | FDA letters; company release |
| **2025-06-27** | FDA issues first CRL. The letter's only deficiency section is **FACILITY INSPECTIONS**: *"Following a Current Good Manufacturing Practices (CGMP) inspection and pre-approval inspection (PAI) of [facility redacted] listed in this submission, FDA conveyed deficiencies to the representative of the facility… on the FDA Form 483."* No clinical, efficacy or safety deficiency is listed. Labeling: *"We reserve comment… until the application is otherwise adequate."* | **FDA letter, openFDA `CRL_NDA218607_20250627.pdf`** |
| 2025-06-27 → 06-30 | UNCY closed **$6.80** on June 27 and **$4.77** on June 30 — **−29.9%** — on 4.77M shares vs ~1M on the prior days | our price series (`price_cache_pdufa_6yr.json`) |
| Sept 2025 | Company holds a **Type A meeting** with FDA on resolving the vendor deficiencies. Company: *"The FDA did not express any concerns about the third-party manufacturer's progress and no additional issues were raised."* | Unicycive release, 2026-06-30 |
| late 2025 / early 2026 | Company resubmits the NDA *"based on Unicycive's belief of continued progress by the original third-party manufacturing vendor in resolving FDA-cited deficiencies and demonstrating inspection readiness."* Resubmission accepted; goal date **June 29, 2026** (six-month Class 2 clock) | Unicycive release, 2026-06-30; goal date on our calendar |
| 2026-03-25 | FDA correspondence finds the proposed **proprietary name "conditionally acceptable pending approval"** — the review had reached the brand-name stage | FDA letter 2026-06-29, PROPRIETARY NAME section |
| **2026-06-29** | FDA issues second CRL (Reference ID 5825414). Only deficiency section again **FACILITY INSPECTIONS**: *"Following a CGMP inspection of [facility redacted]… FDA conveyed deficiencies to the representative of the facility… The facility's satisfactory responses are dependent on FDA's determination that the facility has come into compliance with CGMP and **may require re-inspection of the facility**… **Satisfactory outcomes of both the PAI and the CGMP surveillance inspections will be needed prior to approval** of the application."* And: *"The deficiencies identified during the inspection **may not be specific to your pending application**."* | **FDA letter, openFDA `CRL_NDA218607_20260629.pdf`** |
| 2026-06-30 07:05 ET | Company announces the CRL. Headline bullets, verbatim: *"Complete Response Letter relates to deficiencies previously identified at third-party manufacturing vendor"* · *"**FDA inspection of third-party facility did not occur during the NDA resubmission review**"* · *"FDA did not raise concerns regarding the clinical efficacy or safety data of OLC, and no additional data was requested"* · labeling discussion with FDA was active as of June 29 | Unicycive release, GlobeNewswire 3319541 |
| 2026-06-29 → 06-30 | UNCY closed **$7.70** on June 29 and **$4.69** on June 30 — **−39.1%** | our price series (`runup_t120_cache.json`) |
| T-120 → T-1 | Run-up into the 2026 decision: **+36.3%** | already published on `/fda-decision/UNCY-2026-06-30` |
| 2026-08-12 | *"The Company's third-party vendor has received written notification from the FDA that the facility inspection has been assigned."* Cash, equivalents and securities **$61.4M**, *"expected runway into 2027."* Company *"expects to resubmit… assuming completion of successful inspection."* | Unicycive Q2 release, GlobeNewswire 3343539 |

**Every row above is a quotation or a close-to-close arithmetic. Nothing is inferred.**

---

# 2. THE SENTENCE THAT MAKES IT A CASE STUDY — and stays inside the line

The structural fact, stated as a fact:

> **Whether and when the FDA inspects a contract manufacturer's facility is not publicly scheduled and is not disclosed in advance.** Neither the clinical data, the September 2025 Type A meeting, the acceptance of the resubmission, nor the FDA's conditional acceptance of the brand name in March 2026 indicated whether that inspection would take place inside the six-month review window. The company's own statement on June 30, 2026 was that it did not.

Then, and only then, **our editorial position — a statement about us, not about anyone else:**

> pdufa.bio does not publish approval probabilities. This application is one reason why: across two review cycles, FDA raised no efficacy or safety deficiency, and the outcome turned each time on the compliance status of a third-party facility — information that was not available to anyone outside FDA and the vendor before the letter arrived. We publish what is documented, link the document, and record what happened.

That is the whole argument. It doesn't need a competitor's odds to make it.

## What the page must NOT contain (guarded)

| Banned | Why |
|---|---|
| *"any model would have…"* / *"a probability score would have said…"* | a counterfactual prediction — the thing we don't do |
| any competitor name or their published odds for UNCY | attack posture; defamation surface; not needed |
| *"CMC CRLs usually resolve"* / *"likely to be approved after inspection"* / *"third time"* | forward-looking |
| *"rejected"* / *"failed"* | it is a Complete Response Letter; the letter itself says *"cannot approve… in its present form"* |
| *"the FDA didn't bother to inspect"* or any characterisation of FDA's motive | we quote FDA's letter and the company's statement; we do not editorialise about why |
| Any stock-move verb beyond "closed at" | the −29.9% and −39.1% are close-to-close arithmetic, stated as such |

**Guard:** `test_case_study_vocabulary.py` — the page fails the build on any of: "would have", "probability", "odds", "likely", "rejected", "failed", "bother", any competitor domain. Prove 0 → 1 → 0.

---

# 3. TWO THINGS THE COMPANY SAID vs. WHAT FDA WROTE — keep both, attribute both

There is a small but real gap between the company's framing and FDA's, and the page must not collapse it:

- **Company (June 30):** *"FDA inspection of third-party facility did not occur during the NDA resubmission review."*
- **FDA (June 29):** *"Following a CGMP inspection of [facility]… FDA conveyed deficiencies… may require re-inspection… Satisfactory outcomes of both the PAI and the CGMP surveillance inspections will be needed prior to approval."*

Both are true and they are not the same sentence. FDA's letter refers back to the deficiencies from the earlier inspection and states what is *needed*; the company states what *did not happen* during the window. **Attribute each to its author. Do not write "the FDA did not re-inspect" as an unattributed fact** — write *"the company said the inspection did not occur during the review; the FDA's letter states that satisfactory PAI and CGMP inspection outcomes will be needed before approval."*

---

# 4. WHERE IT LIVES, AND WHY THIS ALSO SERVES THE MOAT

**Page:** `/case-studies/uncy-oxylanthanum-carbonate-two-crls` (or under `/learn/`). Linked from `/fda-decision/UNCY-2026-06-30`, `/fda-decision/UNCY-2025-06-30`, `/drug/oxylanthanum-carbonate`, `/crl`, and `/methodology` where the no-probabilities policy is stated.

**Why it earns citations:** it answers, in sourced sentences, the questions a reader (and an AI answer box) actually asks after a CRL — *"why did UNCY get a CRL"*, *"was it clinical or manufacturing"*, *"what does the FDA letter say"*, *"did the FDA inspect"*. Nobody else publishes the FDA letter text alongside the company's release and the price series. It is also the first page on the site that explains the *no-probabilities policy with a worked example* rather than an assertion — which is exactly what the Gemini report wanted, minus the attack.

**Schema:** `Article` + `FAQPage` (the four questions above as Q&A, each answer a sourced sentence) + links to both letters as `citation`.

---

# 5. TWO DEFECTS FOUND WHILE RESEARCHING THIS

1. **`/fda-decision/UNCY-2026-06-30` does not link the FDA letter we hold.** `/crl` lists both `NDA218607` PDFs, but the decision page has no `fda.gov` or letter link. UNCY is one of the 40 unlinked CRL pages — and now the most important one. **Acceptance:** both UNCY decision pages link their respective letter.
2. **`runup_t120_cache.json` carries `UNCY|2026-06-29` and `UNCY|2026-06-30` as two events** — goal date and decision date keyed separately, same price series. **78 same-ticker pairs within three days** exist in the cache (ARQT 06-29/06-30, ACHV 06-20/06-22, ASND 02-27/02-28, …). Some are legitimate (ABBV had several approvals in one week); some look like goal-vs-decision double keys. **Unverified whether the published 1,845 de-duplicates these.** `runup_study_stats.json` reads from `conference_runup_PUBLISHED.csv`-style source, not this cache, so it may be clean — but the builder should confirm with a one-line count and state the de-dup rule on `/runup-by-year`. If the 1,845 includes double-keyed events, the n is wrong on the site's most-quoted study.

---

# 6. THE PAGE, DRAFTED (plain language, ready to red-team)

> **Two Complete Response Letters, no clinical deficiency: what happened to Unicycive's oxylanthanum carbonate**
>
> Unicycive Therapeutics (UNCY) applied to the FDA to market oxylanthanum carbonate, a phosphate binder for people with kidney disease on dialysis. The FDA has now declined to approve it twice — on June 27, 2025 and June 29, 2026 — and both letters are public. We hold both. Neither raises a concern about whether the drug works or whether it is safe.
>
> **What the FDA wrote.** The only deficiency in the 2025 letter is under the heading *Facility Inspections*: after inspecting the contract manufacturer, the FDA "conveyed deficiencies to the representative of the facility" on a Form 483. The 2026 letter carries the same heading and adds that the facility's responses "may require re-inspection" and that "satisfactory outcomes of both the PAI and the CGMP surveillance inspections will be needed prior to approval." Every other section — labeling, carton, brand name — reads "we reserve comment until the application is otherwise adequate." In March 2026 the FDA had found the proposed brand name conditionally acceptable.
>
> **What the company said.** After the 2025 letter, Unicycive met the FDA in September 2025 and reported that the agency "did not express any concerns about the third-party manufacturer's progress." It resubmitted, and the FDA set a June 29, 2026 goal date. On June 30, 2026 the company announced the second letter and stated that "FDA inspection of third-party facility did not occur during the NDA resubmission review" and that the FDA "did not raise concerns regarding the clinical efficacy or safety data." On August 12, 2026 it said the FDA had assigned a facility inspection, and that it held $61.4 million with runway into 2027.
>
> **What the stock did.** UNCY closed at $6.80 the day the 2025 letter was dated and $4.77 the next trading day, down 29.9%. It closed at $7.70 the day the 2026 letter was dated and $4.69 the next trading day, down 39.1%. In the 120 trading days before the 2026 decision it had risen 36.3%.
>
> **Why this page exists.** Whether and when the FDA inspects a contract manufacturer is not publicly scheduled and is not disclosed in advance. Nothing available outside the FDA and the vendor — not the clinical data, not the Type A meeting, not the accepted resubmission, not the conditionally approved brand name — showed whether that inspection would happen inside the review window. pdufa.bio does not publish approval probabilities. This is one reason. We publish what is documented, link the documents, and record what happened.
>
> *Sources: FDA Complete Response Letters, NDA 218607, dated June 27, 2025 and June 29, 2026 (linked). Unicycive Therapeutics releases dated June 30, 2026 and August 12, 2026 (linked). Prices are daily closes. Informational and educational only — not investment advice.*

**Red-team of my own draft:** no forward-looking verb · no competitor · no "would have" · FDA and company attributed separately · "declined to approve" tracks the letter's "cannot approve in its present form" · every number is a close or a quotation · the policy paragraph is about us. **It passes.**

---

# 7. ORDER

| # | Item | Acceptance |
|---|---|---|
| 1 | Publish the case-study page per §6, with both FDA letters and both releases linked, `Article` + `FAQPage` schema | 200; contains "Reference ID 5825414", "did not occur during the NDA resubmission review", "−29.9%", "−39.1%", "$61.4 million"; zero banned tokens; both PDF links resolve |
| 2 | Link the FDA letter from `/fda-decision/UNCY-2026-06-30` and `/fda-decision/UNCY-2025-06-30` | each page has an `href` to its `NDA218607` letter |
| 3 | Cross-link from `/methodology` ("we do not publish approval probabilities — see the UNCY case") and `/crl` | links present |
| 4 | Confirm the 1,845 de-duplicates goal-vs-decision double keys; state the rule on `/runup-by-year` | one sentence on the page; builder reports the count of pairs collapsed |
| 5 | `test_case_study_vocabulary.py` | 0 → 1 → 0 |

---
*FDA letters read from the openFDA CRL corpus on disk (`CRL_NDA218607_20250627.pdf`, `CRL_NDA218607_20260629.pdf`). Company statements from GlobeNewswire releases 3319541 and 3343539. Prices from our own daily-close caches. Not investment advice.*
