# Audit, 2026-09-09: the Vercel token, currency, and the channels
**Live build `2026-09-09T03:14:29Z` commit `c78438989`. API `as_of` 2026-09-09. Bing and Google consoles read live this morning; Bing publishes through Sept 7.**
*Facts and build mechanics only. Not investment advice.*

> Bash is still down (mount failure, third identical attempt). Verified through Chrome, `web_fetch`, and file grep.

---

# 1. THE TOKEN DOES NOT WORK, AND IT IS NOT YOUR FAULT

**CI run #155 (2026-09-09, job succeeded) carries this annotation, verbatim:**

> `VERCEL_TOKEN does not authenticate (Error: User not found.). The IDs are fine; re-create the token at vercel.com/account/tokens and update the secret.`

The secret is set (the step no longer logs "VERCEL_TOKEN secret not set"), and the org and project IDs resolve. The failure is at `vercel whoami`, before any project or scope lookup. **The token itself is not authenticating.**

## This is a known Vercel-side issue, not a setup mistake

Vercel's own community carries a report dated **August 24, 2026** that matches ours exactly:

> *"I'm unable to authenticate using any personal access token from my account, even though browser-based login works completely normally... Reproduced with three separate tokens at three different scopes (account-scoped, project-scoped, and team-scoped) all fail identically and immediately: `vercel whoami --token=<token>` → `Error: User not found.` Also fails the same way when used in GitHub Actions CI."*

A second thread reports the same 404 "User not found" / invalidToken on every API call. Both describe tokens that appear valid on the Tokens page and fail on first use. **Re-creating the token is unlikely to help**; the poster tried three at three scopes.

## What the builder did right

The `whoami` probe added after run 34321787738 is why we have a clean answer instead of a guess. It separates "the token is bad" from "the scope or project is bad" and writes which one into the log. Without it, this would have looked like an ID problem and we would have spent time on the IDs, which are correct.

## Recommendation: park it, and here is why that is the right call rather than a shrug

The purge was **already unproven** as a remedy. Vercel's own docs state each deployment carries its own cache key and that promoting a deployment does not affect the previous deployment's cache, which is the opposite of the stale bodies we saw on 09-07 and 09-08. So we are currently blocked, by a third-party bug, on a fix that may not fix anything.

**Do this instead, in order:**

1. **Nothing, for now.** The step logs a warning and skips. It costs nothing and it is honest.
2. **Next time the verifier or an audit catches a stale body**, purge by hand from the dashboard (project → **CDN** → **Caches** → **Purge**, enter `*`), then immediately re-fetch. That is the experiment that tells us whether purging is even the right instrument. No token required.
3. **If the manual purge clears it**, the automation becomes worth chasing, and at that point the ask is a Vercel support ticket citing the community threads, not another token.
4. **If it does not clear it**, the diagnosis is promotion timing on the production alias and we should stop discussing purges entirely.

I would not spend more of your time on the token until step 2 has an answer.

---

# 2. CURRENCY: CLEAN

| Gate | Result |
|---|---|
| API `as_of` | 2026-09-09, 456 rows |
| Past-goal day-precision PDUFAs undecided | **0** |
| Past Guided readouts without outcome | **0** |
| Conferences past their end date not marked Ended | **0** (ERS resolved correctly; my 09-08b/c error is closed) |
| Next decisions | **TLX Sept 11 (2 days)**, RARE Sept 19, MRK Sept 21, INCY Sept 26 |

TLX is 2 days out. Given that the watcher's MIMRYLO catch is the clearest citation win we have on record, that is the next event where speed converts.

---

# 3. THE CHANNELS

## Bing search: up on every measure, and the keyword base is widening fast

| | Sept 6 read | **Sept 7 read** |
|---|---:|---:|
| Clicks (3 mo) | 317 | **331** |
| Impressions | 10.7K | **11.1K** |
| CTR | 2.97% | **2.98%** |
| **Keywords ranked** | (414 on Aug 31) | **563** |

Sept 7: **426 impressions, 14 clicks, 3.29%**, a clean recovery from the weekend (239 and 278).

Movers: `pdufa date` 6 → 7 clicks, CTR 1.97% → **2.27%**. `fda pdufa` 0 → 2 clicks at 8.00%. `pdufa calendar` holds **28.57% at position 2.64**.

## Bing AI: breadth finally moved

| | Sept 6 | **Sept 7** |
|---|---:|---:|
| Citations (3 mo) | 3.7K | **3.8K** |
| Avg cited pages | 15 | 15 |
| **Grounding queries** | 19 (flat two weeks) | **20** |

