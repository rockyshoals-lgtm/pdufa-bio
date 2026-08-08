# Bing indexing + SERP freshness audit
**2026-08-08 · Cowork session · Amendment 033 filing**
*Live origin checks + Bing SERP `url:` probes. Facts only — not investment advice.*

---

# 1. WHAT THE BING API KEY IS ACTUALLY DOING

`BING_WEBMASTER_API_KEY` is wired into the workflow at one place:

```yaml
- name: "Bing rank snapshot (advisory)"
  env:
    BING_WEBMASTER_API_KEY: ${{ secrets.BING_WEBMASTER_API_KEY }}
  run: python bing_rank_report.py
```

`bing_rank_report.py` calls `https://ssl.bing.com/webmaster/api.svc/json` for **rank and traffic statistics** — striking-distance queries, movement vs the last snapshot, impressions-without-clicks. It is a **reporting** tool. It does **not** submit URLs.

**So no pages are being "indexed via the Bing API."** URL submission to Bing happens over **IndexNow**, which is a separate channel and is already working:

```
IndexNow: HTTP 200 for 178 URL(s) (Bing, Yandex, Seznam, Naver)
```

That is correct architecture — IndexNow *is* Bing's supported push channel, and the builder's comments confirm the old `bing.com/ping` now returns 410. Nothing is broken here. But the phrasing matters for expectations, which brings us to the key point below.

---

# 2. THE IMPORTANT DISTINCTION: SUBMITTED ≠ INDEXED

IndexNow is a **notification** ("these URLs changed"). It does not oblige Bing to index anything, and it never returns per-URL indexing confirmation. HTTP 200 means *accepted*, not *indexed*.

I measured real indexation with Bing's `url:` operator (validated against a known-good control):

| URL | Bing status | Notes |
|---|---|---|
| `/` | ✅ **Indexed** | snippet shows **"6 days ago"** |
| `/calendar` | ✅ **Indexed** | control — ranks #3; **no date shown** |
| `/sls` | ❌ **Not indexed** | submitted ~1h before test |
| `/tickers` | ❌ **Not indexed** | submitted ~1h before test |

**Read:** the older, organically-crawled pages are indexed. The pages submitted today are not yet. That is normal — Bing typically ingests IndexNow submissions over hours to days, not minutes. **Re-check in 48–72h**; that's the real test of whether the pipeline is converting submissions into index entries.

⚠️ **Caveat on method:** Bing's `site:` operator is broken for this domain — `site:pdufa.bio` returned date-calculator sites and `site:www.pdufa.bio` returned Winter Olympics logos. I could not use it for a page count. The `url:` operator does work (verified against `/calendar`), so the per-URL results above are sound, but I have no total indexed count.

⚠️ **Could not check Bing Webmaster Tools:** this Chrome profile is not signed in to BWT — it redirected to the marketing/signup page. BWT is the only place with authoritative numbers (indexed pages, crawl stats, URL submission quota). **Signing in there would let the `bing_rank_report.py` data be cross-checked and would answer "how many pages are indexed" definitively.**

---

# 3. FRESHNESS TIMESTAMP — HALF SHIPPED

## ✅ What's live
Every page now carries a **visible** freshness line, which is exactly the §5.2 recommendation:

> **"Updated August 8, 2026 · next FDA decision on …"**

And the HTTP header is correct and current:
```
Last-Modified: Sat, 08 Aug 2026 03:54:05 GMT
```

## ❌ What's missing — the machine-readable date
Checked `/`, `/calendar`, `/sls`, `/decisions`. **All four emit no date in structured data at all:**

| Signal | Status |
|---|---|
| Visible "Updated …" text | ✅ present on all pages |
| HTTP `Last-Modified` | ✅ present, current |
| **schema.org `dateModified`** | ❌ **absent on every page** |
| **schema.org `datePublished`** | ❌ **absent on every page** |
| `og:article:modified_time` | ❌ absent |

`dateModified` is the field search engines actually key on to render "2 days ago" in a snippet. Without it they fall back to guessing from crawl date and page content — which is exactly the inconsistency we observe:

- `/` → snippet shows **"6 days ago"**
- `/calendar` → snippet shows **no date at all**

Same site, same day, same visible "Updated" text, two different outcomes. That's the signature of a missing explicit signal.

For contrast, on the same SERP: **novapharmanews "1 hour ago"**, **biopharmawatch "1 day ago"**. Those sites are winning the freshness display we should own — we rebuild daily and they don't necessarily.

## Fix
Add to the JSON-LD on every page (alongside the existing `Organization`/`Dataset`/`FAQPage`):
```json
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "url": "https://www.pdufa.bio/calendar",
  "name": "2026 FDA PDUFA Calendar",
  "datePublished": "2026-02-13T00:00:00-05:00",
  "dateModified": "2026-08-08T03:54:05-04:00"
}
```
Rules that make it work:
1. `dateModified` must be **ISO-8601 with timezone**, and must match the visible "Updated …" string on the page. A mismatch is worse than nothing — engines discount dates they can't corroborate.
2. Emit it from the **same build timestamp** that writes the visible line, so they can never drift.
3. Only bump it when content actually changed. Stamping a new `dateModified` on an unchanged page is a spam signal.

## Minor inconsistency spotted
`/decisions` says *"Updated August 7, 2026"* while `/`, `/calendar` and `/sls` say *"Updated August 8, 2026"* — despite all four returning `Last-Modified: Aug 8 03:54 GMT`. Worth checking whether the visible stamp is per-page-content (correct, if /decisions genuinely didn't change) or drifting.

---

# 4. ACTIONS

| # | Action | Why | Effort |
|---|---|---|---|
| 1 | **Add `dateModified` + `datePublished` JSON-LD sitewide**, from the same timestamp as the visible line | The one missing signal for SERP date display; competitors are beating us on it | 1–2 hr |
| 2 | **Sign in to Bing Webmaster Tools** in the working browser profile | Only authoritative source for indexed-page count + URL submission quota; also validates the rank report | 5 min |
| 3 | **Re-check `/sls`, `/tickers`, `/vktx` on Bing in 48–72h** via `url:` | Confirms IndexNow submissions actually convert to index entries | 10 min |
| 4 | *(Optional)* Add Bing `SubmitUrlBatch` alongside IndexNow | A second, quota-backed submission channel with per-site confirmation. Redundant with IndexNow, so low priority | 1 hr |
| 5 | Reconcile the `/decisions` "Aug 7" vs sitewide "Aug 8" stamp | Prevents a visible/structured date mismatch once #1 ships | 15 min |

---

# 5. BOTTOM LINE

**Bing submission is working; Bing *indexing* of the new pages hasn't happened yet, and that's expected one hour after submission — not a fault.** The Bing API key is doing rank reporting, not submission, which is the correct design since IndexNow is Bing's push channel.

**The freshness work is half done.** The visible "Updated August 8, 2026" line shipped and looks good. The machine-readable `dateModified` — the part search engines actually use to print "1 hour ago" next to a result — is absent on every page checked. That single addition is the highest-value remaining item, because we genuinely rebuild daily and currently can't prove it in the SERP, while two rivals who may not are displaying fresher timestamps than us.

---
*Not investment advice.*
