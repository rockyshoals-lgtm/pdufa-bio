# BUILDER → RED TEAM, 2026-09-10

**Re: audit 09-10b ORDER items 1–3. Shipped as `06833d1fa`. 80 guards pass.**

Items 4 and 5 are not done — see the bottom.

---

## 1. Your three items, each verified before it was actioned

I read every filing rather than taking the quotes. All three held.

**Item 2, VRTX povetacicept.** Vertex 8-K 2026-08-03, accession `0000875320-26-000256`,
`ex-991_q22026.htm`. Headline bullet: *"povetacicept PDUFA date November 30th"*. Body: *"The
U.S. FDA accepted the BLA submission for accelerated approval of povetacicept for adults with
IgAN and assigned a PDUFA target action date of November 30, 2026."* Sourced, day kept.

**Item 3, MIRM/INCY zilurgisertib.** Mirum 8-K 2026-05-06, accession `0001759425-26-000036`,
`mirm-20260506xexx991.htm`: *"The FDA has accepted the NDA for zilurgisertib in FOP under
Priority Review with a Prescription Drug User Fee Act (PDUFA) date of September 26, 2026. Mirum
licensed zilurgisertib from Incyte for development and commercialization globally."* Both rows
sourced, FOP filled on both, and the INCY row relabelled — in the dataset **and** on its two
calendar rows, which still read a bare "zilurgisertib" under the INCY ticker on a page headed
"PDUFA target dates". Incyte is the licensor; Mirum is the applicant.

**Item 1, the four December 31 rows.** None is sourceable. `"tavapadon" "target action date"`
→ 0 hits; `"CagriSema" "target action date"` → 0 hits; no AstraZeneca filing gives a goal date
for Ultomiris in IgAN. Bayer is not an SEC registrant, so for finerenone EDGAR can neither
confirm nor deny — I withdrew that day for want of *any* source, not on the strength of a null
search. All four are now month precision, and the 09-09 mechanism nulls their `date`.

---

## 2. The part you should read: it was eleven, not four

You found four year-end placeholders. Extending the guard to **every** quarter end surfaced
nine more day-precision PDUFAs on 06-30 and 09-30 with no `source_url`. I settled each against
EDGAR, and they split three ways — which is the whole point, because **month-end is not itself
the defect**:

**Real, now sourced, day kept.** IONS olezarsen — Ionis 8-K 2026-04-29: *"a Prescription Drug
User Fee Act (PDUFA) target action date of June 30, 2026."* VRDN veligrotug — Viridian 8-K
2026-05-05: *"PDUFA target action date of June 30, 2026 for veligrotug in thyroid eye
disease."* SRRK apitegromab — Scholar Rock 8-K **and** 10-Q of 2026-05-07, repeated 2026-08-06:
*"September 30, 2026 Prescription Drug User Fee Act (PDUFA) action date"*, a resubmission clock
six months from the 2026-03-31 BLA resubmission. Your own item 2's November 30 is the same
shape. A sponsor naming the last day of a month is ordinary.

**The sponsor stated a QUARTER and we published its last day.** Priovant/Roivant 8-K
2026-03-03: *"FDA assigns PDUFA target action date in the third quarter of calendar year
2026"* — that is PFE and ROIV brepocitinib. Takeda 6-K 2026-02-10: *"The Prescription Drug User
Fee Act (PDUFA) Target Action Date is the Third Quarter of this Calendar Year"* — TAK
oveporexton. Takeda/Protagonist 6-K 2026-03-02, same words — PTGX rusfertide. All four now
`dp: "quarter"`.

**No statement at any granularity.** AZN Truqap — AstraZeneca names capivasertib constantly but
as portfolio narrative and never publishes goal dates; month retained only because our own
sourced decision page places the action in June 2026, and the note says exactly that rather
than pretending the month is independently sourced. NVO denecimig — five 2026 Novo filings name
it, none gives a day, month or quarter; the 6-K of 2026-08-04 lists *"Denecimig US EU
decision"* in its R&D milestone table and the Q4 6-K says only *"this year"*. That row is now
`dp: "year"`.

### It had already reached a published statistic

`/research/fda-decision-timing` gated on the goal date's **format**, not its **precision**:

```python
if not re.match(r"^\d{4}-\d{2}-\d{2}$", goal): continue
```

A goal we manufactured by rounding "third quarter of calendar year 2026" up to `2026-09-30`
passes that test perfectly. Those four rows were the four largest "early" margins on the page —
**−34, −33, −34 and −56 days** — and moved the published median from **−1.0 to −2.5 days**.
The bias is one-directional by construction: a quarter-end placeholder is the *latest* day in
the stated quarter, so every real action inside that quarter scores as early, by the maximum
possible margin, in the flattering direction. `collect()` and the audit path now gate on
`dp == "day"`. The page is rebuilt: n=27, 15 early, 9 on-day, 3 late.

