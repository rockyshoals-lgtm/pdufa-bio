# SESSION HANDOFF — 2026-07-15 (evening) — phantom PDUFAs closed + 3 bugs found

Continues `_SESSION_HANDOFF_2026-07-15.md`. That doc's §1 ("THE BIG OPEN ITEM") is **DONE**.
Everything below is verified state. **Deployed and verified live on www.pdufa.bio.**

---

## 0. TL;DR

| Area | State |
|---|---|
| 4 phantom PDUFAs (BIIB/MRK/PFE/IONS) | **Closed, deployed, verified live.** `check_pdufa_decided.py` now reports clean. |
| `build_decision_page.py` | **NEW.** First real generator for `/fda-decision/` pages. Builds from the price cache. |
| CELC decision page | **Was publishing VERA's data live. Fixed.** (see §2.1) |
| IONS duplicate archive row | **False row removed + 301.** It was jamming the sweep. (see §2.2) |
| Calendar counter | Was **59** vs 57 actual. Now **55**, counted not assumed. |
| CORT breadcrumb | Said "ARQT 2026-06-29". Fixed. |
| **~430 decision pages have wrong run-up DATES** | **FOUND, NOT FIXED.** Prices correct, dates wrong. (see §3.1) |

Forward slate: **80 → 76**. Archive 2026: **129 → 131** rows. Calendar scheduled: **59 → 55**.

---

## 1. WHAT WAS VERIFIED (primary sources, not headlines)

All four confirmed the approval is the *same application* as the pending PDUFA — the trap the
old handoff warned about. It nearly bit on BIIB.

- **BIIB 2026-08-24 → Approved 2026-07-13.** Biogen IR 2026-05-08: the sBLA for LEQEMBI IQLIK
  **"as a starting dose"** had its PDUFA extended to **Aug 24, 2026**, and that release
  *explicitly distinguishes* it from the subcutaneous **maintenance** regimen approved
  2025-08-26. The 07-13 release approves that same starting-dose sBLA. **This is why the
  headline alone was not enough: "LEQEMBI IQLIK approved" was already true in Aug 2025.**
- **MRK + PFE 2026-08-17 → Approved 2026-07-10.** Merck **Q1-2026 Form 8-K**: *"In April, FDA
  granted priority review for KEYTRUDA and KEYTRUDA QLEX, each with Padcev, for
  cisplatin-eligible patients with MIBC, based on the Phase 3 KEYNOTE-B15 trial. FDA set PDUFA
  date of Aug. 17, 2026."* That 8-K lists **no second MIBC action date**, so there was no other
  pending MIBC application to confuse it with. Both sponsors announced 07-10.
- **IONS 2026-06-30 → Approved 2026-06-24.** Ionis **Form 8-K Ex-99.1**: TRYNGOLZA (olezarsen)
  approved for sHTG on the Phase 3 **CORE/CORE2** studies. Slate row was "Olezarsen - (CORE)".

**Not touched (verified still live):** OTLK 2026-07-29, MRK 09-21 + 10-10, PFE 09-30,
IONS 09-22 + 10-26. A pre-write simulation asserted exactly-4-swept and zero collateral before
anything was written; the real `--dry-run` then matched it exactly.

---

## 2. BUGS FOUND AND FIXED

### 2.1 `fix_early_approvals.make_page()` shipped VERA's data onto CELC's page — LIVE
`/fda-decision/CELC-2026-07-14` was live saying CELC's gedatolisib got
**"accelerated approval for IgA nephropathy (Jul 7 2026)"**, over **VERA's** chart, VERA's
$49.1/$31.26 high/low, and "FDA decision 7/7/26". Wrong indication, wrong date, wrong prices.

