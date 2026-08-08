# pdufa.bio — Go-Live Runbook (target 2026-07-01)

**Status:** the fresh crawl is in (readouts 480 → 1,000, dataset ~doubled, dedup/QA working).
All pages are built and assembled into `pdufa_site_src/`. Stripe is built. You do the steps below;
I do the deploy + the `/app`/`/today` re-encryption.

---

## YOUR STEPS, in order

### Step 1 — (optional, background) finish the option-chart backlog
Terminal in your `9realms` folder:
```
python build_option_charts.py --universe option_chart_universe.csv --workers 12 --max-calls 80000
```
Resumes from the ~35 done; ~75 min at ~900/min; fills `opt_charts/index.html`. Not needed for launch.

### Step 2 — assemble the deploy folder
```
python assemble_site.py
```
Folds the fresh `/readouts` + `/devices` + the SEO pages (month archives, conditions, "why no %", coverage) + `pricing.html` into `pdufa_site_src/`, and refreshes `sitemap.xml`. (Re-run any time the data refreshes.)

### Step 3 — purge the homepage cache  🔴 LAUNCH BLOCKER #1
The apex still serves the old "Coming soon." In the Vercel dashboard:
1. Open the project that serves the live `pdufa.bio` (the **staging** one).
2. **Settings → Caching → Purge Everything.**  *(or: Deployments → latest Production → ⋯ → Redeploy → UNCHECK "Use existing Build Cache" → Redeploy.)*
3. Verify in a private window: `https://pdufa.bio/` (no `?query`) shows the live tape, **not** "Coming soon."

### Step 4 — detach the apex from the OLD project  🔴 LAUNCH BLOCKER #2
1. Vercel → the **old `pdufa-bio`** project (the per-drug "99%→APPROVED" one).
2. **Settings → Domains →** remove `pdufa.bio` and `www.pdufa.bio`.
3. Delete that project (or set its deployments to noindex) so a rollback can't put the old product back on the apex.

### Step 5 — Stripe (Pro payments) — full detail in `STRIPE_SETUP.md`
1. Sign in to Stripe → stay in **Test mode**.
2. **Products →** add **"pdufa.bio Pro"**, recurring **$29/month** → copy the **Price ID** (`price_…`).
3. **Developers → API keys →** copy the **Secret key** (`sk_test_…`).
4. In your Vercel project → **Settings → Environment Variables**, add:
   - `STRIPE_SECRET_KEY = sk_test_…`
   - `STRIPE_PRO_PRICE_ID = price_…`
5. Add `"stripe": "^16"` to the project's `package.json` dependencies.
6. *(after the deploy)* **Developers → Webhooks → Add endpoint →** `https://pdufa.bio/api/stripe-webhook` → events `checkout.session.completed`, `customer.subscription.created`, `…updated`, `…deleted` → copy the **signing secret** (`whsec_…`) → add `STRIPE_WEBHOOK_SECRET` to Vercel env → redeploy.
7. **Test:** `/pricing` → Start Pro → card `4242 4242 4242 4242`, any future date/CVC → lands on `/app?checkout=success`.
8. **Go live:** flip Stripe to **Live mode**, recreate the product + webhook there, swap the env vars to live keys, redeploy.

### Step 6 — hand off to me
Message me **"deploy"** once Steps 2–4 are done → I push `pdufa_site_src/` to Vercel (preview → promote).
Also send me the **production gate password** → I'll wire the `/app` + `/today` bug fixes + the Stripe gate-unlock and re-encrypt/deploy those.

### Step 7 — verify live
1. `https://pdufa.bio/` → tape, no "Coming soon."
2. `/pricing`, `/coverage`, `/readouts`, `/condition/cancer` → all load.
3. `/app` + `/today` on your phone → hero cards fixed, modals show a real "—", header reads "Snapshot."
4. Stripe test purchase unlocks Pro.

---

## What I do (no action from you)
- Deploy `pdufa_site_src/` to Vercel after Steps 2–4.
- Re-encrypt + deploy `/app`/`/today` with the fixes (needs the gate password, Step 6).
- Wire the `/app` gate to `/api/verify-access` so paying = access (needs the Stripe keys live).

## Critical path to 07/01
Step 2 (1 min) → Steps 3+4 (Vercel, ~15 min) → tell me → I deploy. Stripe (Step 5) can finish in parallel
and flip live any time after. The two red blockers are the only hard gate.
