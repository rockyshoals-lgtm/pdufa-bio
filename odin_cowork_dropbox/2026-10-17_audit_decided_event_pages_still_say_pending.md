# Audit: both approvals of the week are live and correctly dated. Eight decided event pages still describe a pending decision, and Bing's "this week" answer is frozen at Oct 13
**2026-10-17, measured 17:45 to 18:05 Eastern = 21:45 to 22:05 UTC (Saturday).** *Per RULE 1 every time carries its zone.*
**Live build `c975628da`, generated 2026-10-17T15:11:18Z (11:11 Eastern).**
- API: 475 rows; `as_of` 2026-10-17; `data_built_at` matches the build.
- `/build-info.json`: `held_leads` [], next decision **GSK bepirovirsen 2026-10-26**, `next_days` 9.

*Facts and build mechanics only. Not investment advice.*

**Client note:** Claude in Chrome was not reachable this session. The site was read through the app's built-in browser, which is not signed in to Bing Webmaster or Search Console. **There are no console numbers in this audit.** SERPs were read directly.

---

# 1. THE BUILDER'S 10-16 AND 10-17 WORK: VERIFIED

| Item | Live |
|---|---|
| Enspryng TED | `pdufa_rhhby_2026-10-15` Decided, `decision_date` 2026-10-15, `fda_action_date` null, `decision_date_unsourced` true. `/fda-decision/RHHBY-2026-10-15` 200, "Enspryng Approval Announced Oct 15, 2026 for Thyroid Eye Disease". MOGAD row 2027-01-10 is still upcoming and linked |
| RYZUMVI (phentolamine 0.75%) presbyopia | IRD and VTRS rows Decided, `decision_date` 2026-10-16, unsourced FDA day. `/fda-decision/IRD-2026-10-16` and `/VTRS-2026-10-16` 200, h1 "RYZUMVI (phentolamine) FDA approval for presbyopia: Oct 16, 2026" |
| FDA record for both | openFDA `last_updated` **2026-10-16**: **no** new submission on BLA 761149 or NDA 217064. Both pages correctly say the FDA day is not on record. Both are correctly kept out of the timing statistic |
| Timing statistic | **32: 21 / 10 / 1** on `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing`, `/llms.txt` |
| Quarantine | The first held lead since the 10-15 fix (IRD/VTRS, 2 runs). The rest of the site kept deploying. **Item 4 of the 10-16 order is closed** |
| September backfill | `/fda-decision/LLY-2026-09-23` Onswik and `/TEVA-2026-09-25` Degevma both 200 and dated by their letters |
| `/calendar` | Title "FDA Calendar 2026: 110 PDUFA Dates, Updated Daily". October sentence in date order: "Bepirovirsen (GSK, Oct 26) and INO-3107 (INO, Oct 30)". November: "13 FDA goal dates in November 2026; 1 already decided… 12 of them are still ahead, including…" |
| Weekly page | "Decided this week (4)": IRD Oct 16, VTRS Oct 16, RHHBY Oct 15, IBRX Oct 14 |

The builder's correction to my count (November has 12 pending rows, not 11; I missed REGN cemdisiran at month precision) is right. **Retracted.**

The 10-16 calendar integrity guard found **11 rows on `/calendar` that contradicted the data**. This was a whole class I never audited, because I read the API, not the calendar grid:
- brepocitinib linked to the Tukysa page;
- JUVMO and Kerendia T1D still pending months after approval;
- Miplyffa rows standing on a patent listing.

The builder's own self-reported incident (stopping David's 9realms MCP server by process pattern) has the right rule attached: stop by PID, never by pattern. **David: restart the 9realms MCP from the Claude app if it has not come back.**

---

# 2. CURRENCY

| Check | Live |
|---|---|
| Day-dated PDUFAs on or past goal and not Decided/Withdrawn | **0** |
| Non-day rows carrying a date / month mismatch | 0 / 0 |
| Conferences mislabelled against the Eastern date | 0. ASN, ECTRIMS and IDWeek (Oct 21) and ESMO (Oct 23) are all "Scheduled" with `end_date` |
| Upcoming PDUFAs | 37; 31 day-dated, **31 sourced** |
| Readouts | bare "Window passed" 2; dated "no topline as of" 79; Reported 14; sponsor release 6 |
| Freshness strip | "Data as of Oct 17, 2026 11:11 AM ET" |

