# Friday Tape — 10 July 2026
## Full July catalyst breakdown · deep dive: CELC & CAPR

*Internal research. Historical/observational statistics and model output only. Not investment advice. No entry, exit, or sizing guidance.*

---

## 0. The one thing that matters

**Every July catalyst name sold off on Friday, and in every one of them the call flow was hitting the bid.**

| Ticker | Catalyst | Open → Close | Net premium | Call vol | % of call vol **sold into the bid** |
|---|---|---|---|---|---|
| **CELC** | PDUFA Jul 17 | 113.50 → **107.58** (−5.2%) | −$16.8K | 615 | **57%** |
| **CAPR** | AdComm Jul 29 | 22.58 → **21.51** (−4.7%) | **−$345.6K** | 1,046 | **87%** |
| **OTLK** | PDUFA Jul 29 | 1.67 → **1.57** (−6.0%) | −$140.8K | 4,119 | **64%** |
| **MNKD** | PDUFA Jul 26 | 4.12 → **4.09** (−0.7%) | **−$1.29M** | 6,029 | **84%** |
| **OCGN** | Readout Jul 31 | 1.48 → 1.47 (−0.7%) | +$4.0K | 542 | 46% |

Four of five names printed **net-bearish premium**. MNKD's was the most lopsided: **$1.50M bearish vs $0.20M bullish**.

**Read it carefully, not dramatically.** "Bid-side" is a heuristic for seller-initiated. It cannot distinguish *opening short* (someone selling upside into the catalyst) from *closing long* (someone ringing the register on a position that already ran). **Volume is not open interest.** Monday's OI print is the confirmation — if OI *rises* on these strikes, it was new call supply; if OI *falls*, it was longs taking profit. Do not conclude before that.

---

## 1. CELC — Celcuity · PDUFA Friday 17 July (5 sessions out)

**$107.58 · $5.25B (mid) · 48.77M shares out · gedatolisib**
Verified: NDA accepted Jan 2026, **Priority Review**, PDUFA **17 Jul 2026**, HR+/HER2−, **PIK3CA wild-type** advanced breast cancer. Ph3 VIKTORIA-1 met PFS; published in JCO.

### ODIN v19-PRUNE (honest champion — see §5)
**p = 0.5461 · T3 · MONITOR** · TA risk bucket VERY_HIGH

Dominant drags are both *sponsor-naivety* terms — Celcuity has **zero prior approvals**:
- `crl_rate_x_naive` −0.431
- `consistency_x_naive` −0.361
- `priority_review_bin` **+0.308** (the main support)
- `ta_very_high` +0.288

### The headline: the options market is asleep

> **IV rank = 9.9.** Five sessions from a first-ever binary approval, CELC's implied vol sits at the **9.9th percentile of its own 1-year range**.

- Implied 30-day move: **15.3%**
- Total options premium traded Friday: **~$400K** (calls $192K + puts $206K) on a **$5.2B** company
- **UOA v1.1 = 1/10 · QUIET · MIXED** → −6% score adj, 0.85× sizing note

Event-expiry (Jul-17) IV: ATM 110C **93.7%**, with a steep put skew (85P **137%**, 80P 149%, 75P 166%). The downside is bid; the event itself is not.

### Positioning is a barbell, and the puts are bigger
| Strike | OI | |
|---|---|---|
| **100 PUT** | **2,472** | ← largest single position in the expiry |
| **120 CALL** | **2,065** | |
| 130 CALL | 1,161 | |
| 100 CALL | 1,143 | |
| 95 PUT | 871 | |
| 110 PUT | 820 | |

**Max pain (Jul-17) = $100**, below spot. Friday's biggest single-strike print was the **85 PUT: 552 contracts, 489 of them bid-side** — the only strike in the name with vol/OI ≈ 1.0.

### Dark pool
One print that matters: **34,200 sh @ $107.85 = $3.69M**, 10:33 ET, flagged `qualified_contingent_trade` — i.e. **options-linked / hedged**, not a clean directional block. Everything else was 1,000–1,400 share retail-scale. There is **no institutional block accumulation** visible on the tape.

### Borrow
Fee **0.47%**, *falling* (was 0.56–0.62% earlier in the month). Availability tightened 1,000,000 → 150–200K shares on Friday — but **with no fee spike**, which is takedown, not desperation. **No squeeze fuel.**

