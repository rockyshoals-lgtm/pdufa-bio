# Biotech Catalyst Audit — 2026-07-19

**Informational / educational only. Not investment advice.** Options flow, dark pool, and analyst
data describe *positioning*, never the outcome of a binary event. Verify every date against company
IR before acting. Data pulled from Unusual Whales (options/dark pool, as of the 2026-07-17 session),
EDGAR/ClinicalTrials.gov (dates), and web sources (regulatory status).

---

## The catalyst calendar (next ~5 weeks are stacked)

| Ticker | Company | Catalyst | Date | Class | Mkt cap | Price |
|---|---|---|---|---|---|---|
| **OTLK** | Outlook Therapeutics | ONS-5010/LYTENAVA (wet AMD) PDUFA | **Jul 29, 2026** | Class 1 | $168M micro | $1.42 |
| **CAPR** | Capricor | deramiocel (DMD cardiomyopathy) **AdCom** | **Jul 29, 2026** | — | $1.13B small | $19.10 |
| **REPL** | Replimune | RP1 (melanoma) AdCom → PDUFA | AdCom late Jul / **PDUFA Aug 2** | Class 1 | $859M small | $9.96 |
| **CAPR** | Capricor | deramiocel PDUFA | **Aug 22, 2026** | Class 2 | — | — |
| **SLS** | SELLAS | REGAL Ph3 GPS (AML) topline — **event-driven** | **imminent** (78 of 80 events @ 5/11) | — | $2.45B mid | $13.30 |
| SLS | SELLAS | SLS009 (tambiciclib) Ph2 AML | 2026 | — | — | — |

Three binaries land in a **nine-day window (Jul 29 – Aug 2)**: OTLK PDUFA, CAPR AdCom, REPL AdCom/PDUFA.
SLS is a wildcard that can print any day (event-driven). This is a genuinely busy catalyst cluster.

---

## Per-name scorecard (ranked by setup clarity)

### 1. OTLK — the one with real, public de-risking
- **Catalyst:** PDUFA Jul 29 for ONS-5010/LYTENAVA in wet AMD. Class 1 (60-day review).
- **The tell that matters:** In **May 2026 Outlook WON its FDA Formal Dispute Resolution appeal** — the
  FDA concluded *"substantial evidence of effectiveness has been established."* The remaining review is
  about **labeling**, not whether the drug works. That is the closest thing in this whole set to a
  *public, pre-outcome signal that the catalyst is likely favorable* — and it is fundamental, not flow.
- **Options:** wildly call-skewed — call vol 3,265 vs put 264 (**~12:1**), call OI 70,914 vs put 10,197
  (**7:1**). UOA **BULLISH**, `CALL_WALL` flag. Net premium is thin, though — it is a $1.42 stock, so a
  lot of that call skew is cheap lottery buying, not big institutional premium.
- **Honest risk:** micro-cap, dilution-prone, and "labeling" disputes can still delay. But the appeal win
  is the rare case where the *base rate shifted publicly before the date.*

### 2. SLS — the most institutionally positioned; David's watch name
- **Catalyst:** REGAL Phase 3 (galinpepimut-S, AML) is **event-driven** — topline triggers on the **80th
  death event**. As of May 11 it was at **78**. This is the "readout soon after the 80th event" you flagged.
  It can print with little warning. SLS009 Ph2 AML is a second shot.
