# External research prompt (feed to Gemini Deep Research + Perplexity Research)

Paste everything in the box below. Run it on **both** engines, then bring both responses back for audit.

---

**ROLE.** You are a market-microstructure research analyst. Prioritize verifiable, citable evidence and
clearly separate strong evidence (peer-reviewed / large-sample) from weak or anecdotal claims (blogs,
marketing). This is informational/educational research, NOT investment advice — do not give buy/sell
recommendations.

**TOPIC.** Predicting whether a large single-day gainer in **small/micro-cap U.S. stocks** will *continue*
higher or *fade* during the same trading day, using intraday price and volume behavior — i.e., the
"buy early and ride the momentum" question.

**MY CURRENT FINDINGS (please corroborate, refute, or refine each with external evidence).**
I studied ~3,000 U.S. small/micro-cap stocks (market cap ≤ $2B) that rose ≥30% in a single day over ~2 years,
using 30-minute intraday bars and each stock's trailing 20-day average daily volume (ADV):
1. **Early volume is inversely related to continuation.** When first-hour volume was under ~1× the stock's
   normal ADV, price continued higher into the close ~95% of the time (avg +29% further). When first-hour
   volume exceeded ~10× ADV, continuation fell to ~62% (avg +12%). Correlation between early relative volume
   and closing strength was slightly negative.
2. **Big early moves exhaust.** If a stock was already up 50%+ in the first hour, it continued to the close
   only ~39% of the time, vs ~87–89% for moves under 25%.
3. **Interpretation:** quiet "gap-and-grind" on moderate volume tends to close near highs; explosive,
   high-volume blow-offs tend to spike and fade.
4. **Known weaknesses of my study:** universe is *currently-listed* names (survivorship bias — excludes
   delisted pump-and-dumps), and events were selected because they *closed* ≥30% up (selection-on-outcome).

**RESEARCH QUESTIONS.**
1. Intraday momentum continuation vs. reversal after large gaps/surges: what do academic papers AND
   practitioner studies find? (gap-and-go vs. gap-fade, opening-range breakout, intraday momentum vs.
   mean-reversion.)
2. Does **relative volume** (vs. average) predict continuation? Is there real evidence that extreme/
   "climactic"/"blow-off" volume marks *exhaustion/reversal* rather than confirmation? Volume–price divergence.
3. Opening-range / first-hour dynamics: does the *size* of the early move predict continuation? Time-of-day effects.
4. Small/micro-cap-specific mechanics: float rotation, short interest & squeezes, LULD trading halts,
   bid-ask spread/liquidity, dilution / ATM offerings, pump-and-dump signatures.
5. VWAP position and where price sits in the day's range as continuation/fade signals.
6. Predictors I may be missing: catalyst/news type, halts, borrow fees, options flow/gamma, sector, insider/
   institutional flow.
7. **Methodology critique**: survivorship bias, selection-on-outcome, look-ahead, data-snooping, regime
   dependence, and realistic transaction costs/slippage/halts on micro-caps. What is best-practice design
   for a study like mine (point-in-time universe, out-of-sample, prospective/live logging)?
8. Concrete, *testable* rules or thresholds practitioners publish (label clearly whether they are backtested
   or just asserted).

**OUTPUT FORMAT (required — make it auditable).**
A. A findings table. One row per claim, columns:
   `Claim | Evidence type (peer-reviewed / working paper / practitioner / anecdotal) | Source + URL | Strength (High/Med/Low) | Supports / Refutes / Refines my finding | Testable rule (if any)`
B. Top 3 findings that **challenge or contradict** my results.
C. Top 3 additional signals worth adding to my model (with rationale).
D. Key caveats and where the evidence is thin.

**RULES.** Cite sources with working URLs. Give each study's sample size and time period where possible.
Distinguish correlation from causation. Flag anything that is marketing rather than evidence. Do not
fabricate citations — if you are unsure a source is real, say so.

---

## After you run it
Bring back **both** responses (paste them or drop them in a file). I'll audit for: real vs. fabricated
citations, strength of evidence, agreement between the two engines, and anything that genuinely challenges
or extends our results — then write the vetted findings into `EXTERNAL_RESEARCH.md` in this folder for the
builder to fold into the model.

**Engine tips:** Perplexity → use *Research* (Deep Research) mode. Gemini → use *Deep Research*. Both should
return citations; ask a follow-up "list every source URL you used" if they don't.
