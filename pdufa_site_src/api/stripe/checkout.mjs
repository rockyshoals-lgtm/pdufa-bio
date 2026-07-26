import { stripe, stripeReady, PRICES } from '../_stripe.mjs';
import crypto from 'node:crypto';

const SITE = 'https://www.pdufa.bio';
export default async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', SITE);
  res.setHeader('Cache-Control', 'no-store');
  const rid = 'req_' + crypto.randomUUID().slice(0, 18);
  const fail = (code, msg, status = 400) =>
    res.status(status).json({ error: { code, message: msg, request_id: rid } });

  if (req.method === 'OPTIONS') return res.status(204).end();

  // ---- MASTER KILL SWITCH -------------------------------------------------
  // Pro is not launched. The checkout URL is public and Stripe is in LIVE mode, so hiding the
  // button is not enough — a real card would be charged into a half-finished flow. Gate it HERE.
  // Flip on with a single env var (BILLING_LIVE=1) when the paywall is 100%. No code change.
  if (process.env.BILLING_LIVE !== '1') {
    if (req.method === 'GET') { res.writeHead(303, { Location: '/pricing?soon=1' }); return res.end(); }
    return res.status(503).json({
      error: {
        code: 'not_launched',
        message: 'Pro is not available yet. The free API and the full calendar stay free — see /pricing.',
        request_id: rid,
      },
    });
  }
  // -------------------------------------------------------------------------

  if (!stripeReady()) return fail('unconfigured', 'Billing is not configured yet.', 503);

  const plan = String((req.query && req.query.plan) || (req.body && req.body.plan) || '');
  const p = PRICES[plan];
  if (!p) return fail('invalid_param', `Unknown plan "${plan}". Valid: ${Object.keys(PRICES).join(', ')}`);
  if (!p.id) return fail('unconfigured', `No Stripe price ID configured for "${plan}". Set STRIPE_PRICE_${plan.toUpperCase()} in the environment.`, 503);

  try {
    const session = await stripe('checkout/sessions', {
      mode: p.mode,
      line_items: [{ price: p.id, quantity: 1 }],
      success_url: `${SITE}/pricing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${SITE}/pricing?cancelled=1`,
      allow_promotion_codes: true,
      client_reference_id: rid,
      metadata: { plan, tier: p.tier || '', credits: String(p.credits || 0) },
      ...(p.mode === 'subscription'
        ? { subscription_data: { metadata: { plan, tier: p.tier } } }
        : { payment_intent_data: { metadata: { plan, credits: String(p.credits) } } }),
    });
    // GET from a link -> redirect; POST from fetch -> JSON
    if (req.method === 'GET') { res.writeHead(303, { Location: session.url }); return res.end(); }
    return res.status(200).json({ url: session.url, id: session.id, request_id: rid });
  } catch (e) {
    return fail('stripe_error', e.message || 'Could not start checkout.', 502);
  }
};
