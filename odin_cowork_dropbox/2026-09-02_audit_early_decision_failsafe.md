# Audit — 2026-09-02 · early-decision fail-safes
**Site built 2026-09-02T16:06Z · all checks cache-busted against that build**
*Facts and historical statistics only — not investment advice.*

---

# 1. ✅ THE P0 IS FIXED, AND FIXED PROPERLY

| Check | Result |
|---|---|
| REGN in the API | ✅ `status: Decided` · `outcome: Approved` · `decision_date: 2026-08-19` |
| REGN event page | ✅ *"Approved · the FDA decided this application on August 19, 2026, **12 days before** its August 31, 2026 goal date."* |
| Timing sample | ✅ **n=28** — 16 before · 9 on · 3 after (16+9+3=28 ✓) |
| `/today` | ✅ **308 → `/fda-decisions-today`** |
| Past-goal events with no outcome | ✅ **0 of 26** |

The event-page sentence is exactly right: outcome, exact date, the delta, and a link to the source. No hedging, no jargon.

**And the builder found one I missed.** `17a7fdc53` — **AZN Truqap (capivasertib), approved 2026-06-12, 18 days early**, verified against FDA.gov. That's a second early approval nobody had caught, and it's what took the sample from 27 to 28.

---

# 2. ✅ THE FAIL-SAFE IS REAL — and it closes the right gap

`watch_fda_approvals.py` (154 lines) + `tests/test_decided_not_upcoming.py` (60 lines), **53 guards**, wired into CI at workflow line 160.

**Why it's the right design:**

**It is independent of our own crawl.** The file states the gap precisely:
> *"every safeguard we had was downstream of our own news crawl — if nobody told us about an approval, nothing looked for it."*

It asks **FDA's own Drugs@FDA feed** directly, daily, for every armed day-precision event, looking for an `AP` submission inside the same review cycle (**−180..+45** days of the goal date).

**It blocks rather than warns.** Unreviewed hits `EXIT 1`, so CI stops. Reviewed leads go to `_fda_watch_ack.json` with a reason — *"shrink it; never grow it silently."*

**It's a lead, never an auto-publish.** Verify-then-publish discipline intact.

**It's honest about its own limits — which is what makes it trustworthy.** They measured the feed lag rather than assuming it:
> *"garetosmab's Aug 19 approval appeared in the feed by Aug 28 (~9-day lag); capivasertib's Jun 12 approval is recorded to the exact day. So this is a SAFETY NET measured in days, not a same-day detector — the crawl stays the fast path."*

**And the guard asserts the outcome, not the process:**
> *"this guard asserts the RESULT, so the safeguard survives even if the CI step is reordered or dropped — the frozen-family lesson."*

That is the correct defensive instinct, and it cites a prior failure to justify itself.

## Honest limits worth knowing
1. **~9-day worst-case detection.** A REGN-class miss now surfaces in about a week instead of never. Real improvement; not same-day.
2. **Day-precision Upcoming events only.** Month/quarter-precision events aren't watched — defensible (no day to window against), but it's a blind spot if a bucketed event resolves early.
3. **Name matching is the weak link.** They hit it (the "lenacapavir trap") and added a lead-token rule. This is the part most likely to fail quietly in future.
4. **60-day lookback** — safe unless CI is red for two months.

---

# 3. 🟠 THE REMAINING GAP: the safeguard protects the DATA layer; six PAGES still say "pending"

**The dataset is clean.** All 26 past-goal events are resolved; zero unresolved.

**But the event pages haven't caught up.** Of nine events decided since 2026-08-01:

| Ticker | Decided | Page shows the decision? | Page `Updated` |
|---|---|---|---|
| MRNA | 08-05 | ❌ **NO** | Aug 7 |
| TAK | 08-05 | ❌ **NO** | Aug 7 |
| LNTH | 08-13 | ✅ yes | Aug 26 |
| **BMY** | 08-13 | ❌ **NO** | Aug 8 |
| RARE | 08-19 | ✅ yes | Sep 2 |
| REGN | 08-19 | ✅ yes | Sep 2 |
| **JAZZ** | 08-25 | ❌ **NO** | Aug 7 |
| **ZYME** | 08-25 | ❌ **NO** | Aug 7 |
| **GILD** | 08-27 | ❌ **NO** | Aug 7 |

`/pdufa/JAZZ` still reads **"FDA decision (PDUFA) target 2026-08-25"** — a drug approved on that date, eight days ago.

Commit `b63783091` says *"decided banners on event pages (daily)"* — **it isn't running daily across the set.** It reached the three pages that were individually touched.

**Why this matters:** these are the highest-converting pages on the site (`/pdufa/JAZZ` 8.33% CTR at position 2.64; the page type peaks at 60%). And the new guard **would pass right now** — it asserts dataset state, and the dataset is correct. **The guard and the defect are in different layers.**

**Two fixes, both cheap:**
1. Make the decided-banner pass iterate **every** decided event each build, not only edited ones.
2. Add **guard 54**: *no event whose dataset row is `Decided` may have a page lacking its decision banner.* That closes the render layer the same way `test_decided_not_upcoming.py` closed the data layer.

*Note: pages for events still genuinely upcoming (PTGX, NVO-mim8 — both 2026-09-30) carry an Aug 7 stamp and that is **correct**. Nothing changed, so nothing should be re-stamped. Don't "fix" those.*

---

# 4. STILL OPEN FROM EARLIER

| Item | Status |
|---|---|
| Link the **458** FDA CRL letters | ❌ `/decisions/crl` still 0 fda.gov links |
| `/crl` hub | ❌ 404 |
| `Drug` schema on 544 drug pages | ❌ absent |
| `/pdufa-date-changes` | ❌ 404 |
| `/decisions/crl` lede 47 vs 44 | ❌ unreconciled |

---

# 5. ORDER

| # | Action | Why |
|---|---|---|
| 1 | Run the decided-banner pass over **all** decided events each build | 6 pages advertise a pending decision on approved drugs |
| 2 | **Guard 54** — decided row ⇒ page must show the decision | closes the render layer |
| 3 | Watch the name-matcher | most likely quiet future failure in the watcher |
| 4 | Link the 458 CRL letters | primary sources held and uncited |
| 5 | `Drug` schema + `alternateName` | biggest non-link citation lever |
| 6 | `/crl` hub · `/pdufa-date-changes` · lede reconciliation | previously specced |

---

# BOTTOM LINE

**The fail-safe you asked for exists and is well built.** It queries FDA's own feed rather than trusting our crawl, blocks CI on an unreviewed approval, treats every hit as a lead rather than a publish, and states its own measured detection lag (~9 days worst case) instead of overclaiming. The companion guard asserts the *result* so it survives a reordered pipeline. That is the right shape for a safety net.

**The P0 is properly closed** — REGN reads "Approved… 12 days before its goal date", the timing sample is honestly at n=28, and the builder caught **AZN Truqap at −18 days** on their own in the process.

**One gap remains and it sits one layer above the new guard.** The dataset is clean on all 26 past-goal events, but **six event pages — MRNA, TAK, BMY, JAZZ, ZYME, GILD — still show a pending decision on drugs already approved.** The new guard passes because it checks the data, and the data is right. A second guard asserting *"a decided row implies a page that says so"* would close it, and the banner pass needs to run across every decided event rather than only the ones someone touched.

---
*Verified against the 2026-09-02T16:06Z build. Not investment advice.*
