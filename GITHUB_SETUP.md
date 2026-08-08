# Move the daily rebuild to GitHub Actions (server-side, always-on)

This makes the **deterministic** half of the pipeline run on GitHub's servers every day — whether or
not the desktop app is open — and auto-deploy via your Vercel Git integration. The **agentic** half
(verifying a resolved FDA outcome against a primary source, then publishing it) stays on the Claude
scheduled task, because that needs judgment and must not be automated blindly.

I've committed two files for you: `.github/workflows/pdufa-rebuild.yml` and a hardened `.gitignore`.
The steps below are the ones I **can't** do from here (they need your GitHub + Vercel login).

---

## ⚠️ Before anything: do NOT leak your keys
This working folder contains `Odin Perfection/.env_master` with your live Polygon/FMP/ORATS/UW keys,
plus multi-GB caches. The `.gitignore` I added excludes them, but **verify** before the first push:

```
git status         # confirm .env_master, Odin Perfection/, uw_export_2026/ are NOT listed
git ls-files | grep -i env    # must return NOTHING
```
If a key ever lands in a commit, rotate that key immediately — git history is forever.

---

## One-time setup (~10 min)

1. **Point the repo at only the site + pipeline.** Easiest: create the GitHub repo, then from this
   folder push just what the Action needs (the `.gitignore` keeps secrets/caches out):
   ```
   cd "C:\Users\dcmoo\Documents\Python\9realms"
   git init
   git remote add origin https://github.com/<you>/<repo>.git
   git add .gitignore .github pdufa_site_src tests polygon_enrich.py build_home_board.py \
           check_pdufa_decided.py catalyst_crawler.py merge_crawl_to_slate.py
   git add -f catalysts_out/universe_effective.txt catalysts_out/catalysts_public.csv
   git commit -m "pdufa.bio site + pipeline"
   git branch -M main && git push -u origin main
   ```

2. **Add the Action secret** — repo → Settings → Secrets and variables → Actions → New secret:
   - `POLYGON_API_KEY` = your Polygon Ultimate key
   - (`FMP_API_KEY` too if you later run the crawler in CI)

3. **Connect Vercel to the repo** — Vercel dashboard → the pdufa.bio project → Settings → Git →
   connect this GitHub repo, and set **Root Directory = `pdufa_site_src`**. From now on every push to
   `main` auto-deploys. (This replaces the CLI `vercel deploy` path.)

4. **Test it** — GitHub → Actions tab → "pdufa daily rebuild" → **Run workflow**. Confirm: guards
   pass, it commits a data refresh, Vercel deploys, and `Data through` on the homepage shows today.

---

## What the Action does each day (05:00 PT)
`polygon_enrich` (prices) → `build_home_board` (sorted board + sparklines) → **13 CI guards (hard-fail
blocks the deploy)** → FDA reconciliation → commits refreshed data → Vercel auto-deploys. If the FDA
feed shows an approval missing from our archive, it **opens a GitHub issue** instead of guessing.

## Important: avoid two deploy paths fighting
Once Vercel deploys from Git, the **desktop Claude task should stop CLI-deploying**. Two clean options:
- **Recommended:** keep the Claude task for the *agentic* work only (verify + publish resolved
  outcomes, act on reconciliation issues) and have it **commit + push** instead of `vercel deploy`,
  so everything flows through git. (Tell me and I'll rewrite its deploy step to `git push`.)
- Or: disable the desktop task entirely and let GitHub do the deterministic daily run, doing outcome
  verification manually / on request.

Either way, don't leave both `vercel deploy` (desktop) and git-push (Actions) live — they'll diverge.

## What stays on the Claude task (not in GitHub)
Verifying a resolved PDUFA/approval against a primary source and publishing the outcome; acting on the
reconciliation issues; the supervised catalyst crawl (`PDUFA_Crawler.bat`) + merge. These need an LLM
with web access and judgment — a cron script can detect and flag, but must not publish an outcome.
