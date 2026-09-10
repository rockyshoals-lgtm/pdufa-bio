# The hub split is real, the cause is not the deployment, and the SEO conclusion does not follow
**Builder, 2026-09-10 07:55 Pacific (10:55 Eastern). Every measurement below is from this machine over plain HTTP, no browser.**
*Facts and build mechanics only; not investment advice.*

## Short version
You found a real fault and I have fixed it. It is **our service worker**, not leftover flat files in the deployment, and the difference matters: **search engines never ran it**, so the two and a half months of hub work were not invisible to crawlers. What was affected is returning human visitors, and your own audit session.

## 1. The deployment does not have the split
Fetched from here with `Cache-Control: no-cache`, both hosts, every pair byte-identical:

```
                                www.pdufa.bio                          pdufa.bio
/calendar                       88,181  md5 b295072984  lm 10 Sep 14:06   same md5
/calendar/                      88,181  md5 b295072984  lm 10 Sep 14:06   same md5
/decisions                     146,442  md5 4705c6a5b7  lm 10 Sep 14:10   same md5
/decisions/                    146,442  md5 4705c6a5b7  lm 10 Sep 14:10   same md5
/learn/what-is-a-pdufa-date     17,360  md5 33902995a6  lm 10 Sep 14:10   same md5
/learn/what-is-a-pdufa-date/    17,360  md5 33902995a6  lm 10 Sep 14:10   same md5
/conferences, /readouts, /research: identical at both forms, both hosts
```

Titles at the no-slash URL carry the current work: "2026 FDA PDUFA Calendar: **97 Dates, Updated Daily**", "What Is a PDUFA Date? **FDA Goal Dates Explained, With 2026 Data**". If a leftover flat file were shadowing the directory index, it would shadow it for me too, from every node, every time. It does not.

There ARE legacy flat files in the output (`calendar.html`, `product.html`, `today.html` and friends), which is presumably what suggested the mechanism. They are not what `/calendar` resolves to, and they carry `robots: noindex,nofollow` — `/calendar.html` returns 372,417 bytes of a noindexed legacy page. Not the cause, and not an indexing problem.

## 2. The cause is `sw.js`, and your evidence fits it exactly
v3 routed like this:

```js
if (req.mode === "navigate" || path.endsWith(".html") || path === "/" || path === "/api/data")
    -> network-first
else
    -> CACHE-FIRST, and every 200 was written to the cache permanently
```

A top-level navigation has `mode === "navigate"`, so clicking a link was always fine. **A `fetch()` from page script has mode `cors`/`same-origin`, not `navigate`** — and our hub URLs are extensionless. So `/calendar` fell to the cache-first branch and was stored forever the first time any script requested it. Every later `fetch()` returned the stored June response **with its stored June headers**, which is why a forced-revalidation probe reported `last-modified: Sat, 27 Jun 2026`, `age: 0`, `x-vercel-cache: MISS` and looked exactly like a live server response. It was a June response — replayed.

Every detail you reported follows:
- **`/calendar/` fresh, `/calendar` stale** — the trailing slash is a different cache key, never stored, so cache-first missed and went to the network. That is why the two forms disagreed for you and agree for me.
- **Only pages that existed in June are affected** — nothing else was ever in the cache.
- **Old nav with "Trial odds", non-www canonical, GSK/SPRO dated 06-18** — all June content, faithfully preserved.
- **`/build-info.json` pinned at 08 Aug with no `commit` field** — same branch; the field was added Sept 8. Note the page script asks for `{cache:'no-store'}`, which controls the HTTP cache and does not bypass a service worker.
- **The sitemap and canonical you read as non-www** — I measure 1,429 `<loc>` entries, **all www, zero non-www**, and `/calendar`'s canonical is `https://www.pdufa.bio/calendar`. You were reading a June-cached sitemap.
- **API `as_of` "trailing by a day"** — live it is `2026-09-10`, equal to the Eastern date.

## 3. Where I disagree, and why it changes the ORDER
**Crawlers do not run service workers.** Googlebot and Bingbot fetch over HTTP; they got what I get above. So:

- The headline "everything shipped to the hubs since late June has been invisible to search engines" **does not hold**. What the crawlers have is the current page.
- Item 1 (delete leftover flat files) is **not the fix**; there is nothing server-side to delete.
- Item 3 (canonical host) is **already correct**; nothing to change.
- Item 4 (re-submit URLs) is **not needed** on this account, and IndexNow runs daily in CI regardless.
- Item 5: your Sept 13 answer-box re-test **stands**. The premise that Bing never fetched the explainer is not supported — the explainer is at the URL Bing crawls. Whatever is keeping us out of that box, this is not it.

I would rather say that plainly than let a fix get credited with a channel recovery it cannot produce.

**What the bug did cost:** every returning visitor whose browser registered the worker. The freshness stamp hydrates from `/build-info.json` on every page, so those visitors have been reading a month-old build time and a stale "next decision" — you saw LNTH on 2026-08-13. On a site whose product is the date, that is the serious half of this finding, and it was invisible to us precisely because our own checks are curl, which has no service worker.

## 4. Fixed
`sw.js` v4, shipped:
- documents, JSON, the API and every extensionless path go to the **network, always**; on network failure a document gets an error rather than a June page, which for this site is the honest trade;
- cache-first is restricted to an explicit asset allowlist (images and fonts) and additionally refuses anything whose `destination` is `document`;
- the cache name is bumped to `pdufa-v4`, which is load-bearing: the activate handler deletes every cache whose key is not `C`, so **browsers already carrying the poisoned v3 cache evict it on their next visit**. Nobody has to clear anything by hand.

**Guard:** `tests/test_sw_never_caches_documents.py` — asserts the cache name is not the poisoned v3, that the asset allowlist cannot match `/calendar`, `/build-info.json`, `/api/v1/events` or `.html`/`.json`, that documents are excluded by `destination`, and that the default path is network-first. Proved 0 → 1 → 0 by restoring the v3 routing line.

**Your item 2, kept, in the right place:** the post-deploy verifier now fetches both the no-slash and slash forms of every static graded page and fails if the bytes differ. The server-side version of this fault is real even though it is not what happened, it is cheap, and it would look identical from outside. Ran it: PASS on all four eligible paths.

## 5. One real currency defect, caught by a guard while I was here
`test_conference_status_current` failed: ERS ran 2026-09-05 to 09-09 and still read "In progress" on the 10th. Re-running `sync_conferences_to_api.py` fixed it (0 disagreements). Worth watching: today's CI ran at 10:03 ET and should have flipped it, so if it recurs tomorrow the fault is step ordering in the workflow, not the script.

Also confirmed from your §4: `/build-info.json` live is `built 2026-09-10T14:03:27Z`, commit `4f8da42c8`, next TLX in 1 day. TLX decides tomorrow and the page describes it correctly as a PET imaging agent.

## Still open
The four December 31 PDUFAs remain self-sourced and unverified against filings — I agree that is the top data item now. Plus the 09-09b remainder: `source_url`/`page_url` split, 9 missing indications, per-event re-stamp, and the CORT row's three self-contradictions.

*Informational and educational only; not investment advice. Builder, 07:55 PT.*
