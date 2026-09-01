# Plain-language spec + red-team protocol
**Standing reference · v1 · 2026-08-12**
*How we write facts so a non-scientist understands them, without losing an ounce of accuracy — and how I will audit every published claim afterwards.*

---

# PART 1 — THE WRITING SPEC

## 1.1 The governing rule

> **Simplify the language. Never simplify the fact.**

Every sentence must survive two tests:
1. **Comprehension** — would a retail investor with no biology background understand this on first read?
2. **Defensibility** — if a clinical scientist read it next to the primary source, would they say "that's correct"?

If a phrasing passes (1) but fails (2), it is worse than jargon. **Vagueness is the failure mode to fear, not complexity.** "The study was small" is vague. "42 people took the drug" is plain *and* precise.

## 1.2 The house sentence pattern

**Fact first, in one sentence with a number and a date. Then the plain-English meaning. Then the caveat.**

> **FDA approved Gwyn Lo on July 29, 2026.** It's a skin patch that prevents pregnancy, worn one week at a time. It was approved only for women with a BMI under 30 — the studies didn't establish that it works above that.

That's three sentences: what happened, what it is, what the limit is. No jargon, nothing softened.

## 1.3 Translation table — jargon → plain English → what NOT to say

The third column is the important one. It lists the *tempting* simplification that would make us wrong.

| Term | Say this | ❌ Never say this |
|---|---|---|
| **Single-arm trial** | "Everyone in the study got the drug. There was no comparison group." | "The study was weak / unreliable" — that's a judgement, and single-arm trials are standard and accepted in oncology |
| **Control arm / comparator** | "A second group who got a different treatment, so results could be compared" | "The placebo group" — a comparator is often an active drug, not placebo |
| **Randomized** | "Patients were sorted into groups by chance, not by choice" | "Fair" / "unbiased" — randomisation reduces one specific bias, it doesn't make a trial correct |
| **Double-blind** | "Neither the patients nor their doctors knew who got which treatment" | "Nobody knew" — the sponsor and monitors often do |
| **Placebo-controlled** | "Compared against a dummy treatment with no active ingredient" | "Compared against nothing" — placebo is not nothing, that's the point |
| **Primary endpoint** | "The main question the study was built to answer" | "The goal" — a study can miss its primary endpoint and still be useful |
| **Met its primary endpoint** | "The study answered its main question in the drug's favour" | "The drug worked" — meeting an endpoint is a statistical result, not proof of benefit |
| **ORR (objective response rate)** | "The share of patients whose tumours shrank by a set amount" | "Cure rate" / "success rate" — shrinkage is not cure and is not survival |
| **PFS (progression-free survival)** | "How long patients lived without their disease getting worse" | "How long they lived" — that's OS, a different measure |
| **OS (overall survival)** | "How long patients lived" | — |
| **Median** | "The middle value — half were higher, half lower" | "Average" — median and mean are different, and the difference matters in survival data |
| **Hazard ratio 0.65** | "In this study, the event happened about 35% less often in the treated group" | "The drug is 35% better" — a hazard ratio is not a percentage improvement in outcome |
| **p < 0.05 / statistically significant** | "A result this large would be unlikely to happen by chance alone" | "Proven" / "significant" in the everyday sense — statistical significance is not importance |
| **95% confidence interval** | "The range the true value most likely falls in" | Omitting it — a number without its range invites over-reading |
| **Pearl Index 4.14 (95% CI 2.77–5.95)** | "About 4 pregnancies per 100 women per year of use. The study's range was roughly 3 to 6." | "96% effective" — that's a different calculation and not what the Pearl Index states |
| **Surrogate endpoint** | "A stand-in measurement used because the real outcome takes years to observe" | "Proof it works" — a surrogate is a proxy, sometimes a poor one |
| **Non-inferiority trial** | "Designed to show the drug is not meaningfully worse than an existing one — not that it's better" | "As good as" / "just as effective" — non-inferiority has a pre-set margin |
| **Accelerated approval** | "Approved early on promising but incomplete evidence. The company must run more studies to confirm the benefit, and the FDA can withdraw it." | "Approved" full stop — the conditional nature is the whole point |
| **Complete Response Letter (CRL)** | "The FDA declined to approve it in its current form and told the company what's missing" | "Rejected" / "denied" — a CRL is not final; many drugs are approved after one |
| **PDUFA date** | "The deadline the FDA has set itself to decide" | "The approval date" — it's a decision deadline, and the FDA can act early, late, or issue a CRL |
| **AdComm vote 3–9 against** | "An outside panel of experts voted 3 in favour, 9 against. The FDA usually follows this advice but doesn't have to." | "The FDA rejected it" — the panel is advisory and is not the FDA |
| **505(b)(2)** | "An approval route that lets a company rely partly on studies already done for a similar drug" | "A shortcut" — it has its own full evidence requirements |
| **Orphan designation** | "A status for drugs treating rare diseases, which comes with incentives and extra market protection" | "Approval" — designation is not approval |
| **Breakthrough therapy** | "A status that speeds up FDA review for drugs showing early promise" | "The FDA thinks it works" — it's a process designation |
| **Loss of exclusivity** | "The earliest date no listed patent or exclusivity blocks a generic from entering" | "The day it goes generic" — settlements, litigation and term extensions can move the real date |
| **Composition-of-matter patent** | "A patent on the drug molecule itself — usually the hardest to work around" | "The patent" — most drugs have many, of different strengths |

