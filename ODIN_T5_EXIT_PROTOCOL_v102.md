# ODIN T-5 EXIT PROTOCOL v10.2

**Effective Date:** 2026-02-02  
**Index Case:** PHAR CRL (January 31, 2026)  
**Philosophy:** Capital preservation > Brier optimization

---

## THE CORE THESIS

**Binary biotech events create asymmetric risk.** 

The runup to a PDUFA date captures 80-90% of the expected gain by T-5. Holding through the binary event exposes capital to catastrophic gap risk that cannot be hedged effectively.

### PHAR Case Study (Index Case)
| Timepoint | Price | Action | Outcome |
|-----------|-------|--------|---------|
| T-30 | $17.06 | Entry | Runup begins |
| T-5 (Jan 27) | $21.18 | **EXIT** | +24.1% LOCKED |
| T-0 (Jan 31) | Weekend PDUFA | CRL announced | - |
| T+1 (Feb 3) | ~$10-12 | Gap down | -40% to -50% |

**Investors who exited T-5:** +24.1% gain  
**Investors who held through:** -30% to -40% loss  
**Capital preserved by T-5 rule:** ~50% of position value

---

## T-5 EXIT RULES BY ODIN TIER

| ODIN Tier | Exit Day | Runner | Position Size | Rationale |
|-----------|----------|--------|---------------|-----------|
| **TIER_1** (≥86%) | T-5 | 10% max | Full | High confidence, small runner acceptable |
| **TIER_2** (73-85%) | T-5 | 0% | 75% | Moderate confidence, no runner |
| **TIER_3** (58-72%) | T-7 | 0% | 50% | Low confidence, exit early |
| **TIER_4** (<58%) | **NO ENTRY** | N/A | 0% | High CRL risk, avoid entirely |

### Special Cases

| Scenario | Exit Rule | Rationale |
|----------|-----------|-----------|
| Weekend PDUFA | Thursday close / Friday open | No exit opportunity after announcement |
| Pediatric sNDA | T-10, 0% runner | Dosing complexity risk |
| Any CMC delay mention | **IMMEDIATE** | 2-5x CRL probability |
| EMA concerns disclosed | **IMMEDIATE** | Cross-regulatory signal |
| <3 commercial hires | T-10 | Hiring void = sponsor concern |

---

## WHY T-5 WORKS: EMPIRICAL EVIDENCE

### 180 Historical CRLs Analyzed

| Metric | Hold Through | T-5 Exit | Difference |
|--------|--------------|----------|------------|
| Average return | -38.5% | +11.0% | **+49.5%** |
| Capital at risk | $1.8M | $1.8M | - |
| Portfolio outcome | -$693,755 | +$198,745 | **+$892,500** |
| Per-event savings | - | - | **$4,958** |

### By Tier (180 CRLs)

| Tier | CRLs | T-5 Capture | Hold-Through Loss | Capital Saved |
|------|------|-------------|-------------------|---------------|
| TIER_1 | 72 | +15.0% | -35.0% | 50.0% |
| TIER_2 | 17 | +15.2% | -33.0% | 48.2% |
| TIER_3 | 67 | +7.6% | -41.8% | 49.3% |
| TIER_4 | 24 | +6.0% | -44.0% | 50.0% |

### The 74 "Dangerous" High-Prob CRLs (≥85%)

These are the WORST outcomes - market expected approval, got CRL.
T-5 exit would have saved an average of **50%** per position.

Examples from dataset:
- GILD: 99% prob → -50% gap
- BIIB: 99% prob → -43% gap  
- LLY: 93% prob → -42% gap
- BMRN: 99% prob → -44% gap

---

## PRICE ACTION TIMELINE

```
T-30 to T-10: Institutional accumulation (bulk of runup)
T-10 to T-5:  Late momentum, retail FOMO entry
T-5 to T-0:   Theta decay, IV crush, smart money exits
T-0:          Binary event (approval or CRL)
T+1:          Gap resolution (+10-20% or -30-50%)
```

### Key Insight
By T-5, you've captured ~80-90% of the runup with ~0% of the binary risk.

---

## HARD AVOID SIGNALS (NO ENTRY AT ANY TIER)

| Signal | Severity | Trigger |
|--------|----------|---------|
| AVOID_001 | CRITICAL | EMA CMC flag |
| AVOID_002 | HIGH | <3 commercial hires within 6 months |
| AVOID_003 | CRITICAL | Pediatric sNDA without published PK study |
| AVOID_004 | CRITICAL | CMC extension from any regulatory agency |
| AVOID_005 | HIGH | Weekend PDUFA with probability <80% |

If ANY hard avoid signal triggers: **NO POSITION, NO EXCEPTIONS**

---

## EXECUTION CHECKLIST

### Entry (T-30 to T-20)
- [ ] Run ODIN v10.2 scoring
- [ ] Check all hard avoid signals
- [ ] Verify no EMA/FDA CMC concerns
- [ ] Confirm hiring gradient (>3 commercial hires)
- [ ] Check publication count (>10 for non-orphan)
- [ ] Set calendar alerts for exit dates

### Position Management (T-20 to T-5)
- [ ] Monitor for new hard avoid signals daily
- [ ] Track price action vs expected runup
- [ ] Prepare exit orders in advance
- [ ] NO averaging up after T-10

### Exit (T-7 to T-5)
- [ ] TIER_3/4: Exit at T-7
- [ ] TIER_1/2: Exit at T-5
- [ ] Weekend PDUFA: Exit Thursday/Friday
- [ ] Verify all shares sold
- [ ] Document final return

### Post-Event
- [ ] Track outcome for model validation
- [ ] If CRL: Add to dataset with v10.2 fields
- [ ] Update signals that would have caught it

---

## THE CARDINAL RULE

> **"We don't hold through binary events. The runup IS the trade."**

A +15% gain at T-5 is infinitely better than a -35% loss from holding through a CRL.

The PHAR loss would have been catastrophic:
- Weekend PDUFA = no exit after announcement
- Gap down -40% to -50% on Monday open
- No stop loss could have executed

**T-5 exit preserved 100% of the +24% gain.**

---

## VERSION HISTORY

| Version | Date | Change |
|---------|------|--------|
| v10.2 | 2026-02-02 | Index case PHAR CRL; added hard avoid signals; refined tier exit rules |
| v10.1 | 2026-01-29 | Added specialist composite signal |
| v9.1 | 2026-01-22 | Therapeutic area adjustments |

---

*This protocol is mandatory for all ODIN-guided PDUFA trades. Exceptions require explicit override documentation with rationale.*