### Price context — this is not a stock coasting into a PDUFA
- **2 June: −25.6% in one day** ($122.96 → $91.42), on 3,728 puts and $3.07M put premium
- Recovered to $115.72 (7 Jul), then faded again
- **−24.7% below the 22 May high of $142.82**
- **runup_30d = −19.7%** · runup_7d = +2.8%

---

## 2. CAPR — Capricor · AdComm Wed 29 July

**$21.51 · $1.25B (small) · deramiocel (CAP-1002)**

### ⚠️ Calendar correction
**The July event is the panel, not the decision.** FDA Cellular/Tissue & Gene Therapies AdComm **29 Jul 2026**; the **PDUFA action date is 22 August 2026**. It is a **Class 2 resubmission** — the prior CRL was lifted and review resumed March 2026. Our `catalysts_public.csv` files CAPR as a July catalyst without that distinction.

### ⚠️ Expiry trap
**The Aug-21 expiry does not span the Aug-22 PDUFA.** Aug-21 captures the AdComm only. **Sep-18 is the first expiry that contains the decision.** Anyone expressing PDUFA exposure through Aug-21 owns the panel, not the approval.

Friday's largest flow went to **Sep-18** — the correct expiry.

### ODIN v19-PRUNE (honest)
**p = 0.5116 · T3 · MONITOR** · TA VERY_HIGH
- `had_adcom_flag` **+0.439** (biggest positive)
- `resub_class_2` −0.281
- `crl_rate_x_naive` −0.431 (Capricor also has zero prior approvals)

### The market IS pricing this one — unlike CELC
- **IV rank 46.4** · **implied 30-day move 53.4%** · 30-day vol **282%**
- Compare CELC: IV rank 9.9, implied 15.3%

### Friday flow: call supply, not accumulation
**87% of all call volume (908 of 1,046) hit the bid.** Net premium **−$345,645** (bearish $524K vs bullish $178K).

Single biggest print: **550 × Sep-18 $35 CALL — 539 on the bid — $274,830.** That is someone *supplying* upside 63% OTM into the decision expiry. Unconfirmed as new positioning until Monday's OI.

### Open interest
| Contract | OI | Note |
|---|---|---|
| Sep-18 **35C** | 2,632 | Friday's 550-lot went here |
| Aug-21 **50C** | 2,004 | 134% OTM lottery strike |
| Aug-21 **25C** | 1,623 | **6 consecutive days of OI increases** |
| Sep-18 **16P** | 1,591 | |
| Sep-18 **12P** | 1,250 | |

Max pain **$25** (Jul-17 and Aug-21), above spot.

### Dark pool — algo signature
Repeated **4,988-share** blocks, four times (13:38, 13:41, 14:07, 19:59 UTC) at $21.53–21.91, plus 6,000 @ $21.59 into the close. Identical odd size repeating = **iceberg/VWAP slicing**, not conviction blocks. ~$107–130K each. Modest.

### Borrow
Fee **0.40%**, dead flat all month. Availability 1.1M → 400–500K. **Cheap, easy, no squeeze.**

### Price context
- **−13% on 26 June — the day the AdComm was announced** ($30.40 → $26.44), on 8,462 calls and 8,619 puts
- **−29.2% over 11 sessions** since
- Heavy bearish premium on 6 Jul ($5.16M) and 8 Jul (9,524 puts, $2.14M)
- **runup_30d ≈ −26.7%**

---

## 3. The CELC ⇄ CAPR contrast — the actual insight

Two binaries, same month, opposite vol regimes:

| | CELC | CAPR |
|---|---|---|
| Event | PDUFA in **5 sessions** | AdComm in 17d, PDUFA in 41d |
| **IV rank** | **9.9** | **46.4** |
| **Implied 30d move** | **15.3%** | **53.4%** |
| Friday premium | ~$400K | ~$726K |
| UOA | 1/10 QUIET | 0/10 QUIET |

The options market is treating **CELC's first-ever approval as a non-event** and **CAPR's panel as a coin flip**. Both cannot be right.

**Two honest readings of CELC's silence — they point opposite ways, and we should not pretend otherwise:**

