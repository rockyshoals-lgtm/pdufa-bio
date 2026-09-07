# UNCY case study, red-teamed: every fact public, every source linked, built for citation
**2026-09-06 20:40 Pacific. Every URL below was fetched and returned 200 this evening. Every price was checked against Yahoo Finance historical data, not only our own cache.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. RESULT OF THE RED TEAM ON MY OWN SPEC

Six corrections to the draft I filed two hours ago. All are now fixed in the page copy in section 4.

| What I wrote | What the source says | Fix |
|---|---|---|
| "on 4.77M shares vs ~1M on the prior days" | Yahoo: June 30, 2025 volume 4,766,100; June 27, 2025 volume 1,816,100 | exact figures, public source linked |
| "The FDA has now declined to approve it twice" | Letter: "determined that we cannot approve this application in its present form" | use FDA's phrase |
| "Sept 2025 Type A meeting" (one source) | June 30, 2026 release says the meeting was in September 2025; the company's own update on it is dated October 28, 2025 | cite both releases, both dated |
| 2025 CRL cause | 2025 release adds a qualifier I omitted: deficiencies "at a third-party manufacturing vendor **unrelated to** Oxylanthanum Carbonate (OLC)" | quote it verbatim, paired with FDA's "may not be specific to your pending application" |
| FDA letters cited by corpus file name only | Public URLs exist and resolve: `https://download.open.fda.gov/crl/CRL_NDA218607_20250627.pdf` and `..._20260629.pdf` | link the PDFs, plus the openFDA API record |
| No decision-day volume for 2026 | Yahoo: June 30, 2026 volume 20,126,100 vs 2,593,500 the day before | add it; it is public and it is striking |

One thing I could not source publicly and have therefore relabelled: the "+36.3% run-up over 120 trading days" is **our measurement** from our price series. It stays, labelled as pdufa.bio's measurement with the method stated, linking our decision page. It is not presented as a third-party fact.

And per David's note: **no em dashes in the page copy.** The draft in section 4 uses none. Commas, colons and full stops do the work.

---

# 1. THE SOURCE LEDGER: every fact, its public URL, fetched 200

| # | Fact | Public source (fetched 2026-09-06) |
|---|---|---|
| S1 | FDA CRL, NDA 218607, dated June 27, 2025. Only deficiency heading: FACILITY INSPECTIONS. "Following a Current Good Manufacturing Practices (CGMP) inspection and pre-approval inspection (PAI) of [redacted] listed in this submission, FDA conveyed deficiencies to the representative of the facility… on the FDA Form 483." Labeling: "We reserve comment on the proposed labeling until the application is otherwise adequate." | https://download.open.fda.gov/crl/CRL_NDA218607_20250627.pdf |
| S2 | Company announces the 2025 CRL: deficiencies "at a third-party manufacturing vendor unrelated to Oxylanthanum Carbonate (OLC), with no other concerns stated, including pre-clinical, clinical, or safety data." | https://www.globenewswire.com/news-release/2025/06/30/3107365/0/en/ (GlobeNewswire 3107365) |
| S3 | UNCY daily closes: June 27, 2025 close $6.80, volume 1,816,100. June 30, 2025 close $4.77, volume 4,766,100. | https://finance.yahoo.com/quote/UNCY/history/ (Nasdaq daily closes; also in our series) |
| S4 | Type A meeting with FDA held September 2025 to discuss "the single deficiency identified in the CRL related to the compliance status of a third-party manufacturing vendor. No other concerns have been identified to the Company." Company plans to resubmit by year-end. | https://www.globenewswire.com/news-release/2025/10/28/3175258/0/en/ (GlobeNewswire 3175258, Oct 28, 2025) |
| S5 | NDA resubmitted. | https://ir.unicycive.com/news/detail/116/ |
| S6 | FDA accepts the resubmission as "a Class II complete response which has a six-month review period" and sets a PDUFA target action date of **June 29, 2026**. "The FDA did not raise any concerns regarding OLC's preclinical, clinical, or safety data included in the original NDA submission." Cash $41.3M, runway into 2027. | https://www.globenewswire.com/news-release/2026/01/29/3228698/0/en/ (GlobeNewswire 3228698, Jan 29, 2026) |
| S7 | FDA correspondence of March 25, 2026 finds the proposed proprietary name "conditionally acceptable pending approval of the application in the current review cycle." | S8 letter, PROPRIETARY NAME section |
| S8 | FDA CRL, NDA 218607, dated June 29, 2026, Reference ID 5825414. Only deficiency heading: FACILITY INSPECTIONS. "The facility's satisfactory responses are dependent on FDA's determination that the facility has come into compliance with CGMP and may require re-inspection of the facility. The deficiencies identified during the inspection may not be specific to your pending application… Following resolution of the CGMP inspection, FDA may need to conduct a pre-approval inspection (PAI) of the facility. Satisfactory outcomes of both the PAI and the CGMP surveillance inspections will be needed prior to approval of the application." | https://download.open.fda.gov/crl/CRL_NDA218607_20260629.pdf |
| S9 | Company announces the 2026 CRL. Headline bullets verbatim: "Complete Response Letter relates to deficiencies previously identified at third-party manufacturing vendor"; "FDA inspection of third-party facility did not occur during the NDA resubmission review"; "FDA did not raise concerns regarding the clinical efficacy or safety data of OLC, and no additional data was requested." Body: "The FDA did not express any concerns about the third-party manufacturer's progress and no additional issues were raised by the FDA at the Type A meeting." | https://www.globenewswire.com/news-release/2026/06/30/3319541/0/en/ (GlobeNewswire 3319541, June 30, 2026, 07:05 ET) |
| S10 | UNCY daily closes: June 29, 2026 close $7.70, volume 2,593,500. June 30, 2026 close $4.69, volume 20,126,100. | https://finance.yahoo.com/quote/UNCY/history/ |
| S11 | "The Company's third-party vendor has received written notification from the FDA that the facility inspection has been assigned." Cash, equivalents and marketable securities $61.4M as of June 30, 2026, "expected runway into 2027." | https://www.globenewswire.com/news-release/2026/08/12/3343539/0/en/ (GlobeNewswire 3343539, Aug 12, 2026) |
| S12 | Both letters as structured records (letter_date, application_number, approval_status "Unapproved", full text) | https://api.fda.gov/transparency/crl.json?search=application_number:"NDA 218607" |
| M1 | pdufa.bio measurement: UNCY rose 36.3% from 120 trading days before the June 29, 2026 goal date to the last close before it (close to close). | https://www.pdufa.bio/fda-decision/UNCY-2026-06-30 (method stated on the page) |