- **Options:** BULLISH lean — call vol 76,294 vs put 14,178 (**~5.4:1**), call OI 664,519 vs put 308,673,
  **net call premium +$1.13M**, bullish premium $14.4M vs bearish $12.6M. UOA NORMAL/**BULLISH**.
- **Dark pool:** heavy institutional block volume — repeated 10k–42k-share prints, hundreds of thousands
  of dollars each, millions in aggregate around $13. Real institutional hands are active here.
- **Honest risk:** REGAL is a hard AML overall-survival endpoint; event-driven means the date is a moving
  target and the readout is a true binary. Bullish options ≠ a good result. High beta (1.70) = violent both ways.

### 3. CAPR — smart money is buying *protection* into the AdCom
- **Catalyst:** **AdCom Jul 29**, PDUFA **Aug 22** for deramiocel (DMD cardiomyopathy). Class 2.
- **Options:** the dominant flow is **downside puts** — a $12-strike Aug **SweepsFollowedByFloor on 7/16
  worth $1.62M, ask-side** (aggressive put *buying*), plus a $15 put `LowHistoricVolumeFloor` (~$485K). UOA
  **MIXED**, `EXTREME_VOI` flag. Net put premium negative.
- **Read:** this is almost certainly **AdCom hedging, not a bearish thesis** — AdComs are high-variance
  coin-flips and rational holders buy protection into them. Do not read the puts as "insiders know it fails."
  But do respect that the market is pricing real two-sided risk here.

### 4. REPL — burned once, hedged again
- **Catalyst:** AdCom late July, **PDUFA Aug 2** for RP1 in melanoma. Class 1 (expedited from an earlier
  Apr-10 date). Already took a **CRL in 2025**, so the scar tissue is real.
- **Options:** near-term **put-dominant** — put vol 7,452 vs call 3,597 (**C/P ~0.33–0.48**), put premium
  $2.59M vs call $582K. UOA **MIXED**, `EXTREME_VOI`. Offsetting it: some **longer-dated call/LEAP
  accumulation** (Jan-2027 $10 calls, sweeps, ask-side) — a split tape: hedge the panel, own the upside later.
- **Read:** near-term protection dominates into the AdCom; the 3-year RP1 survival data (47.8% alive at
  3y, mOS 32.9 mo) is the bull case the LEAP buyers are playing. Two-sided, protection-first.

---

## KLRS retrospective — *was the good readout foreshadowed?*

**Short answer: not in the options or dark pool — because neither existed. The only pre-readout tells were
fundamental.**

What the audit found for KLRS *before* its +35% intraday move on 7/17:
- **`has_options: false`.** A $104M microcap with **no listed options at all** — so there was zero options
  flow, zero UOA signal, nothing to read. The entire "unusual options" lens is blind on a name like this.
- **No pre-readout dark pool.** The only dark-pool prints were **after** the data dropped (7/17 afternoon).
  No institutional block accumulation was visible in the days before.
- **No insider buying** on file.

What *did* exist pre-readout, and would have flagged it as higher-quality than a random microcap:
1. **Strong, quality analyst coverage:** 6 analysts, all Buy, price targets **$14–$25 vs a $4.24 price**
   (Raymond James *Strong Buy* $23, Morgan Stanley Overweight $14, Citizens $25, Wedbush $17). Bulge-bracket
   and top-analyst coverage on a $100M micro is itself a signal.
2. **The data was CONFIRMATORY, not a coin-flip.** The 7/17 drop was an **expansion** of Phase 1a data
   (n=17) that was **already positive** back in December 2025 (n=13) — same 9.2-letter BCVA gain, same
   durability. Our Smart Money overlay caught exactly this: `CONFIRMATORY_TRIAL` flag, fallen-angel ratio
   **2.88x**. A company re-reporting more of already-good early data is structurally lower-risk than a first,
   unseen readout.
3. Smart Money score **31 (LOW)** overall — but the two components that fired were the right ones: analyst
   **17/20** and structural **14/20**. The institutional and insider components were 0 (no 13F/insider tell).

**The lesson:** for a no-options microcap, the options/dark-pool audit will *always* come up empty — that is
not a failure of the data, it is the nature of the name. The pre-readout edge on KLRS-type events lives in
**(a) analyst quality, (b) whether the data is confirmatory vs first-look, and (c) fallen-angel structure** —
the Smart Money lens, not the UOA lens. Wiring analyst-quality + confirmatory-data flags onto the biotech
watchlist would have surfaced KLRS as "higher-conviction microcap readout" ahead of time; the options tape
never could.

---

## The meta-finding: what actually foreshadows a "good" readout

Across all five names, the honest hierarchy of pre-event signal strength:

1. **Public regulatory de-risking > everything.** OTLK's *won appeal* ("efficacy established") is the only
   signal here that genuinely moved the base rate before the date. Confirmatory data (KLRS) is second.
   These are fundamental facts, not tape.
2. **Institutional dark-pool accumulation + bullish call premium** (SLS) shows *conviction and presence*,
   and is worth weighting — but it is positioning, not prophecy.
3. **Put-heavy flow into an AdCom** (CAPR, REPL) is usually **hedging, not a bearish forecast.** Reading it
   as "smart money knows it fails" is the classic misread — AdCom protection is what rational longs *do*.
4. **No pre-readout signal reliably predicts a binary's direction.** Every overlay we run tells you *size,
   positioning, or base-rate shift* — never the coin. That is the same truth the whole system is built on.

**Actionable takeaways for the watchlist:**
- Add **AdCom dates** as a first-class field — CAPR (7/29) and REPL (late-July) both have panels *before*
  their PDUFAs, and the AdCom is the real variance event. The calendar currently tracks PDUFA/PCD, not AdCom.
- Add an **analyst-quality + confirmatory-data flag** for **no-options microcaps** (the KLRS gap), since UOA
  is structurally blind there.
- Flag **"FDA appeal won / efficacy established"** as a distinct, high-value regulatory state (OTLK) — it is
  the single most predictive pre-event fact in this batch.

---

## Also on the live calendar (context, lighter data)
From `readout_calendar.csv` (72 names), the near-term biotechs with a smart-money lean already enriched:
EWTX (Phase 2, BULLISH options + EDGAR/CTgov disagree), CLYM (Phase 1, BULLISH, dark-pool ACCUM),
OCGN (Phase 1, 7/31, BULLISH), ARGX (Phase 2, 8/31, BULLISH, ACCUM), MANE (Phase 2, 8/31, BULLISH, ACCUM).
SLS sits at 12/30 on the CT.gov date but the **event-driven REGAL readout can lead that by months** — treat
SLS as "imminent, watch daily," not "December."

*Disclaimer repeated: informational and educational only, not investment advice. Binary catalysts can gap
hard in either direction regardless of any signal here. Position sizing and every decision are yours.*