## 2a. P1: decided event pages keep their pre-decision description and a "Scheduled" Event

I swept all 73 `/pdufa/{TICKER}-{drug}` event pages in the sitemap. **30 are decided.** Of those, **8 still carry a meta description written as if the decision were pending**:

| Page | Title (correct) | Description (stale) |
|---|---|---|
| `/pdufa/IRD-phentolamine-ophthalmic` | **also stale:** "IRD / VTRS PDUFA date: Phentolamine ophthalmic, Oct 17, 2026" | "IRD's FDA PDUFA target is Oct 17, 2026 for Phentolamine ophthalmic…" |
| `/pdufa/RHHBY-enspryng` | "RHHBY FDA decision: Enspryng, Approval announced October 15, 2026" | "…sBLA for thyroid eye disease: FDA goal date October 15, 2026 under Priority Review…" |
| `/pdufa/IBRX-anktiva` | "…Approved October 14, 2026" | "IBRX's FDA PDUFA target is Jan 6, 2027 for ANKTIVA…" |
| `/pdufa/INCY-zilurgisertib` | "…Atebrioz…, Approval announced Septem…" | pending form |
| `/pdufa/MIRM-zilurgisertib` | same | pending form |
| `/pdufa/BAYRY-sevabertinib` | "…Approved September 9, 2026" | pending form |
| `/pdufa/NUVB-ibtrozi` | "…Approved September 16, 2026" | pending form |
| `/pdufa/SRRK-apitegromab` | "…Approved September 11, 2026" | pending form |

**What the reader sees on these pages.** The body is right: the IRD page reads "the FDA decided this application on October 16, 2026". But Bing and Google print the description. Anktiva's description says the target is **January 2027**, about an application approved on October 14.

**Event schema.** All 8, and by inspection the decided event pages generally, keep `"eventStatus": "https://schema.org/EventScheduled"`. The withdrawn-page rule (10-09) already drops the Event schema. A decided goal date is equally over.

**Root cause, two places:**
1. The description is set when the event page is generated and is never rewritten on decision. Tecentriq's was rewritten by hand.
2. The IRD title escaped the "FDA decision:" title rewrite, probably because the partner page carries two tickers ("IRD / VTRS").

**Fix:** on decision, the same step that retitles the event page also rewrites its description from the decision. Use "{Brand} ({INN}) was approved by the FDA on {FDA day}" when the FDA day is sourced, and "Approval of {Brand} was announced on {date}; goal date {goal}" when it is not. Drop the Event schema at the same time.

**Guard:** no decided event page carries "PDUFA target is", "goal date … under", "due to decide" or "PDUFA date:" in its title or description, and none carries `EventScheduled`. Prove it 0 → planted 1 → 0.

## 2b. Brand names in decision titles

The two RYZUMVI pages use the brand in the h1 and 12 times in the body, but not in the place search reads first:

| Page | Title | Description |
|---|---|---|
| `/fda-decision/IRD-2026-10-16` | "**Phentolamine ophthalmic solution** Approval Announced Oct 16, 2026" | 106 characters |
| `/fda-decision/VTRS-2026-10-16` | "**MR-141** Approval Announced Oct 16, 2026 for Presbyopia" | 106 characters |

People search "ryzumvi". `MR-141` is Viatris's development code, and nobody searches it after approval.

**Fix:** titles become "RYZUMVI (phentolamine) Approval Announced Oct 16, 2026 for Presbyopia | {T} FDA Decision". Write a 140-to-155-character description that names RYZUMVI, presbyopia, VEGA-2/VEGA-3 and Viatris's U.S. rights. The rule: a decision title uses the approved brand when the source names one, and never a development code once a brand exists.

---

# 3. SEO, BING AND AI CITATIONS (SERPs read live)

## 3a. Bing's "fda approval decisions this week" answer has not refreshed since 10-13

Tonight's answer box is word-for-word the one I recorded on 10-13. It cites pdufa.bio eight times, for "Tecentriq — decision expected October 9", "Ifinatamab deruxtecan — decision expected October 10" (withdrawn Sep 25), "Enspryng — decision expected October 15" (approved), and "IRD / Viatris — decision expected October 17" (approved). The only pdufa.bio URL behind it is `/fda-decisions-today`.