1. **Cheap convexity.** IV rank 9.9 with a hard binary five days out is, mechanically, inexpensive optionality. (Caveat from our own 1,828-trade ORATS backtest: **mid-cap PDUFA options avg +1.8%, win 36.2% — "marginal"**. The edge lives in *micro/small*, not mid. CELC is mid.)
2. **QUIET is a bearish tell.** Our own UOA v1.1 backtest on 976 PDUFA events found **QUIET is a statistically significant negative signal — 65.0% approval vs 73.6%, p=0.016** — and QUIET×BULLISH is retail noise. Silence has historically not been golden.

I am not resolving that for you. Both are our own numbers; they disagree; that disagreement is the finding.

---

## 4. The rest of July (21 catalysts)

**Decisions**
- **MNKD** — PDUFA Jul 26, FUROSCIX ReadyFlow autoinjector (sNDA, device). *Most bearish tape of the month:* $1.50M bearish vs $0.20M bullish premium; 84% of calls sold into the bid. IV rank 48.6.
- **OTLK** — PDUFA Jul 29, bevacizumab-vikg (ONS-5010), wet AMD. $1.57, sub-$2. IV rank 47.0, implied 30d move **56.4%**. 64% of calls bid-side, net premium −$141K. Note: OTLK has a long CRL history in this program — a resubmission profile, not a first look.
- ~~**CORT** — Jul 11~~ **⚠️ FALSE. Relacorilant was APPROVED 25 March 2026.** See §5.

**Readouts** — EXEL (Jul 12), INCY (Jul 13 & 30), PFE (Jul 13), HCWB (16), DRTS (21), BNTX (23 & 31), LTRN (28), QNRX (30), JAZZ (31), BMY (31), IBRX (31), BIIB (31), OCGN (31).

The large-caps (PFE, BMY, JAZZ, BIIB, INCY, EXEL, BNTX) carry no catalyst-specific flow signature — single-asset readouts are immaterial to the equity. **OCGN** (OCU410ST, DME) is the one worth watching given the IIS/interim-inflation history on OCU410 — Friday was quiet (542 calls, IV rank 23.0).

---

## 5. Data-quality & model issues found (act on these)

**P0 — CORT is on the calendar again with a Jul 11 PDUFA. It was approved 25 March 2026.**
This is the *same* regression we fixed. The reconciliation guard that should stop the crawler re-adding decided events off their PDUFA date is not holding. If it's in `catalysts_public.csv`, it's plausibly live on the site.

**P0 — CLAUDE.md is stale and dangerous on ODIN.**
The memory file says *"ODIN v14 is the ONLY PDUFA scoring model. Never fall back."* The **deployed MCP flags v14 as KNOWN LEAKED** (`ODIN_v14_LEAKAGE_FINDING.txt`, 2026-04-17; HO AUC inflated ~368bp). Champion is **v19-PRUNE, honest test AUC 0.8934**. Anyone (or any agent) following CLAUDE.md scores on a leaked model. **Update the memory file.**

**P1 — `ppm_flag_bin` looks hard-set to 1.**
It contributed an **identical −0.5956** to both CELC and CAPR, with z = **10.9**. A feature that lands the same constant on every event isn't discriminating — it's a fixed negative offset dragging *all* ODIN probabilities down. Worth an hour in the scorer.

**P1 — `explosion_score` is not usable on these names.**
Its top features are `log_float_inv`, `days_to_cover`, `pct_float_short`. I passed zeros (we don't have SI wired), and the model returned a meaningless **0.8%**. Separately, the Apr-2026 red team already found **BIFROST's SI features are lookahead-biased** (one Apr-2026 snapshot applied retroactively to 2020–2026). **Do not use the explosion detector until SI is sourced point-in-time.** (This is backlog P6-1.)

**P2 — Calendar data**
- CAPR: July row is an **AdComm**; PDUFA is **Aug 22**. Needs both, distinctly typed.
- CELC: `indication` is **blank**. Should be *HR+/HER2−, PIK3CA wild-type advanced breast cancer*.

**P2 — Stale strings in MCP**
`uoa_score` still returns *"Score with ODIN v14 first"* / *"Gungnir v43 first"*.

---

*Sources: primary — Celcuity 8-K/424B5 (SEC EDGAR), Capricor 8-K 2026-06-26 (SEC EDGAR), FDA AdComm notice. Market data: Unusual Whales (dark pool, options chain, OI, borrow, OHLC/IV). Models: ODIN v19-PRUNE, UOA v1.1, BIFROST v5.4 — all internal.*