Arithmetic, all close to close: 6.80 → 4.77 is −29.9%. 7.70 → 4.69 is −39.1%. Volume on June 30, 2026 was 7.8× the prior day.

**Nothing on the page will rest on a source outside this table.** Twelve public documents and one labelled measurement of our own.

---

# 2. WHAT THE RED TEAM CONFIRMS IS INSIDE THE MANDATE

| Test | Result |
|---|---|
| Every fact is publicly available | Yes. Two FDA letters (openFDA), six company releases (GlobeNewswire / SEC-filed), Nasdaq closes (Yahoo). No private data, no vendor feed, no paywalled source. |
| Every fact links its source | Yes. Twelve URLs, each fetched 200 tonight. Our one measurement links our page and states its method. |
| No prediction | Yes. No sentence about the third resubmission, the assigned inspection's outcome, or the stock. |
| No competitor named, no odds quoted | Yes. The argument is made entirely by FDA's two letters. |
| No characterisation of FDA's motive | Yes. "The company said the inspection did not occur during the review" is attributed; FDA's "will be needed prior to approval" is quoted. The two are not merged into "FDA didn't bother." |
| Never "rejected" or "failed" | Yes. FDA's phrase: "cannot approve this application in its present form." |
| The policy sentence is about us | Yes. "pdufa.bio does not publish approval probabilities. This application is one reason why." |
| No em dashes | Yes. |

---

# 3. WHY THIS PAGE WILL BE CITED, AND HOW TO BUILD IT SO IT IS

AI answer boxes lift **one declarative sentence that contains the entity, a number or date, and a source**. This page has several that no other site has, because no other site puts the FDA letter text next to the company release next to the closes:

**The five most quotable sentences on the page (the builder should keep each one intact, on its own line, in the HTML):**

1. *"The FDA's two Complete Response Letters to Unicycive for oxylanthanum carbonate (NDA 218607), dated June 27, 2025 and June 29, 2026, each list one deficiency category, facility inspections, and neither raises an efficacy or safety concern."*
2. *"The June 29, 2026 letter states that satisfactory outcomes of both a pre-approval inspection and a CGMP surveillance inspection of the contract manufacturer will be needed before approval."*
3. *"Unicycive stated on June 30, 2026 that the FDA's inspection of the third-party facility did not occur during the six-month resubmission review."*
4. *"UNCY closed at $7.70 on June 29, 2026 and $4.69 on June 30, 2026, a fall of 39.1 percent on volume of 20.1 million shares against 2.6 million the day before."*
5. *"Whether and when the FDA inspects a contract manufacturer is not publicly scheduled and is not disclosed in advance."*

**Build rules for citation:**