## 1.4 Numbers: rules that keep us accurate

1. **Always attach n.** "72% responded" is unquotable. "72% of 140 patients responded" is a fact.
2. **Always attach the date.** Facts about drugs expire.
3. **Never convert between measures.** Don't turn a hazard ratio into "% better", or a Pearl Index into "% effective". Report what the source reported.
4. **Never compare numbers from different studies** — see `/learn/why-cross-trial-comparisons-mislead`. This is the single most common error in retail biotech writing.
5. **Round honestly.** 33.6% → "about 34%" is fine. → "roughly a third" is fine. → "over a third" is wrong.
6. **Give the range when the source gives one.** A confidence interval left out is information removed.

## 1.5 Worked examples on our own data

**REPL / TUDRIQEV — the hard case (single-arm, twice refused, then approved)**
> On August 6, 2026 the FDA approved TUDRIQEV for advanced melanoma that has stopped responding to other treatment. This was an **accelerated approval**, meaning the evidence was promising but incomplete — Replimune has to run more studies to confirm the benefit, and the FDA can withdraw the approval if they don't.
>
> The main study, IGNYTE, gave the drug to 140 patients with no comparison group, so there's no direct read on how they'd have done on something else. About 34% saw their tumours shrink, and among those, the effect lasted a median of about 25 months.
>
> The FDA had declined to approve this drug twice before, both times citing the lack of a comparison group. An outside expert panel voted 10–3 in its favour on July 30, 2026.

Every clause is sourced. No jargon. Nothing softened — the two prior refusals stay in.

**CAPR — a negative vote, stated without editorialising**
> On July 29, 2026 an outside panel of experts advising the FDA voted **3 in favour and 9 against** on whether the evidence shows Deramiocel works for heart problems in Duchenne muscular dystrophy. The FDA usually follows this advice but is not required to. Its own decision is due **August 22, 2026**.

**Patent cliff — plain, with the limit stated**
> **SPRYCEL loses its last patent protection on September 28, 2026.** Bristol Myers Squibb listed 12 patents on it with the FDA; that's the last one to expire.
>
> This is the earliest date a generic *could* enter — not a guarantee one will. Companies often settle lawsuits with generic makers for a different date, and those agreements aren't public in this data.

## 1.6 Reading level and formatting
- **Target: 8th–10th grade.** Short sentences. One idea each.
- **Define on first use, every page** — readers arrive from search, not from your homepage.
- **Bold the fact, not the adjective.** Bold "September 28, 2026", never "huge".
- **Numbers as digits** ("12 patents"), not words.
- No em dashes as connectors in body copy (house style, already enforced by the build).

## 1.7 Being quotable (this is also the AI-citation format)
The pattern that gets us cited is the same one that helps humans:

> **Q: When is the SPRYCEL patent expiring?**
> **A:** SPRYCEL's last listed patent expires on September 28, 2026. That's the earliest a generic could enter, though settlements can change the actual date.

One-sentence answer, containing a number and a date, followed by the honest limit. Put it in `FAQPage` schema. This is why the drug pages get cited and the calendar doesn't.

---

# PART 2 — RED-TEAM PROTOCOL

When the builder ships, I audit against this. It is adversarial by design: **I try to find the claim that is wrong, not confirm the ones that are right.**

## 2.1 Severity ladder

| Level | Definition | Action |
|---|---|---|
| **S1 — False fact** | A published statement contradicted by primary source | **Pull the page immediately**, then correct + log on `/corrections` |
| **S2 — Unsupported** | Stated as fact, no primary source, or source doesn't say it | Retract or downgrade to explicitly "unverified" |
| **S3 — Misleading-but-true** | Technically accurate, predictably misread | Rewrite |
| **S4 — Imprecise** | Missing n, date, range, or unit | Fix in the next build |
| **S5 — Style** | Jargon, reading level, formatting | Batch |

## 2.2 What I check, every claim

