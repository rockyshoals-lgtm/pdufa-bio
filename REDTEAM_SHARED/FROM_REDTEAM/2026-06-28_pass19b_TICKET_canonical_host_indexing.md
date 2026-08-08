# BUILDER TICKET — One canonical host + indexing hygiene · 2026-06-28 (Pass 19b)

**Priority:** P0 for SEO. **Type:** config + templates. **Owner:** builder.
**Correction note:** this supersedes the host claim in `pass19`. After direct testing, **neither host redirects** — both `pdufa.bio` and `www.pdufa.bio` serve 200. The fix is to *add* a redirect and consolidate on **apex** (which everything already points to), not to "switch to www."

---

## TL;DR
The site serves identical pages on **both** `pdufa.bio` (apex) and `www.pdufa.bio` with **no redirect between them** — both return HTTP 200. Canonical tags, the sitemap, robots.txt, and OG URLs already all point to **apex**. The missing piece is the redirect: **301 www → apex**, then remove a stale sitemap, kill the dead ODIN ghost URLs, and dedupe `/pricing.html`. Then re-submit + request-index.

## Evidence (verified live, 2026-06-28)
| Check | Result |
|---|---|
| `https://pdufa.bio/decisions` | **200**, canonical `https://pdufa.bio/decisions`, internal links apex |
| `https://www.pdufa.bio/decisions` | **200 (no redirect)**, canonical `https://pdufa.bio/decisions`, internal links www |
| `https://pdufa.bio/` and `https://www.pdufa.bio/` | both **200**, neither redirects |
| robots.txt | `Sitemap: https://pdufa.bio/sitemap.xml`; sitemap = 170 apex URLs |
| GSC → Sitemaps | TWO submitted: apex `pdufa.bio/sitemap.xml` (170, read Jun 25) **+ stale `www.pdufa.bio/sitemap.xml` (35, read Feb 25)** |
| GSC → Pages (updated Jun 11) | **11 indexed** / 25 not-indexed (17 redirect error · 3 page-with-redirect · 5 crawled-not-indexed) / 36 known |

## Reality check (so we fix the right thing — don't over-claim)
The "11 indexed" snapshot is dated **Jun 11**, which is *before* the 170-URL sitemap (read Jun 25) and before the latest content push — so it lags the live site and is probably already improving. A new domain with **zero backlinks** also just indexes slowly. So this ticket **removes the obstacles**; it is not a switch that indexes 170 pages overnight. Expect gradual gains over ~2–6 weeks, accelerated by the backlink push. The single biggest growth lever remains backlinks (kit in `pass10a`).

## Decision: consolidate on **apex** (`pdufa.bio`)
Everything already points to apex (canonical, sitemap, robots, OG). So keep apex canonical and **301-redirect www → apex** — lowest-effort, already-consistent. (Choosing `www` instead is the same work but *also* requires flipping every canonical tag, the sitemap, robots, and OG to www — more surface. Recommend apex.)

## Changes (behavior + config — map to your actual files)
1. **301 redirect www → apex, all paths.** Vercel: Project → Domains → set `www.pdufa.bio` to **Redirect to `pdufa.bio`**; OR in `vercel.json`:
   ```json
   {
     "redirects": [
       { "source": "/:path*",
         "has": [{ "type": "host", "value": "www.pdufa.bio" }],
         "destination": "https://pdufa.bio/:path*",
         "permanent": true }
     ]
   }
   ```
2. **Internal links → root-relative.** Templates emit absolute links to whichever host served (apex page → apex links, www page → www links). Change nav/footer/in-content links to **root-relative** (`/calendar`, `/decisions`, …). Kills this whole bug class and stops www URLs being crawled.
3. **Remove the stale `www` sitemap.** GSC → Sitemaps → `https://www.pdufa.bio/sitemap.xml` → Remove. Ensure the generator emits ONE sitemap of apex URLs only.
4. **Kill the 3 ODIN ghost URLs at the source.** `/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar` currently 404 → return **410 Gone** (preferred) or 301 → `/calendar`. Confirm they're absent from the sitemap. *(GSC temporary-removals already submitted as a 6-month stopgap — the 410 is the durable fix.)*
5. **Dedupe `/pricing.html`.** Both `/pricing` and `/pricing.html` are in the sitemap. Keep `/pricing`; 301 `/pricing.html` → `/pricing`; drop `.html` from the sitemap. (Vercel `cleanUrls:true` does this globally — then verify no `.html` remains in the sitemap.)
6. **Cookie scope (carryover).** Scope the gate "remember me" cookie to `Domain=.pdufa.bio` so it survives the www→apex redirect and works on `/today` + `/app`.

## After deploy — GSC steps (in order)
1. Sitemaps → re-submit `https://pdufa.bio/sitemap.xml`; remove the www sitemap.
2. Pages → open **Redirect error (17)** and **Page with redirect (3)** → read the example URLs (confirm they're the www/.html/ghost URLs above) → after deploy click **Validate Fix**.
3. URL Inspection → Request Indexing for ~10 (quota/day): `/`, `/calendar`, `/decisions`, `/readouts`, `/methodology`, `/fda-approval-rate`, `/clinical-trial-success-rates`, `/learn/what-is-a-pdufa-date`, + 2 top `/pdufa/[ticker]`.
4. Re-check Pages in ~1 week — indexed count should climb.

## Acceptance criteria (curl)
- `curl -sI https://www.pdufa.bio/decisions` → **301** → `https://pdufa.bio/decisions`
- `curl -sI https://pdufa.bio/decisions` → **200**
- `curl -sI https://www.pdufa.bio/` → **301** → `https://pdufa.bio/`
- `curl -sI https://pdufa.bio/pdufa-calendar` → **410** (or 301 → `/calendar`)
- `curl -sI https://pdufa.bio/pricing.html` → **301** → `/pricing`
- Sitemap: apex-only, no `.html`, no ghost URLs; GSC shows ONE sitemap
- View-source on 3 random pages: `<link rel=canonical>` = apex; nav links root-relative

## What this does NOT fix (separate items, see tracker)
Backlinks (the real ranking lever), `/readout/[id]` pages, new-page schema (`/devices`, `/readouts`, `/pricing`), homepage H2 hierarchy, the "±% cohort" label. Indexing hygiene ≠ ranking — backlinks + the on-charter content do that.

*— Red Team Pass 19b (builder ticket).*