Cause — the template swaps are literal and incomplete:
```python
t = t.replace('2026-07-07', d)          # ISO only; the chart labels say "7/7/26"
t = t.replace('Jul 7, 2026', pretty)    # comma form only; the banner says "(Jul 7 2026)"
t = t.replace('Trutakna (atacicept)', label)   # swaps the brand, KEEPS the trailing prose
```
**A template that carries data is not a template.** `make_page()` should be considered unsafe —
use `build_decision_page.py` instead. CELC rebuilt from Celcuity's own price history.
`fix_early_approvals.py` was left in place but **do not call `make_page()` again.**

### 2.2 IONS was archived TWICE, and the duplicate jammed the sweep
The archive held both `IONS-2026-06-24` (correct) and `IONS-2026-06-30`. The 06-30 page stated
*"FDA decision date 2026-06-30"* while its own headline said the approval was *"(Jun 24 2026)"* —
it contradicted itself, and no decision happened on 06-30.

That false row is **exactly why the phantom survived every build**. `already_decided()` stands
down when a drug matches >1 archive entry (the KEYTRUDA platform-drug guard). Both IONS rows
contain `olezarsen`, so the slate row matched two entries → "ambiguous" → no sweep. sim for
`"olezarsen core"` vs `"tryngolza olezarsen core"` is **0.74**, under the 0.80 `strong` bar, so
the tie-break couldn't save it either. **Self-inflicted ambiguity.**

Fix: removed the false row, retired the page, **301 → IONS-2026-06-24** (in `vercel.json`).

> **Archive-label rule (learned the hard way):** existing archive labels are truncated to ~30
> chars ("KEYTRUDA (pembrolizumab) and K"). For a platform drug that scores ~0.54 against the
> slate string and **will not sweep**. New rows for platform drugs must keep the label long
> enough to score >0.80. The MRK/PFE rows carry the full
> `KEYTRUDA (pembrolizumab) plus Padcev (enfortumab vedotin-ejfv) - (KEYNOTE-B15/EV-304)`.

### 2.3 The calendar counter was decremented, not counted
`fix_calendar_page.py` ended with `('%d scheduled FDA decisions' % (old_n - 2))` — it assumed
the delta. Page said **59** while carrying **57** scheduled rows. *That 2-row drift was the
"IONS still counted scheduled" symptom.* The script's own docstring had already learned this for
`numberOfItems`; the counter never got the same treatment. Now **everything is recounted from
the DOM**: counter = ListItems = numberOfItems = `/pdufa/` rows = **55**.

---

## 3. FOUND, NOT FIXED — READ BEFORE THE NEXT SESSION

### 3.1 ~430 of 442 decision pages have WRONG run-up DATES (prices are fine)
The published **values are all correct and all exist in the price cache — on a different day.**

| page says | actually |
|---|---|
| VERA $49.1 on 1/21/26 | **1/13/26** |
| VERA $31.26 on 6/4/26 | **6/2/26** |
| ABBV $164.99 on 11/25/24 | **11/15/24** |
| AAPG $47.9 on 8/26/25 | **8/22/25** |
| ABBV $216.66 on 3/10/25 | 3/10/25 ✓ |

So this is **not** a bad data source — it's a date-attribution bug: the right price with the
wrong day attached, off by a *variable* number of trading days (looks like an index
misalignment between the price slice and the date slice; it vanishes at some indices, which is
why 12 pages are clean).

**Reassuring part:** the prices and the `120-day run-up %` — the numbers a reader would act on —
are correct. VERA's published **-13.6%** is exactly what the *correct* T-120 (1/12, $46.46 →
$40.13) produces, proving the % was computed from the right window while the labels were not.
**The bug is confined to the displayed high/low dates and the T-120 start label.**

Not fixed because regenerating 430 live pages is a sampling-frame-wide change and the standing
rule is *never change the sampling frame and the published number in the same step*. It is very
doable though: the existing pages' drug/indication/company/outcome fields are correct, so a
regeneration pass can preserve those facts and fix only the labels via `build_decision_page.py`.
**Recommend doing it as its own reviewed step.**