Daily citations recovered to **160** on Sept 7 from the weekend's 79 and 87, so the "decline" I flagged on Sept 8 was the weekend, and I was right to say watch before drawing anything.

**Biggest mover by far: `fda calendar 2026`, 201 → 291 citations, share 28.15% → 30.83%.** That is the query the Saturday calendar explainer was written for, and it is the one moving.

**The new grounding query is `tavapadon fda approval date`: 4 citations, 100% citation share.** Two things about it. It is a query shape we have not seen before, "fda approval date" rather than "pdufa date", and we own it outright. That suggests the entity pages are picking up a second query family, and it is worth checking whether our drug pages answer "approval date" phrasing as well as they answer "pdufa date".

`camizestrant pdufa date` holds 82 citations at 32.03%. `zanidatamab pdufa date` still 100%.

## Google: flat for the fifth read

53 clicks, 3.2K impressions, 1.7% CTR, position 19, 162 queries. Generative AI report unchanged at **58 impressions across 15 pages**. Entity queries convert; head terms do not (`pdufa dates` 0 clicks on 64 impressions, `pdufa date` 0 on 51).

---

# 4. THE TWO SNIPPET ITEMS, AND WHAT IS AND IS NOT MEASURABLE YET

**Camizestrant: not yet judgeable.** Its description was fixed on Sept 8 at about 20:20 PT. Bing's data runs through Sept 7. The 29 impressions at 0 clicks in this read **predate the fix**. First honest read is around Sept 11 to 12. I will not credit or fault it before then.

**`/ticker/PFE`: still wrong, and still costing.** Live right now:

> title: `Pfizer Inc. (PFE) FDA Catalysts: BRAFTOVI (encorafenib) in co`
> description: `Roivant/Priovant (PFE) FDA catalysts. Next: Readout Oct 2026 for Palbociclib. 1 FDA decision on record.`
> body: `Pfizer Inc. · no upcoming catalyst on file · 10 past FDA decisions`

`pfizer pfe pdufa dates fda approval decisions 2026 2027`: **82 impressions, 0 clicks, position 3.23**, unchanged. The build has not moved since 03:14Z, so this is expected rather than a regression; it is simply still the top open item.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | `/ticker/PFE` description from the same majority-vote owner as the title; then the other 33 changed hubs | description names Pfizer, "10 FDA decisions", no phantom upcoming catalyst |
| **2** | Ticker-hub titles break on a word boundary | `/ticker/PFE` title does not end "in co" |
| **3** | The 48 pending-drug pages state their PDUFA date in the description | `/drug/aficamten` description contains "November 14, 2026"; count of pending-with-date pages on the generic string = 0 |
| **4** | `/conferences` description carries the run-up finding | contains "1,425" and the no-reliable-run-up clause |
| 5 | Check drug pages answer "approval date" phrasing, not only "pdufa date" | `/drug/tavapadon` and peers contain an "FDA approval date" phrasing in body or FAQ |
| 6 | UNCY case study per 09-06f, linked from `/why-no-approval-probability` | acceptance list in 09-06f §5 |
| **David** | Nothing on the token. Manual dashboard purge next time a stale body is caught. | a purge either clears it or does not; that answer decides the automation |

---

# BOTTOM LINE

**The token is set and does not authenticate.** Run #155 says so in one line, because the builder added a `whoami` probe that isolates the token from the IDs. Vercel's own community has two reports of exactly this since August 24, including one user who tried three tokens at three scopes with identical failures while browser login worked. Re-creating it is unlikely to help. **I recommend parking it**, because the purge it would enable is still unproven against Vercel's own documented cache-key behaviour, and the dashboard purge tests that for free the next time we catch a stale body.

**Currency is clean on every gate**, including the ERS conference I wrongly called stale twice. TLX decides in two days.

**The channels moved in the right direction for the first time in two weeks.** Bing clicks 331, impressions 11.1K, and the keyword base widened to 563. AI citations 3.8K with the daily rate recovering to 160 after the weekend, and **grounding queries broke 19 for the first time since late August**, at 20. `fda calendar 2026` gained 90 citations and 2.7 points of share, which is the query the calendar explainer was written for. A new query family appeared, `tavapadon fda approval date`, and we hold 100% of it.

**Google remains flat for a fifth read**, and the two snippet items that would move it are one build away: camizestrant's fix is real but too recent to measure, and `/ticker/PFE` still tells a Pfizer searcher it is a Roivant page.

---
*Consoles read 2026-09-09; Bing data through Sept 7 and revises recent days upward. CI annotation read from run 34374057382. Vercel community threads dated 2026-08-24. Not investment advice.*
