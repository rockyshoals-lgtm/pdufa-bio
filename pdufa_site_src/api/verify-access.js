// Vercel serverless function — GET /api/verify-access?email=<addr>  (or ?key=<beta unlock>)
// Issues a signed, HttpOnly `pb_pro` session cookie when the caller is a paying Pro
// subscriber (Stripe) OR presents the temporary beta-unlock key. /api/data reads that
// cookie to decide free-vs-pro payload (only when PRO_GATING_ENABLED=1).
//
// Env: PRO_SESSION_SECRET (required to mint cookies), STRIPE_SECRET_KEY (Stripe path),
//      PRO_BETA_UNLOCK (optional temporary pre-Stripe bridge — a shared secret).
// SECURITY: email alone is a weak credential; gate behind a magic-link / one-time code
// before scaling (see STRIPE_SETUP.md "Hardening"). The beta bridge is pre-launch only.
const crypto = require('crypto');

function _sign(payload, sec){
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = crypto.createHmac('sha256', sec).update(body).digest('base64url');
  return body + '.' + sig;
}
function _setPro(res, email){
  const sec = process.env.PRO_SESSION_SECRET; if(!sec) return false;
  const tok = _sign({ email: email || '', exp: Date.now() + 24*60*60*1000 }, sec);
  res.setHeader('Set-Cookie',
    `pb_pro=${encodeURIComponent(tok)}; Path=/; Max-Age=86400; HttpOnly; Secure; SameSite=Lax; Domain=.pdufa.bio`);
  return true;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const email = (req.query.email || '').toString().trim().toLowerCase();
  const key   = (req.query.key || req.query.pass || '').toString();

  // Temporary pre-Stripe bridge: unlock Pro with the shared beta key.
  if (process.env.PRO_BETA_UNLOCK && key && key === process.env.PRO_BETA_UNLOCK) {
    const ok = _setPro(res, email || 'beta');
    res.status(200).json({ pro: true, via: 'beta', cookie_set: ok });
    return;
  }

  // Stripe path (active once STRIPE_SECRET_KEY is set).
  if (!process.env.STRIPE_SECRET_KEY) { res.status(200).json({ pro: false, reason: 'stripe-not-configured' }); return; }
  if (!email) { res.status(400).json({ error: 'email required' }); return; }
  try {
    const Stripe = require('stripe');
    const stripe = Stripe(process.env.STRIPE_SECRET_KEY);
    const customers = await stripe.customers.list({ email, limit: 10 });
    let pro = false;
    for (const c of customers.data) {
      const subs = await stripe.subscriptions.list({ customer: c.id, status: 'all', limit: 25 });
      if (subs.data.some(s => ['active', 'trialing', 'past_due'].includes(s.status))) { pro = true; break; }
    }
    const ok = pro ? _setPro(res, email) : false;
    res.status(200).json({ pro, cookie_set: ok });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