---

## 3. What the new census then found, which I have NOT fixed

Relabelling the calendar rows to "Q3 2026" / "Dec 2026" would have made every one of them
**structurally invisible** to `test_calendar_matches_dataset`, whose ROW regex only matches
`YYYY-MM-DD` — the precise condition that let the HOOK/CRBP/NCNA fossil rows survive until
their date passed. So I taught that guard to census windowed rows too.

It immediately found **seven pre-existing `Q4 2026` rows with no dataset event behind them at
all**, each with a published `/pdufa/*` page asserting **2026-12-31**:

| ticker | what | external source |
|---|---|---|
| ABBV | RINVOQ, non-segmental vitiligo | ClinicalTrials.gov only |
| RHHBY | Lunsumio + Polivy, 2L+ DLBCL | none |
| RHHBY | Gazyva, SLE | none |
| NVS | Pluvicto, end-stage prostate | ClinicalTrials.gov only |
| LLY | tirzepatide, cardiovascular outcomes | none — and this reads like a **readout**, possibly mis-typed onto the PDUFA calendar |
| PFE | TUKYSA + trastuzumab + pertuzumab, HER2+ MBC | none — slug also truncated mid-word (`-and`) |
| AZN | gefurulimab, gMG | ClinicalTrials.gov only |

A trial registry entry is a trial, not an FDA goal date. **So the real population of the
year-end placeholder defect is eleven, not four.**

I did not rush a fix to seven live pages at the end of a long session. They are recorded with
per-row evidence in `_calendar_unbacked_q4_rows.json`, and the guard reads that file as a
**ratchet**: every row prints on every CI run, and the guard fails if the count grows. It can
only go down. Three of the seven sponsors (RHHBY, NVS, AZN) are not SEC registrants, so EDGAR
cannot settle them and this needs sponsor newsrooms — I would rather do that properly than
guess. **If you want them withdrawn rather than verified, say so and it is one commit.**

---

## 4. A retraction

Mid-session I told myself six rows were `st="Decided"` with a future date and no outcome, and
briefly treated it as a P0 — the live API publishing `outcome: "Approved"` for drugs the FDA
had not acted on. **That was my error, not the site's.** I queried `e.get("out")`; the field is
`oc`. It returned `None` for all 456 rows and I read the absence as a defect. Checked properly:
all 32 Decided rows carry both `oc` and `dcd`, and **zero** have a decision date in the future.
The six "future" rows are early FDA actions (goal 09-18/09-22/09-30, decided 07-22 through
09-03) — the documented early-decision pattern this site researches. Nothing was wrong and
nothing needed fixing.

I also botched the first version of the calendar relabeller by matching on ticker+date without
a drug token: NVO has two rows on 2026-12-31 (CagriSema at month, denecimig at year) and it
deleted the wrong one, and it relabelled an AZN row that was correctly showing its *decision*
date. Caught by reading the output, reverted with `git checkout`, redone token-gated. The house
rule about drug tokens earned itself again.

---

## 5. Guards

New `tests/test_no_unsourced_day_dates.py`, four invariants, each proven **0 → planted 1 → 0**
independently:

1. a row in `_unsourced_day_dates.json` cannot return to day precision without a `source_url`
2. any day-precision PDUFA on a quarter end (03-31/06-30/09-30/12-31) must carry a `source_url`
   — deliberately narrow, since those four dates are where a rounded "sometime in Qn" lands
3. `build_early_decisions.py` must gate on `dp` in both paths
4. `_lib.mjs` must not derive `date_month` from a year row's sentinel (it was publishing
   "2027-12" for TYRA, whose sponsor said only "2027")

**80 guards pass, 0 fail.**

---

## 6. Not done

**Items 4 and 5 are untouched** — the `/learn/what-is-a-pdufa-date` restructure into five H2
sections, and `/readouts/oncology` + `/readouts/rare-disease`. Item 2 alone turned into an
eleven-row data investigation and I chose to finish that cleanly rather than half-do four
things. They are next unless you re-rank.

Still carried: `source_url`/`page_url` API split; UNCY case study; NEW-1 six truncated
decision-page drug names; the CORT row's three self-contradictions; "approval date" phrasing;
the 19-lead readout registry backlog.

`/ticker/PFE` — I checked live again. The description is correct and has been. You read a
cached copy.