**Provenance**
- Does every factual claim have a primary source (FDA, SEC, sponsor PR, Orange Book)?
- Does the source **actually say it**? — I open the source and read it. This is where the SLS false CRL was caught.
- Is the source URL the *right* document? (REPL's approval was sourced to the AdComm 8-K — right company, wrong event.)
- No same-domain URL counted as a "primary source".

**Numbers**
- n present · date present · units correct · range given where the source gives one
- No cross-trial comparison, anywhere, in any form
- No derived metric the source didn't publish (no HR→"% better", no Pearl Index→"% effective")
- Arithmetic re-computed independently from source values

**Entity accuracy**
- Right drug, right company, right indication, right dose/strength
- *(We have already shipped: bevacizumab attributed to BMY; ZORYVE 0.05% vs 0.3% collision; LNTH's page showing another molecule's CRL. This class of error is our most frequent — I check it hardest.)*

**Regulatory precision**
- CRL described as "declined in current form", never "rejected"
- Accelerated approval always flagged as conditional
- AdComm described as advisory, never as the FDA's decision
- Designation ≠ approval
- PDUFA date ≠ approval date
- Goal date vs actual decision date distinguished

**Patent/exclusivity precision** *(new surface — highest risk of confident error)*
- LOE stated as "earliest date no listed patent or exclusivity blocks entry"
- PTE, Paragraph IV settlements, authorised generics disclosed as **not modelled**
- Biologics not implied to be covered by Orange Book data
- Delisted patents excluded
- Every cliff traceable to Appl_No + Patent_No

**Plain-language integrity**
- Spot-check the §1.3 table: has any translation drifted into judgement?
- Would a clinician object to any sentence?
- Has "simplified" become "wrong"?

## 2.3 Method
1. **Sample** — every new page type, plus a random 20 of each at-scale type (drug pages, cliff entries).
2. **Independent re-derivation** — recompute from the primary source without looking at our page first, then compare. Catches inherited errors.
3. **Adversarial read** — for each page: *what's the most damaging true statement someone could make about this page?*
4. **Regression sweep** — re-check every previously-fixed item (the open-items file's §6 closed list).
5. **Report** — S1/S2 immediately in chat; full findings filed to the dropbox with verification commands.

## 2.4 Automatable guards (should run in CI, not just my review)
- Reject "rejected" / "denied" adjacent to CRL
- Reject a same-domain URL on a record marked verified
- Reject a number without an adjacent n on statistical claims
- Reject accelerated-approval pages lacking the conditional language
- Reject cliff pages lacking the "not a guarantee" disclosure
- Flag any page comparing two numbers from different NCT IDs
- Existing junk-drug-name guard, extended to comparison and cliff pages

**Automate what's mechanical so my review is spent on judgement, not spellcheck.**

## 2.4b Verification commands must be able to fail
*Added 2026-08-12 after I got this wrong three times running.*

I asserted for five days that `bing_rank_report.py` needed migrating off a "legacy" Bing API, verified with:

```bash
grep -c "api.svc/json" bing_rank_report.py    # "expect 0 after fix"
```

`api.svc/json` is the protocol Microsoft is migrating people **to**. SOAP and POX are what retire. The command could only ever confirm the finding — it grepped for the string I'd assumed was legacy and read its presence as exposure. The builder had to refute it three times before I checked the one fact the item rested on.

**Standing rules:**
1. **A verification command that presumes its conclusion is not verification.** Target the failure condition (`api.svc/soap|api.svc/pox`), never the thing you expect to find.
2. **State what a passing result looks like before running it.** If no realistic output would clear the item, the test is wrong.
3. **A check that never fails is not a strong check** — it may be aimed at the wrong target. This is the identical failure to the conference miner's edition-mismatch: both look rigorous, both confirm the wrong thing with perfect consistency.
4. **When the builder pushes back twice, stop re-running the check and go verify the premise.** Repetition is not evidence.

## 2.5 My standing commitment
- I will **not** sign off on a page I could not independently verify. "Probably right" is not a pass.
- I will report **my own** errors as loudly as the builder's — I've already had to correct three in this engagement (soft-404 misread, CAPR vote direction, ticker-page JSON-LD claim), and each is logged.
- If something is unverifiable, the recommendation is to **publish it as unverified or not at all** — never to publish it confidently and hope.

---

# PART 3 — WHY THIS IS THE MOAT

Competitors publish confident numbers with no provenance. We publish **the number, its sample size, its date, its source, and what it does not mean.**

That is more useful to a retail reader, more defensible legally, and — as the AI-citation data already shows — more quotable. The `/decisions` page saying *"449 records · 142 verified · 307 inferred"* and refusing to compute an approval rate from mixed data is the strongest trust signal on the site. Plain language extends that posture to every sentence, rather than diluting it.

**Being the easiest to understand and the hardest to catch out is a single strategy, not two.**

---
*Facts and historical statistics only. Not investment advice. Verify every date and outcome against primary FDA / SEC / company filings.*
