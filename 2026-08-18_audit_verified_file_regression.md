# Audit — 2026-08-18
**All 08-16 items re-checked live · one regression found · calendar root cause finally isolated**
*Facts and historical statistics only — not investment advice.*

---

# 1. THE 08-16 ITEMS — WHAT ACTUALLY LANDED

| # | 08-16 finding | Status | Evidence |
|---|---|---|---|
| 2.2 | `/api/v1/conferences` stale (14 / 0 presenters) | ✅ **FIXED** | now **41 conferences, 14 in 2027**, with `presenters` + `presenter_note` fields |
| 3 | BOLT → SITC 2026 (wrong edition, "40th" = 2025) | ✅ **GATED OUT** | **0 hits** |
| 3 | IMNM → ENA 2026 (past tense, 2025 filing) | ✅ **GATED OUT** | **0 hits** |
| 3 | True rows must survive the gate | ✅ | MOLN, EVAX, MGNX, NVCR, OLMA all retained |
| — | Patent cliff intact after the `.gitignore` incident | ✅ | all pages 200; **BALCOLTRA correctly on `/2027`** (its LOE year) and **correctly absent from `/cancer`** |
| 2.1 | Calendar page vs API | ❌ **still open — 4th audit** | page **73 / 57**, API **68 / 48** |

**The presenter gate is genuinely careful work.** BOLT's snippet reads *"…data in the third quarter of **2026**. o In November at the **40th** Annual Meeting…"* — a naive whole-snippet year match would have passed it on the readout clause's year. The implementation clips at the sentence boundary and judges only the conference clause. That's the right level of paranoia for this data.

---

# 2. 🔴 REGRESSION — all 9 hand-verified presenters have vanished

On 08-16 the page carried my 9 hand-verified rows **plus** the history-file rows. Today the API carries **5 presenter entries across 3 conferences**, and every one is from the history file:

```
ASTRO  -> NVCR
ESMO   -> EVAX, MGNX, MOLN
SABCS  -> OLMA
```

**Gone:** IONS/ESC · BNTX/WCLC · IBIO/EASD · SANA/EASD · IPSC/EASD · ENTX/ASBMR · XNCR/ESMO · ZLAB/ESMO · CRVO/CTAD.

Note ESMO kept its three history rows but lost XNCR and ZLAB — so this isn't the edition gate rejecting them.

## Root cause — the file never deploys

```bash
git ls-files --error-unmatch catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv
#   error: did not match any file(s) known to git

git check-ignore -v catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv
#   .gitignore:35: *.csv
```

`.gitignore` line 35 is a blanket `*.csv`, with an explicit re-include block below it:

```
!readout_miner.csv
!catalysts_out/conference_presentations_history.csv     ← this is why the history rows DO publish
!catalysts_out/catalysts_public.csv
!conf_study/conference_runup_PUBLISHED.csv
```

**The verified file isn't in that list.** It exists on the workstation, is untracked, and CI never sees it. `build_conferences.py` does `if not os.path.exists(path): continue` — so it **silently publishes fewer presenters instead of failing.**

**Fix — one line plus a force-add:**
```
!catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv
```
```bash
git add -f catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv
```

## This is my fault as much as anyone's
I created that CSV, in a directory covered by a blanket `*.csv` rule, and handed it over without checking it would survive a deploy. The builder wired it correctly; the file just wasn't there.

## And it's the third instance of the same root cause
- `73faf74f` — "the verification steps read a **workstation-only file**"
- `6bf22f9b` — "`.gitignore`'s `*.csv` **swallowed the cliff dataset**"
- today — `*.csv` swallowed the verified presenter file

**The generalisable defect:** the build **degrades silently** when a data file is absent. A missing input produces fewer rows, not an error. That is the same shape as everything else we've been chasing — a check that can only ever pass.

**Recommended guard:** assert a minimum expected row count per data source at build time. If the verified presenter file yields 0 rows, fail the build rather than publishing a thinner page. Cheap, mechanical, and it would have caught all three.

---

# 3. 🟠 CALENDAR — root cause isolated after four audits

Page and API still disagree, and the gap is stable at 5:

| | Page | API |
|---|---:|---:|
| Total (Jun–Dec 2026) | **73** | **68** |
| Ahead / Upcoming | 57 | 48 |
| Decided | 15 | 19 |
| Lapsed / Awaiting | 1 | 1 |

**What I established this time — and one hypothesis I had to discard.**

I assumed the page was including month/quarter-precision dates the API drops. The page even says *"where the source gives only a month or a quarter we say so instead of inventing a day."* **That hypothesis is wrong.** I parsed the API's own source file:

```
pdufa_site_src/api/v1/dataset.mjs → 449 records, 79 PDUFA, 68 in the window
dp values in the window: {"day": 68}      ← zero month/quarter precision
```

`/api/v1/pdufa` and `/api/v1/events` independently agree at **68**, with no duplicate ticker+date clusters. **The API is faithful to its source.**

So the page's 73 comes from a **different file** — the page builds from the `data.js` SLATE, the API serves `dataset.mjs`, and nothing reconciles the two.

**That is why four rounds of "reconcile the calendar rows" haven't closed it.** The fix isn't a better count; it's either one source of truth, or an explicit build-time assertion that the two files agree for the same window.

Minor, same family: the page stamps *"as of August 17"* while today is the 18th.

---

# 4. STILL OPEN

| Item | Status |
|---|---|
| `/compare/` | 404 — last unbuilt content surface |
| Per-event PDUFA URLs `/pdufa/{T}-{date}` | 404 |
| **`/terms` · `/privacy` · `/refund-policy` · `/contact`** | **all 404** — blocks email capture *and* payments |
| Email capture form | not built (unblocked since 08-16 — both false claims are gone ✅) |

`/pricing` is clean: free-trial 0, "not collecting emails" 0.

---

# 5. ORDER

| # | Item | Why | Effort |
|---|---|---|---|
| 1 | `.gitignore` re-include + `git add -f` the verified CSV | **9 true presenters are missing from a live page** | minutes |
| 2 | Build guard: minimum row count per data source | would have caught all three `*.csv` incidents | hours |
| 3 | Calendar: one source of truth, or assert `data.js` == `dataset.mjs` for the window | 4th audit; the number is in FAQ schema | hours |
| 4 | Legal pages (terms, privacy, refund, contact) | blocks email **and** payments | 1 day |
| 5 | Email capture form | audience compounding | 1 day |
| 6 | `/compare/` pilot | last content surface | 2 days |
| 7 | Per-event PDUFA URLs | AI cites specific URLs | 1 day |

---

# 6. BOTTOM LINE

Everything I raised on 08-16 was actioned, and the conference presenter gate is better engineering than I asked for — it correctly rejects BOLT's "40th Annual Meeting" by clipping the snippet at the sentence boundary rather than year-matching the whole thing.

But the fix shipped alongside a regression neither of us saw: **the hand-verified presenter file is gitignored and untracked, so nine true, sourced presenter rows are silently missing from a live page.** The build doesn't fail when a data file is absent — it just publishes less. That's now happened three times with `*.csv`, and a minimum-row-count assertion would end it permanently.

On the calendar, I finally have the root cause rather than another restatement of the gap: **the page and the API are built from two different files.** My month-precision theory was wrong — the API's source genuinely holds 68 day-precision records. No amount of row reconciliation will fix a two-source problem.

And the legal pages remain the single thing standing between you and both an email list and a paywall.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
