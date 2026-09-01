# 9 Realms — Immutable Rules

## ⏰ RULE 1 — TIMEZONE (David, 2026-08-18, after it burned us three separate times)

**This machine runs PACIFIC (PDT/PST). The market runs EASTERN. We are 3 hours BEHIND.**

Before analyzing ANY timestamp, state which zone it is in. Never assume. The specific traps,
each of which has already corrupted real analysis:

| source | zone | note |
|---|---|---|
| `Get-Date` / local clock / file mtimes | **PACIFIC** | 06:30 local = 09:30 ET bell |
| nest_egg `runners_*.jsonl` → `ts` field | **PACIFIC** | pre-2026-08-13 rows; +180 min to reach ET |
| nest_egg `runners_*.jsonl` → `ts_et` field | **EASTERN** | post-fix rows carry `"tz": "ET"` |
| `runner_board_*.jsonl` | **EASTERN** | proven on 89,415 rows |
| `board_timeline.jsonl` → `ts` | **PACIFIC** | `ts_et` where present is Eastern |
| `/api/nest` → `as_of` | **PACIFIC** | looked "frozen at 09:40" mid-afternoon 8/18 — it was ticking, in PT (#128) |
| Polygon epoch ms | **UTC** | convert with −4h for ET (EDT); −5h in winter (EST) |
| FMP timestamps | **EASTERN** | calendar dates and publishedDate |
| true_open recording window | **09:30–09:35 ET** = 06:30–06:35 local |

History: the Pacific/Eastern mixup corrupted FOUR studies before being proven on 217,210 rows
(2026-08-13), then cost hours of misdiagnosis again on 2026-08-18 (the `as_of` incident).
When a timing result looks impossible — a board "3 hours late," an entry "before the open" —
check the timezone FIRST, before any other hypothesis.

## Standing rules (from the trading sessions)

- **Never give investment advice.** Information only; David makes every trading decision.
- **Never execute trades or move money.** Ever.
- Complete honesty, no hallucinations; retract loudly and immediately when wrong.
- Test on ALL sessions before claiming a finding; one session is an anecdote (this error
  occurred four times — churn-ranking, +5%-exit, OR-width, close-ramp — same shape each time).
- **NEST EGG board: $300M+ (SMALL+) only.** No nano/micro, no exceptions for armed names.
  ETFs and leveraged wrappers never enter tracked samples (triple-net: netf flag → LEV_ETF →
  FMP isEtf/isFund cached in `_DATA/etf_flags.json`).
- Interpreter pin: `C:\Python314\python.exe`. Long scripts run via .bat + `Start-Process`
  (tool calls time out ~25s; never run pulls inline).
- All strategy content is educational/informational, not investment advice.
