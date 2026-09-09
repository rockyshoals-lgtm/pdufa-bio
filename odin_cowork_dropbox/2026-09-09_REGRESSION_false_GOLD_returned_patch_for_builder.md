# 2026-09-09 — REGRESSION: false GOLD dates are back in the feed. Patch below.

**Classification: CORRECTION + PATCH REQUEST.** From the trading-side research assistant.
Filed as a note, not a commit, per CLAUDE.md RULE 2 (pdufa.bio pipeline changes go to the
pdufa builder). **Please apply to `readout_gold_dates.py` on `main`.**

## What is wrong right now

Today's 12:26 chain run published **9 false GOLD rows** to `odin_cowork_dropbox/latest/`.
GOLD is the tier we tell people is safe to preload a trade against. These are vendor
placeholder dates that got promoted to GOLD because the BPC Conference column was non-empty:

```
ABBV   2026-09-15  BPC/conference:IASLC World Conference on Lung Cancer   (x2)
LLY    2026-10-01  BPC/conference:European Academy of Dermatology and V   (x2)
NKTR   2026-10-01  BPC/conference:European Academy of Dermatology and V   (x2)
CLDX   2026-12-31  BPC/conference:American Academy of Allergy, Asthma &
IMMP   2026-12-31  BPC/conference:European Alliance of Associations for
TLSA   2026-12-31  BPC/conference:ACTRIMS Forum
```

The last three claim **AAAAI, EULAR and ACTRIMS Forum meetings on New Year's Eve.** Those are
February / June / February congresses. The date is a vendor bucket, not an agenda.

Current census: 527 rows, GOLD 93, DAY 134, **no YEAR tier**, 34 placeholder-shaped days of
which 9 are GOLD.

## Why it regressed

This was found and fixed on 2026-09-07 (GOLD went 95 → 86, DAY 159 → 127, a YEAR tier added
for NYE rows, and the verifier was made to exit non-zero on any GOLD placeholder). That fix
was committed while I was also doing hypestock work. When the four hypestock commits were
moved off `main` to `hypestock-wip`, **this pdufa.bio fix went with them by mistake** — it was
never hypestock work. `readout_gold_dates.py` and `_verify_gold_dates.py` on `main` are both
back to their pre-09-07 state (all four markers absent: `SELF-AUDIT FIX`, `FALSE GOLD`,
`conf-bucketed`, `_nye`).

My error in filing it, not the builder's in moving it. Flagging the mechanism so it does not
happen a third time — the same class of loss took out the `window_precision` work on 08-24.

## The patch

In `readout_gold_dates.py`, in the BPC loop, replace the `if conf: / elif is_pdufa...` block
with the version below. Two behaviour changes: (a) a placeholder-shaped **conference** date is
SOFT, never GOLD; (b) bucketed rows write the honest granularity into `date` instead of a full
day we have ourselves flagged as fake — NYE means "2026" (YEAR), any other placeholder means
that month.

```python
        # SELF-AUDIT FIX (2026-09-07, re-filed 09-09). Two placeholder leaks found by
        # measuring our own file the same way we measure BPC's:
        #
        #  (a) FALSE GOLD — a conference row was promoted to GOLD/DAY purely because the
        #      Conference column was non-empty, even when the date was New Year's Eve.
        #      Three rows claimed AAAAI/EULAR/ACTRIMS congresses on 2026-12-31. Those are
        #      February/June meetings; the date was a vendor placeholder, not an agenda.
        #      GOLD is the tier we tell people to preload against — a false GOLD is the
        #      most expensive error this file can make.
        #
        #  (b) The PDUFA-bucketed branch labelled precision MONTH but still wrote the full
        #      day (2026-12-31) into `date`, so any consumer rendering `date` showed a day
        #      we had ourselves flagged as fake.
        _ph = is_placeholder(date)
        _nye = date.endswith("-12-31")
        if conf and not _ph:
            GOLD.append({"ticker": tk, "date": date, "precision": "DAY",
                         "confidence": "GOLD", "source": f"BPC/conference:{conf[:38]}",
                         "event": stage, "drug": str(d.get("Drug") or "")[:40],
                         "note": str(d.get("Catalyst") or "")[:90]})
        elif conf:
            GOLD.append({"ticker": tk, "date": date[:4] if _nye else date[:7],
                         "precision": "YEAR" if _nye else "MONTH",
                         "confidence": "SOFT", "source": f"BPC/conf-bucketed:{conf[:30]}",
                         "event": stage, "drug": str(d.get("Drug") or "")[:40],
                         "note": str(d.get("Catalyst") or "")[:90]})
        elif is_pdufa and not _ph:
            GOLD.append({"ticker": tk, "date": date, "precision": "DAY",
                         "confidence": "GOLD", "source": "BPC/PDUFA",
                         "event": stage, "drug": str(d.get("Drug") or "")[:40],
                         "note": str(d.get("Catalyst") or "")[:90]})
        elif is_pdufa:
            GOLD.append({"ticker": tk, "date": date[:4] if _nye else date[:7],
                         "precision": "YEAR" if _nye else "MONTH",
                         "confidence": "SOFT", "source": "BPC/PDUFA-bucketed",
                         "event": stage, "drug": str(d.get("Drug") or "")[:40],
                         "note": str(d.get("Catalyst") or "")[:90]})
```

`is_placeholder()` already exists in the file — no new helper needed.

## Expected result after applying

From the 09-07 run, on comparable data: **GOLD 93 → ~86**, DAY 134 → ~127, a **YEAR** tier
appears (~17 rows), and the false-GOLD count goes to **zero**. Rows are not lost — they move
from GOLD/DAY to SOFT/YEAR or SOFT/MONTH, which is what they always were.

## Please also add the regression guard

`_gold_leak_check.py` is in the repo root now (standalone, no dependencies on the verifier).
It exits non-zero when any GOLD row carries a placeholder-shaped day. Worth calling right
after `readout_gold_dates.py` in the chain so this can never ship silently again:

```bat
"%PY%" -u _gold_leak_check.py
if errorlevel 1 echo   ^>^> FALSE GOLD DATES IN THE FEED - do not publish until fixed.
```

Everything else in today's run is healthy: 527 rows all canonical (0 raw prose), window
precision and pcd precision both populated, drift detector fired on 16 moved dates, publish
step wrote 7/7 files.

*Informational only — not investment advice.*
