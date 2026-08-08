# Stripe setup — pdufa.bio Pro (Free + Pro, $29/mo)

Architecture (all built, env-driven — no code changes needed to go live):
- **Pricing page** → `pricing_pro.html` (deploy as `/pricing`). "Start Pro" POSTs to the Checkout API.
- **`/api/create-checkout-session`** → creates a Stripe Checkout subscription session, returns the URL.
- **`/api/stripe-webhook`** → verifies the signature, records Pro status on subscription events.
- **`/api/verify-access?email=`** → returns `{pro:true|false}` by checking the live Stripe subscription. The `/app` gate calls this to unlock Pro (instead of a shared password).

You only add a Stripe account + keys. **I can't create the account or enter card/bank/API keys for you** — those are yours to set in Stripe + Vercel.

## Steps (do it all in TEST mode first)
1. **Create a Stripe account** (or use your existing) → stay in **Test mode** (toggle, top-right).
2. **Product + price:** Products → Add product → name **"pdufa.bio Pro"**, recurring **$29 / month** → save → copy the **Price ID** (`price_…`).
3. **API keys:** Developers → API keys → copy **Secret key** (`sk_test_…`) and **Publishable key** (`pk_test_…`).
4. **Add the dependency:** ensure `stripe` is in the project's `package.json` dependencies (Vercel installs it on build):
   `"dependencies": { "stripe": "^16" }`
5. **Vercel env vars** (Project → Settings → Environment Variables):
   - `STRIPE_SECRET_KEY` = `sk_test_…`
   - `STRIPE_PRO_PRICE_ID` = `price_…`
   - `STRIPE_WEBHOOK_SECRET` = *(filled in step 6)*
6. **Webhook:** Stripe → Developers → Webhooks → Add endpoint → URL **`https://pdufa.bio/api/stripe-webhook`**, events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted` → copy the **Signing secret** (`whsec_…`) → set `STRIPE_WEBHOOK_SECRET` → redeploy.
7. **Deploy** the pricing page as `/pricing` and the three `api/*.js` files (they're in `pdufa_site_src/api/`).
8. **Test:** open `/pricing` → Start Pro → pay with test card **4242 4242 4242 4242**, any future date / any CVC → you land on `/app?checkout=success`. Confirm the webhook shows `200` in Stripe, and `GET /api/verify-access?email=<the email you used>` returns `{"pro":true}`.
9. **Go live:** flip Stripe to **Live mode**, recreate the product/price + webhook there, swap the env vars to the **live** values (`sk_live_…`, live `price_…`, live `whsec_…`), redeploy.

## Persistence (optional but recommended)
`verify-access` already works straight off Stripe (no database needed). For faster checks / an allow-list, add **Vercel KV** (or Upstash Redis) and uncomment the `kv.set(...)` line in `stripe-webhook.js` + read it in `verify-access.js`.

## Hardening before heavy promotion
- **Email proof:** `verify-access` trusts the email typed in. Add a one-time email code / magic link so the caller proves they own the address before unlock. (Email alone is fine for a soft beta launch; add this before scaling.)
- **Gate integration:** wire the `/app` + `/today` gate to call `/api/verify-access` (and unlock on `pro:true`) instead of the shared beta password. Source is in `pdufa_bio_preview/pdufa_app.html` — I can make that edit when you're ready (it's the last integration step).
- **Customer portal:** enable Stripe Billing customer portal so subscribers can manage/cancel themselves; link it from `/app`.

## Files
- `pricing_pro.html` → deploy to `/pricing`
- `pdufa_site_src/api/create-checkout-session.js`
- `pdufa_site_src/api/stripe-webhook.js`
- `pdufa_site_src/api/verify-access.js`
