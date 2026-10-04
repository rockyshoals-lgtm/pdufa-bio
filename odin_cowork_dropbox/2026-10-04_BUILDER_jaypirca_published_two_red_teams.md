# Builder: Jaypirca first-line CLL/SLL published, two red-team passes, three site-wide faults found on the way
**2026-10-04, written ~10:35 Pacific = 13:35 Eastern (Sunday).** *RULE 1: times carry their zone.*
*Facts and build mechanics only. Not investment advice.*

David, 10-04: "yes, publish the page, ensure it's quotable, red team to ensure it's factual, and optimized for search engines SEO and Bing." This answers the 10-04 audit's one currency gap (`/fda-decision/LLY-2026-10-02` 404).

## 1. The page: `/fda-decision/LLY-2026-10-02`

| Element | Value |
|---|---|
| title (99 chars) | Jaypirca (pirtobrutinib) Approved Oct 2, 2026 for First-Line CLL/SLL \| LLY FDA Decision \| pdufa.bio |
| meta description | Jaypirca (pirtobrutinib) was approved by the FDA on October 2, 2026 for previously untreated CLL/SLL with no known 17p deletion, based on BRUIN CLL-313. |
| h1 | Jaypirca (pirtobrutinib) FDA approval for first-line CLL/SLL: Oct 2, 2026 |
| FDA date source | FDA approval notification, Oncology/Hematologic Malignancies, posted Fri 10-02 15:31 Eastern. It states "On October 2, 2026". Drugs@FDA has not posted the NDA 216059 supplement letter yet; `sync_fda_action_dates.py` swaps the letter in when it appears. |
| goal date | none held. Lilly guided "second half of 2026" (June 26 release, linked). `goal_unsourced`, **no early or late margin** |
| FAQ | 4 hand-written Q&As (`_decision_extra_faq.json`) plus the generated ones; FAQPage JSON-LD |

Every number on the page is from the FDA notice: BRUIN CLL-313 (NCT05023980), 282 patients 1:1 vs bendamustine plus rituximab; IRC PFS HR 0.20 (95% CI 0.11 to 0.37), p<0.0001; median PFS NE vs 33.5 months; follow-up 28 months; deaths 3 (2.1%) vs 10 (7.1%); serious ARs 28%; 200 mg once daily; orphan designation. No aggregator was used as a source.

## 2. Red team #1 found, fixed

- The title read "Jaypirca (pirtobrutinib) - previously untreated Approved..." because `drug_names` did not strip a suffix with capitals or a slash. The regex is now `\s+-\s+[a-z][A-Za-z0-9 ,'/-]{6,}$`.
- `fix_meta_lengths.py` overwrote the description with "ELI LILLY & Co (LLY) FDA decision...". It now recognises "was approved by the FDA on".
- **Site-wide: no decision page built by `build_decision_page.py` had an FAQ** (JUVMO, Gazyva, Atebrioz, Jaypirca). The title regex never matched answer-format titles. It now falls back to the banner class.
- **Site-wide: the FAQ said "The FDA approved JUVMO on September 28"**, which is the announcement date; the FDA date is 09-25. FAQ answers now take the FDA day from an FDA record only: the dataset `fda_action_date`, `_fda_action_archive.json`, or Drugs@FDA in `_decision_verification.json`. Otherwise the answer says "announced on" and that pdufa.bio holds no FDA record of the day. 349 FAQs were refreshed.
  - New guard: `tests/test_decision_faq_dates.py` (0 → planted 1 → 0).
- **Site-wide: 29 decision pages built from the VERA template carried VERA's BreadcrumbList.** `build_breadcrumbs.py` now replaces any marker block that does not name its own page, and `build_decision_page.py` strips the template's BC, DMOD and DFAQ blocks. 140 breadcrumbs were replaced.
  - New guard: `tests/test_breadcrumb_is_own_page.py` (0 → 1 → 0).
- Articles: "a Eli Lilly" became "an Eli Lilly".
- `/fda-decisions-today` names cut at 40 or 50 characters now use `clean_drug_name`.
- "in Adult patients" on /fda-this-month is now lower case.

## 3. Red team #2 found, fixed

1. **Factual.** The relapsed or refractory CLL/SLL approval (Dec 3, 2025) was stated too broadly in three places: the headline, the timeline and the FAQ. The FDA wording is "who have previously been treated with a covalent BTK inhibitor", and it is now on all three. The MCL qualifier ("after at least two lines of systemic therapy, including a BTK inhibitor") and the Dec 1, 2023 qualifier ("including a BTK inhibitor and a BCL-2 inhibitor") are now on the timeline and the FAQ too.
2. **Drug pages labelled an FDA action day "PDUFA".** `/drug/jaypirca` said "PDUFA · Oct 2, 2026" with no goal date on record. Two rules changed:
   - a `goal_unsourced` decided row now reads **"FDA action"**;
   - an archive-sourced row now reads **"FDA decision"**, because the archive holds the decision day and does not establish that it was also the goal.
   - Five pages carried the error: centanafadine, gazyva, inluriyo, jaypirca and lipfendra.
   - New guard: `tests/test_drug_page_action_label.py`. It found 6 on the rendered pages before the fix, 0 after, 1 with a planted label, then 0.
3. **The drug-page About text read as the drug's only approval** ("Approved indication in our records: Adult patients..."). It now reads "FDA approval tracked on pdufa.bio: adult patients ... (approved Oct 2, 2026). Earlier approvals may not be listed here; the FDA label is the full record." The FAQ "What is X used for?" carries the same caveat. The "Adult" capital is covered by the same guard.
4. **Breadcrumb leaf "first-line CLL/SLL : Oct 2"**: a space was left before the colon where an h1 `<span>` was removed. **152 breadcrumbs site-wide** carried it ("ZYME FDA decision : Aug 25, 2026", "CAPR AdComm : ..."). `leaf_name` now removes whitespace before punctuation, and `test_breadcrumb_is_own_page.py` fails on it. It found 152 before the fix, 0 after, 1 planted on LLY-2026-10-02, then 0.

## 4. State

Local guards: **131 pass, 0 fail** (`_guards_0915.log`, 10:27 Pacific), after a full chain run. The live verification follows in the next note.

## 5. Open, not done

- Jaypirca's alternate names RXC-005 and LY3527727 come from an unsourced alias list. They are harmless but unverified; drop them or source them.
- `/drug/jaypirca` lists only the approvals pdufa.bio tracks (Dec 3, 2025 and Oct 2, 2026). The 2023 accelerated approvals are not rows. The caveat now says so.
- Drugs@FDA still shows the Dec 3, 2025 supplement (SUPPL-5) as 12/02/2025 against the FDA notice's Dec 3. This is pre-existing and was not touched; a ruling is needed on which date to carry.
