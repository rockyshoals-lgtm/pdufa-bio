# CPHI, 2026-07-21 — what the day taught us

**No position taken.** CPHI ran 0.91 → 3.30 (3.6x) and halted. We didn't buy because the plan
was to buy a pullback and the pullback never came. No money lost, no money made. The value of
the day is entirely in what broke.

---

## 1. The pullback thesis, measured — and it doesn't hold

Ran the executable rule (limit sitting R% back off a leg high) across **8,295 entries, 602
names, 7 sessions** of tape.

| retrace | n | med MFE | med MAE | +8 b4 −8 | +5 b4 −5 | med close | green@close |
|---|---|---|---|---|---|---|---|
| 40% | 3,217 | +1.2% | −2.3% | 43% | 36% | −0.5% | 45% |
| 50% | 2,730 | +1.4% | −2.1% | 46% | 41% | −0.2% | 48% |
| 60% | 1,445 | +1.9% | −2.1% | 50% | 51% | +0.1% | 51% |
| 70% | 903 | +2.2% | −1.7% | 50% | **62%** | +0.6% | 54% |

Coin flip. Median upside ≈ median downside at every depth. Only the 70% retrace tilts
positive — and a **+2.2% median win cannot survive a 2–4% spread** on a sub-$1 microcap, which
is why the LIMIT-ONLY guardrail exists.

Compare: the GO hard-push runs 30.8% hit +8 before −8 against a 10% base — a 3x lift. That is
an edge. The pullback buy is not.

**Known gap in this study:** every entry is conditional on a give-back *happening*. It never
measures the branch where the name runs away and the limit never fills. Today is that branch.
"46% hit rate" means 46% of fills, not 46% of intents. → task #71.

### The CPHI-only version was garbage and nearly got reported
First pass used FMP 1-min bars, which returned **2 sessions, not 7** — essentially yesterday
and today, with today being the +100% day in progress. It reported **median MFE +28.3%, 4-of-5
hit rate.** Circular: measuring the outcome we hoped to repeat, on the day it happened. The
7-session tape version said +2.1%. **Off by an order of magnitude.**

---

## 2. Three independent failures on the biggest move of the day

Live board, mid-run:

```
CPHI   price 2.46   move +170.3%   surge 46   vel_now +202.5%/hr
go:             null        <- no chart data at all
repeat_pumper:  null        <- CHRONIC in the registry, badge never reached the board
GO LOG:         0 fires     <- entire session, not just CPHI
```

- **No chart data.** Surge score 46 = mid-table, never made the `CHART_COVER=60` cut. `hard_push`
  had nothing to check, so GO could not fire. Same class as AEHR/DNTH: *not gated out — never
  looked at.* → task #65
- **No 🔁 badge.** CPHI is `CHRONIC`, `n_pumps: 6` in `serial_pumpers.json`. Registry correct,
  wiring broken. The one indicator that says "this name does this repeatedly" was silent while
  it did it again. → task #66
- **Zero GO fires all session** — the day after widening coverage 24→60 and opening the 10:30
  gate specifically to catch more.

We did not miss this for lack of discipline. The board never surfaced it.

---

## 3. FMP is not usable on fast thin names

| time | FMP | broker | lag |
|---|---|---|---|
| ~10:59 | 1.84 (dayHigh 1.84) | 2.37 | **−29%** |
| ~11:10 | 2.4599 (dayHigh 2.495) | 3.30 | **−25.5%** |

FMP's *day high* sat below the live price — the vendor never saw the last leg. Also behind on
volume (24.39M vs 26.31M).

**This corrects my earlier claim.** I said Monday that FMP quotes are 1–2s old and talked David
out of a $199/mo Polygon subscription. That was true for normal names. It is false for thin,
fast, low-priced names — which are exactly the ones that pay. → task #73

---

## 4. Halt detection: v1 was broken, and David supplied the fix

v1 flagged **6,625 "halts" across 292 names in 7 sessions** — impossible. It checked *price
frozen* only, so it caught:

```
MTEM   0.107 → 0.000   frozen 134 min, 230 min     dead ticker
CALA   0.030 → 0.000   frozen 134 min              dead ticker
CCG   15.530 → 0.444   "MFE +3399%"                reverse split, unadjusted
FSTB 408.000 → 20.010  "MFE +1938%"                reverse split
IKNA  17.160 → 1.460                               reverse split
```

Discarded without reporting a conclusion.

**The discriminator, from David watching his own tape:** on a real halt the **volume freezes
too** — CPHI stuck at 26,306,453 @ $3.30. Price frozen alone = stale quote or dead ticker.
Price + volume frozen = halt. The `v` field is already in every tape row; v1 just didn't use it.

This also makes it a **live** signal, not just a study — the board can flag `⏸ HALTED` in real
time, and flag the RESUME, which is the moment that matters (auction print, worst spread of the
day). → tasks #67, #68

**Side effect worth acting on:** those split ghosts poison *any* study over the tape. Deferred
on 2026-07-20 (IKNA); no longer theoretical. → task #69

---

## Scoreboard for the day

**Correction:** an earlier draft of this doc read "Trades 0, P&L $0." That was written while a
POET position was open — I wrote it during the CPHI conversation and never asked. Wrong.

| | |
|---|---|
| Trades | 2 |
| P&L | **+$649.28** (2/2 winners) |
| Bugs found | 5 (chart coverage, 🔁 wiring, GO silence, halt detector, split ghosts) |
| Prior claims corrected | 2 (FMP latency, CPHI pullback edge) |
| Studies discarded as invalid | 2 (2-session pullback, halt v1) |

```
POET   910 sh   7.91 → 8.18   09:46:00–11:04:34 ET   held 78m34s   +3.41%   $+245.70
VIVK  1187 sh   6.23 → 6.57   11:05:09–11:13:40 ET   held  8m31s   +5.46%   $+403.58
```

### The rotation thesis got a same-day controlled test
VIVK made **64% more dollars in 8½ minutes than POET made in 78.** Same account, same morning.
This is the strongest evidence yet for "the more rotations the more money we make" — and it
argues for pushing on the late-GO gate opening rather than reverting it.

Tick replay:
- **POET** — high while held 8.25 (+4.30%), took +3.41%, left 0.89pp. Entry +1.2% off the open,
  worst drawdown −0.51%. Ran to 8.38 after the exit (+2.44% past it) but the rotation out-earned
  that.
- **VIVK** — entry was **+31.2% from the open** (a chase, and it worked). High while held 6.8552
  (+10.04%), took +5.46%, left 4.58pp. Dipped −3.21% at 11:08 before running: a third of the
  8-minute hold was red.

**Open question for the post-mortem:** POET left 0.89pp on the table, VIVK left 4.58pp. The
tight exit was on the slow name and the loose exit on the fast one. Worth checking across the
whole journal whether exits are being set off elapsed time rather than the name's velocity.

*Informational and educational only. Not investment advice.*