- **Title answers the query.** `Why did Unicycive (UNCY) receive two Complete Response Letters for oxylanthanum carbonate? The FDA letters, the company statements, and the stock, with sources`. Queries this matches: "why did UNCY get a CRL", "oxylanthanum carbonate CRL reason", "Unicycive FDA inspection", "UNCY complete response letter 2026".
- **`FAQPage` schema with four questions**, each answer one of the sentences above, verbatim, with the source URL in the answer text: *Was the CRL about efficacy or safety?* / *What does the FDA letter say?* / *Did the FDA inspect the manufacturer?* / *What did the stock do?*
- **`Article` schema** with `citation` array listing S1, S2, S6, S8, S9, S11 URLs; `dateModified` set from the build; `author` pdufa.bio.
- **Both FDA PDFs linked inline at first mention and again in a Sources block.** The openFDA API record (S12) linked once as "structured record."
- **Every quotation in `<blockquote cite="URL">`**. Search engines and AI extractors treat `cite` as provenance.
- **One `<table>` with a `<caption>`**: "Timeline of NDA 218607, June 2025 to August 2026, with sources". Captioned tables are extracted as `Table_title` by both engines.
- **Plain language throughout**, per the house spec. "Contract manufacturer" not "CMO"; "the FDA's letter" not "the action letter"; "cannot approve in its present form" explained once as "the FDA's standard wording when it declines to approve for now."
- **Internal links**: from `/fda-decision/UNCY-2026-06-30`, `/fda-decision/UNCY-2025-06-30`, `/drug/oxylanthanum-carbonate`, `/ticker/UNCY`, `/crl`, `/methodology` (at the sentence where the no-probabilities policy is stated), and `/learn/what-is-a-pdufa-date` (at "Class II, six-month review").
- **Guard** `test_case_study_vocabulary.py`: fail on "would have", "probability", "odds", "likely", "rejected", "failed", "bother", any competitor domain, and the em dash character. Prove 0 → planted 1 → healed 0.

---

# 4. THE PAGE, RED-TEAMED COPY (no em dashes)

> # Why did Unicycive receive two Complete Response Letters for oxylanthanum carbonate?
> ## The FDA's letters, the company's statements, and the stock, with every source linked
>
> Unicycive Therapeutics (Nasdaq: UNCY) applied to the FDA to market oxylanthanum carbonate, an oral phosphate binder for people with chronic kidney disease on dialysis. The application is NDA 218607, filed under the 505(b)(2) pathway. The FDA has twice determined that it "cannot approve this application in its present form," on June 27, 2025 and on June 29, 2026. Both letters are public. Neither raises a concern about whether the drug works or whether it is safe.
>
> ### What the FDA wrote
>
> The FDA's two Complete Response Letters, dated June 27, 2025 and June 29, 2026, each list one deficiency category, facility inspections, and neither raises an efficacy or safety concern.
>
> The 2025 letter states that after "a Current Good Manufacturing Practices (CGMP) inspection and pre-approval inspection (PAI)" of the contract manufacturer, "FDA conveyed deficiencies to the representative of the facility" on a Form 483. The 2026 letter states that the facility's responses "may require re-inspection of the facility," that the deficiencies "may not be specific to your pending application," and that "satisfactory outcomes of both the PAI and the CGMP surveillance inspections will be needed prior to approval of the application." Every other section of both letters, covering labeling, carton and brand name, reads "we reserve comment on the proposed labeling until the application is otherwise adequate." In correspondence dated March 25, 2026, the FDA had found the proposed brand name conditionally acceptable pending approval.
>
> Sources: FDA letter of June 27, 2025 (PDF). FDA letter of June 29, 2026, Reference ID 5825414 (PDF). Both letters as structured records on openFDA.
>
> ### What the company said
>
> On June 30, 2025 Unicycive said the deficiencies were "at a third-party manufacturing vendor unrelated to Oxylanthanum Carbonate (OLC), with no other concerns stated." It met the FDA in September 2025 and reported on October 28, 2025 that the meeting addressed "the single deficiency identified in the CRL related to the compliance status of a third-party manufacturing vendor" and that no other concerns had been identified. It resubmitted the application, and on January 29, 2026 announced that the FDA had accepted it as a Class II resubmission with a six-month review and a goal date of June 29, 2026.
>
> On June 30, 2026 Unicycive announced the second letter and stated that "FDA inspection of third-party facility did not occur during the NDA resubmission review" and that the FDA "did not raise concerns regarding the clinical efficacy or safety data of OLC, and no additional data was requested." On August 12, 2026 it said the FDA had assigned a facility inspection to the vendor, and reported $61.4 million in cash, cash equivalents and marketable securities with expected runway into 2027.
>
> Sources: releases of June 30, 2025; October 28, 2025; January 29, 2026; June 30, 2026; August 12, 2026.
>
> ### What the stock did
>
> UNCY closed at $6.80 on June 27, 2025, the date of the first letter, and at $4.77 on June 30, 2025, a fall of 29.9 percent on 4.8 million shares against 1.8 million the day before. It closed at $7.70 on June 29, 2026, the date of the second letter, and at $4.69 on June 30, 2026, a fall of 39.1 percent on 20.1 million shares against 2.6 million the day before. By pdufa.bio's measurement, the stock had risen 36.3 percent over the 120 trading days before the June 29, 2026 goal date, close to close.
>
> Sources: Nasdaq daily closes (Yahoo Finance history). pdufa.bio decision record for June 30, 2026, method stated there.
>
> ### Why this page exists
>
> Whether and when the FDA inspects a contract manufacturer is not publicly scheduled and is not disclosed in advance. Nothing available outside the FDA and the vendor, not the clinical data, not the September 2025 meeting, not the accepted resubmission, not the conditionally accepted brand name, showed whether that inspection would take place inside the review window. The company's statement is that it did not.
>
> pdufa.bio does not publish approval probabilities. This application is one reason why. Across two review cycles the FDA raised no efficacy or safety deficiency, and each outcome turned on the compliance status of a third-party facility, which no one outside the FDA and the vendor could observe before the letter arrived. We publish what is documented, link the document, and record what happened.
>
> | Date | Event | Source |
> |---|---|---|
> | 2025-06-27 | FDA letter: cannot approve in present form; facility inspections | FDA PDF |
> | 2025-06-30 | Company announces; UNCY $6.80 → $4.77 | Release; Nasdaq |
> | 2025-09 / 2025-10-28 | Type A meeting; company update | Release |
> | 2026-01-29 | Resubmission accepted, Class II, goal date 2026-06-29 | Release |
> | 2026-03-25 | FDA: proprietary name conditionally acceptable | FDA PDF (2026) |
> | 2026-06-29 | FDA letter: cannot approve in present form; facility inspections; re-inspection and PAI needed before approval | FDA PDF |
> | 2026-06-30 | Company: inspection did not occur during review; UNCY $7.70 → $4.69 | Release; Nasdaq |
> | 2026-08-12 | Company: FDA has assigned the facility inspection; $61.4M cash | Release |
>
> *Informational and educational only. Not investment advice. pdufa.bio does not predict FDA decisions or publish approval probabilities. Every date and quotation above links its source; verify against the FDA and SEC documents directly.*