**So Bing's grounding copy of `/fda-decisions-today` is at least nine days old,** and the 10-13 hub-first ordering has not moved it yet. Bing caps SubmitUrlBatch at 100/day, shared across the three CI runs.

**What the builder can do:**
- Confirm in the CI log that `/fda-decisions-today` and `/fda-approval-decisions-this-week` were accepted (HTTP 200) in each run since 10-13, not just queued.
- Add `<meta name="robots" content="max-snippet:-1">` if absent, and an explicit `dateModified` in the page's WebPage JSON-LD that changes daily. Both pages' content really does change every day, so the stamp is honest.

**What David can do:** in Bing Webmaster, run URL Inspection → Request indexing on `/fda-decisions-today` and `/fda-approval-decisions-this-week`. This is the third audit asking. It is the one lever that does not depend on the queue.

## 3b. The week's two approvals

- **RYZUMVI.** Bing's answer for "ryzumvi presbyopia fda approval" names October 16 correctly, and **pdufa.bio is in its source set** (`/fda-decision/VTRS-2026-10-16`), alongside Viatris, Healio, Ophthalmology Times and PR Newswire. That is the decision page earning a citation within a day.
- **Enspryng.** "enspryng thyroid eye disease fda approval": we are **not** in the source set. Yahoo, MedPage Today, Healio, PharmExec and Seeking Alpha are.
  - Bing's answer says "October 15–16, 2026". That is a real ambiguity we can resolve when the BLA 761149 letter posts.
  - **First page to carry the FDA's own day wins that sentence.** `sync_fda_action_dates.py` must run on the next openFDA update. The page should then lead with "approved by the FDA on {day}" and request indexing the same night.

---

# 4. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Decided event pages: rewrite description (and title where needed) on decision; drop the Event schema.** Fix the 8 pages above; guard as in 2a | Sweep of the 30 decided event pages: 0 pending-tense titles or descriptions, 0 `EventScheduled`; guard 0 → 1 → 0 |
| **2** | **Brand-first decision titles** (2b); RYZUMVI pages retitled; descriptions 140 to 155 characters | Both titles start "RYZUMVI"; rule documented in the title builder |
| **3** | **Enspryng and RYZUMVI FDA days:** when Drugs@FDA posts the BLA 761149 and NDA 217064 supplements, swap in the letter dates, compute margins (Enspryng goal Oct 15; RYZUMVI goal Oct 17), and admit both to the statistic if both dates are sourced | Statistic updates on all four surfaces in the same build; pages lead with the FDA day |
| **4** | **`/fda-decisions-today` freshness to Bing:** confirm daily acceptance in CI logs; daily `dateModified` in JSON-LD on the two daily hubs | CI log lines quoted in the next note |
| **5** | Bepirovirsen (GSK/IONS, goal Oct 26, a Monday) runbook. Watch Friday Oct 23 as well: GSK's last two approvals landed before goal | Decision page the day of the record |
| 6 | Carried for David: Bing Request indexing (`/fda-decisions-today`, the weekly page, the Enspryng and RYZUMVI pages); restart the 9realms MCP; CI `SEC_USER_AGENT` empty; `goal_date_held`; Jaypirca SUPPL-5; RXC-005; SMTP; Drive exclusion; AZN/NVO sources; the 20 nct-mismatch readouts; the 131 registry rows | |

---

# 5. BOTTOM LINE

**The data is right.** Three approvals in three days, each published within hours from the sponsor's record. Each correctly refuses to state an FDA day the FDA has not yet posted. The quarantine held one row and let everything else deploy, which is the design working for the first time.

**The words around the data lag the data.** Eight decided event pages still introduce themselves to search engines as pending. Two decision titles hide the brand people search for. Bing's AI answer for "this week" is still built from a nine-day-old copy of our today page. None of this is a wrong fact in the body of any page. All of it is what a searcher or an AI reads first.

---
*Site read from the app's built-in browser with `cache: 'reload'`, 2026-10-17 21:45 to 22:05 UTC, against build `c975628da`. Sweep covered all 73 `/pdufa/` event pages in the sitemap. openFDA `drugsfda` read live for BLA 761149 and NDA 217064 (last_updated 2026-10-16). Bing SERPs for "fda approval decisions this week", "ryzumvi presbyopia fda approval", "enspryng thyroid eye disease fda approval" and "phentolamine presbyopia fda approval october 2026" read live. Bing Webmaster and Search Console not read (client not signed in). Not investment advice.*
