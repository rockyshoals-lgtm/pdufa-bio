# Morning-Runner strategy slices

_Informational/educational only - not investment advice._

Sample: 1880 gap-up events. Baseline (buy 9:30 open, exit noon): mean +0.46%, median -2.71%, win 38.9%.

## 1) Confirmation entry (only trade if still green at 10:00)
Confirmed subset: 722/1880 (38%).

**Open-entry exits, confirmed subset only:**
| exit | mean % | median % | win | n |
|---|---|---|---|---|
| exit 10:00 | +11.45 | +6.73 | 100.0% | 722 |
| exit noon | +13.47 | +5.78 | 70.2% | 722 |
| +10% target else noon | +7.77 | +10.0 | 88.9% | 722 |
| hold to close | +530.76 | +5.61 | 65.5% | 722 |

**Enter AT 10:00 on confirmation, fixed-time exits:**
| exit | mean % | median % | win | n |
|---|---|---|---|---|
| -> 10:30 | -0.38 | -0.76 | 44.0% | 722 |
| -> 11:00 | -0.2 | -1.11 | 41.7% | 722 |
| -> noon | +1.04 | -1.37 | 43.4% | 722 |

## 2) Subset slicing - does any bucket pay? (exit at 10:00, fast scalp)
**By opening gap:**
| gap | mean % | median % | win | n |
|---|---|---|---|---|
| 20-40% | -0.46 | -1.52 | 41.8% | 1216 |
| 40-70% | -2.27 | -5.08 | 32.3% | 337 |
| 70-120% | -2.38 | -5.25 | 30.0% | 190 |
| 120%+ | -0.16 | -5.51 | 35.0% | 137 |

**By first-hour volume x ADV:**
| vol xADV | mean % | median % | win | n |
|---|---|---|---|---|
| <1x | -2.49 | -2.9 | 33.8% | 450 |
| 1-3x | -1.57 | -2.51 | 36.9% | 388 |
| 3-5x | +0.48 | +0.84 | 52.2% | 178 |
| 5-10x | -0.49 | -2.49 | 36.7% | 180 |
| 10x+ | -0.1 | -2.89 | 39.2% | 684 |

## 3) Short side (short the 9:30 open, cover intraday = negated long, GROSS)
| cover at | mean % | median % | win | n |
|---|---|---|---|---|
| cover 10:00 | +0.96 | +2.5 | 59.9% | 1880 |
| cover noon | -0.46 | +2.71 | 60.1% | 1880 |
| cover at close | -263.7 | +3.76 | 58.6% | 1880 |

**Heavy caveat:** shorting micro-cap runners needs locatable borrow (often unavailable, or 100-1000%+ annual fees), faces violent squeezes and LULD halts, and these GROSS figures ignore borrow cost, spread, and slippage. Realizable short returns are far lower with severe tail risk. Not a recommendation.

**Overall caveats:** survivorship (currently-listed only); before costs; open/stop/confirmation fills optimistic on thin micro-caps.