### 3.2 The same duplicate-archive bug is still hiding 4 stale rows
`already_decided()` still won't sweep these past-dated rows, for the same >1-match reason:

```
GSK  2026-06-18  Tebipenem HBr   (archive has GSK-2026-06-17 AND GSK-2026-06-18)
SPRO 2026-06-18  Tebipenem HBr   (archive has SPRO-2026-06-17 AND SPRO-2026-06-18)
VRDN 2026-06-30  Veligrotug      (archive has VRDN-06-26, 06-29 AND 06-30)
AZN  2026-06-30  Truqap
```
`check_pdufa_decided.py` does **not** flag them (their PRs are outside its 40-PR window), so
they are invisible to the daily job. **9 duplicate archive pairs total** across ACHV, ARQT, GSK,
SPRO, UNCY, VRDN (IONS now resolved). Each pair is one curated-style label + one prose-style
label from a PR headline; **one of the two dates in each pair is wrong.** Each needs
primary-source verification to decide which — do not bulk-delete.

### 3.3 Still open from the previous handoff
`/runup-by-year` PNGs have no generator · `calendar/index.html` has no generator (still
surgical patches) · P2-6 FMP redistribution terms unread · P0-5 ODIN retrain on capped
`prior_crl_count`.

---

## 4. NEW / CHANGED FILES

| File | Purpose |
|---|---|
| `build_decision_page.py` | **NEW.** Real generator for `/fda-decision/` pages. `--verify TICK-DATE` regenerates an existing page and diffs the numbers. Use this, never `make_page()`. |
| `decision_pages_2026_07_15.json` | Verified facts for the 4 pages built/rebuilt today. |
| `fix_phantoms_2026_07_15.py` | Archive rows + CORT breadcrumb + sitemap + 301 + retire false page. Idempotent, `--dry-run`. |
| `fix_calendar_page_2026_07_15.py` | Calendar patch. **Recounts everything from the DOM.** Rebuilds heatmap week bars. Idempotent, `--dry-run`. |
| `_retired_IONS-2026-06-30/` | The retired false page, kept for reference. |

Backups written alongside each edited file as `*.bak_2026-07-15`.

### Heatmap geometry (reverse-engineered — no generator exists)
Each week is a **stacked bar, one `<rect>` per cap tier**, bottom-up:
`Small #46d17f, Mid #5b8fd0, Large #33547e, Unlisted #28405f`
```
y = 189 - (pos + k) * 15      height = k * 15 - 1.2      label y = 189 - n*15 - 3
```
Verified against **every** existing block. Yesterday's script could only delete
single-decision weeks; Aug 17 (9→6) and Aug 24 (6→5) had to be rebuilt at the new counts.

---

## 5. DEPLOY / VERIFY

Deployed via Vercel CLI → `✓ Ready`, `Aliased https://www.pdufa.bio`. Verified live:
`/fda-decision/BIIB-2026-07-13` ✓ · `/fda-decision/CELC-2026-07-14` now shows gedatolisib /
breast cancer / 7-14 with CELC's own prices ✓ · `/fda-decision/IONS-2026-06-30` **301s** to
`IONS-2026-06-24` ✓ · `/calendar` counter/ListItems/numberOfItems/rows all **55** ✓ ·
`check_pdufa_decided.py` → *"No forward PDUFA appears to have been decided already."* ✓

> Note: deploy ran from the Linux sandbox (`npm i --prefix /tmp/vc vercel`), not
> `deploy_site.bat`. Same project/token, same result. The `.bat` remains the normal path.

---

## 6. STANDING RULES (unchanged — from CLAUDE.md)
ODIN v19-PRUNE only (v14 KNOWN LEAKED) · real data only, verify every date against primary
sources · never publish a number you can't defend · nothing with `redistribute=False` reaches
the site · no scores/probabilities/sizing on the site · never change the sampling frame and the
published number in the same step · **data integrity outranks presentation** · educational only.
