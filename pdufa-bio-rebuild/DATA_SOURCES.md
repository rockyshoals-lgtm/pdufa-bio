# DATA_SOURCES — APIs, rate limits, gotchas

_All values verified during the build session (June–July 2026). Re-verify plan-specific limits against the live accounts._

---

## ⚠️ Critical fix (must ship) — FMP `avgVolume`

**Symptom:** the momentum scanner returns **0 candidates from ~150 names** even mid-session.

**Root cause:** FMP's `/stable/quote` response **no longer contains an average-volume field.** Its keys are:
`symbol, name, price, changePercentage, change, volume, dayLow, dayHigh, yearHigh, yearLow, marketCap,
priceAvg50, priceAvg200, exchange, open, previousClose, timestamp`. There is **no `avgVolume` / `averageVolume`.**

In the scanner:
```python
avgv = float(quote.get("avgVolume", quote.get("averageVolume", 0)) or 0)   # -> 0 for EVERY name
relv = (vol / avgv) if avgv > 0 else 0                                      # -> always 0
mover = (avgv >= MIN_AVG_VOLUME and abs(chg) >= MIN_DAY_CHANGE_PCT)         # -> always False
```
So the "mover" filter never fires, relative volume is always 0, the volume score is dead, and a
🚀 **ROCKET can never trigger** (its volume leg needs `relv >= 5`).

**Fix:** average volume lives on **`/stable/profile`** as `averageVolume` (verified live: `CELZ` → 78,725;
`AMD` → 37,578,872). Two clean options for the port:

1. **Use `/stable/profile.averageVolume` for relative volume** in scoring (profile is already fetched during
   enrichment), and for the candidate gate use **today's `volume`** from the quote as the liquidity floor:
   ```
   mover = (quote.volume >= MIN_DAY_VOLUME and abs(chg) >= MIN_DAY_CHANGE_PCT)
   relv  = quote.volume / profile.averageVolume     # true relative volume, drives ROCKET
   ```
2. Or batch a dedicated average-volume source once/day and cache it (see caching note below).

Either way: **relative volume must come from `/stable/profile.averageVolume`, not `/stable/quote`.** This is
the single highest-priority correctness fix in the rebuild.

---

## FMP (Financial Modeling Prep) — universe, quotes, news

- **Base:** `https://financialmodelingprep.com/stable`
- **Auth:** `?apikey=$FMP_API_KEY` query param.
- **Endpoints used:**
  | Path | Use |
  |---|---|
  | `biggest-gainers` | universe (movers) |
  | `most-actives` | universe (movers) |
  | `quote?symbol=` | price, %chg, today's volume, marketCap. **No avg volume — see fix above.** |
  | `profile?symbol=` | sector/industry, **`averageVolume`**, marketCap. Near-static → cache. |
  | `news/stock?symbols=&limit=` | fresh headlines + catalyst keyword classifier |
  | `grades?symbol=&limit=` | recent analyst up/downgrades |
- **Rate limit:** depends on FMP plan tier — **verify the account's plan** before setting cadence. Cache profile (static) and news (slow) to conserve.

## Unusual Whales — options flow firehose, per-name options, short interest

- **Base:** `https://api.unusualwhales.com`
- **Auth:** header `Authorization: Bearer $UW_API_KEY`, `Accept: application/json`.
- **Plan:** Retail Pro + API Basic.
- **Rate limit:** **~120 requests/minute** default, **plus daily caps that vary by plan.** Upgrade or throttle for more. Confirm the exact daily cap on the account, then size cadence under it (§4 of BUILD_SPEC).
- **Endpoints used:**
  | Path | Use |
  |---|---|
  | `api/option-trades/flow-alerts` (params `limit`, `min_premium`, `vol_greater_oi=true`) | **Market-wide UOA firehose, all sectors.** One call → aggregate by ticker (premium, ask-side call/put, sweeps, max vol/OI). Drives the UOA score + bias, and can lead price. |
  | `api/stock/{t}/options-volume` | per-name call/put volume vs 30d avg (options spike) |
  | `api/shorts/{t}/data` | % float short, days-to-cover (squeeze fuel). Changes ~daily → cache daily. |
  | `api/stock/{t}/flow-alerts` | per-name sweep detection |

### Does Unusual Whales provide social sentiment? — **No (not via API).**
- **API:** checked the UW public API docs directly for `social`, `sentiment`, `socials`, `tweet/twitter/mentions`, `news` → **zero matching endpoints.** UW's API is options flow, dark pool, congress, insider, institutions, Greeks. **You cannot pull UW social programmatically.**
- **Website only:** UW does run a free [Socials Tracker](https://unusualwhales.com/socials) on their site that watches Reddit/Twitter chatter — but it is screen-only, not a machine-readable feed.
- **Important framing:** in this system UW was never the social layer — it is the **options tape.** There is nothing to "replace UW with" for social; they are different jobs. If you want better social, add/swap the social vendors below.

## Social sentiment vendors (2026, verified)

| Vendor | API? | Key? | Cost | Signal | Status / notes |
|---|---|---|---|---|---|
| **LunarCrush** | Yes | Yes (`$LUNARCRUSH_API_KEY` **already set**) | Paid | Galaxy Score + social sentiment (multi-platform) | Strongest social signal already wired. Keep. |
| **StockTwits** | Yes (public stream) | No | Free (best-effort) | Community **bull/bear** self-labeled sentiment | Dev API frozen to new devs, but the keyless `streams/symbol/{t}.json` endpoint the scanner uses still works. Keep. |
| **ApeWisdom** | Yes | **No** | **Free** | Reddit/WSB **mention counts** (velocity, ~30 subs, hourly) — not true sentiment | **Recommended free add** for mention velocity. `apewisdom.io/api/`. |
| **Quiver Quantitative** | Yes | Yes | Paid | WSB NLP sentiment (back to 2018) | Optional upgrade if you want cleaner NLP than mention counts. |
| **Finnhub** | Yes | Yes | Social endpoint is **paid only** (not on free tier) | Reddit/Twitter social sentiment | Only if already paying for Finnhub. |
| StockGeist / Utradea | Yes (some via RapidAPI) | Yes | Paid | Sentiment scores | Niche; evaluate only if the above fall short. |

**Recommendation:** keep **LunarCrush + StockTwits**, **add ApeWisdom (free)** for Reddit mention velocity.
Treat social as a **secondary** signal, capped (~10% of the momentum score) — never proof. Keep Reddit/PRAW
optional (off unless `REDDIT_*` keys are set).

---

## Sources
- Unusual Whales API rate limits / pricing — https://unusualwhales.com/pricing
- Unusual Whales Socials Tracker (web-only) — https://unusualwhales.com/socials
- ApeWisdom API (free, keyless) — https://apewisdom.io/api/
- Finnhub social sentiment (paid tier) — https://finnhub.io/docs/api/social-sentiment
- 2026 stock sentiment API comparison — https://adanos.org/insights/blog/best-stock-sentiment-apis-2026/
- FMP field shapes (`/stable/quote` vs `/stable/profile`) — verified live during build session.