**Second red-team pass on this copy:** twelve source links, one labelled measurement; FDA quoted, company quoted, never merged; no forward verb; no competitor; no "rejected"; no em dash; the policy paragraph describes pdufa.bio only. **Passes.**

---

# 5. ORDER FOR THE BUILDER (08:20 slot)

| # | Item | Acceptance (run live) |
|---|---|---|
| 1 | Publish `/case-studies/unicycive-oxylanthanum-carbonate-two-crls` with the section 4 copy, the twelve source links, the captioned timeline table, `Article` + `FAQPage` schema with `citation` | 200; page contains "Reference ID 5825414", "did not occur during the NDA resubmission review", "unrelated to Oxylanthanum Carbonate", "29.9 percent", "39.1 percent", "20.1 million"; all twelve source URLs present and each returns 200; zero em dashes; zero banned tokens |
| 2 | Link both FDA PDFs from `/fda-decision/UNCY-2026-06-30` and `/fda-decision/UNCY-2025-06-30` | each decision page has an `href` to `download.open.fda.gov/crl/CRL_NDA218607_…pdf` |
| 3 | Cross-links from `/methodology` (at the no-probabilities sentence), `/crl`, `/drug/oxylanthanum-carbonate`, `/ticker/UNCY` | each contains an `href` to the case study |
| 4 | `test_case_study_vocabulary.py` (banned tokens + em dash) | proven 0 → 1 → 0 |
| 5 | Sitemap + IndexNow submit for the new URL | present in sitemap; IndexNow 200 |
| 6 | Confirm the run-up study's 1,845 de-duplicates goal-vs-decision double keys (UNCY 2026-06-29 vs 2026-06-30 and 77 similar pairs in `runup_t120_cache.json`); state the rule on `/runup-by-year` | one sentence on the page; count of collapsed pairs reported in the ack |

---

*Sources fetched and verified 2026-09-06 20:40 Pacific. FDA letters from openFDA (download.open.fda.gov/crl). Company statements from GlobeNewswire. Prices from Yahoo Finance historical data, cross-checked against pdufa.bio's own daily-close series. Not investment advice.*
