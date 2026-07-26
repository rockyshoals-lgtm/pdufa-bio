import { session } from '../_session.mjs';
import { kvGet, kvJson, kvReady, hashKey, stripe, stripeReady } from '../_stripe.mjs';
import { TIERS } from '../v1/_lib.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const s = session(req);
  if (!s) return res.status(401).json({ error: { code: 'not_signed_in' } });
  if (!kvReady()) return res.status(503).json({ error: { code: 'unconfigured' } });

  const key = await kvGet('cust:' + s.customer);
  const rec = key ? await kvJson('key:' + hashKey(key)) : null;
  const credits = key ? Number(await kvGet('credits:' + hashKey(key)).catch(() => 0)) || 0 : 0;

  // usage this month
  const bucket = new Date().toISOString().slice(0, 7);
  let used = 0;
  try { used = Number(await kvGet(`q:k:${hashKey(key).slice(0,24)}:${bucket}`)) || 0; } catch {}

  let sub = null;
  if (stripeReady() && rec?.subscription) {
    try {
      const x = await stripe('subscriptions/' + rec.subscription, null, 'GET');
      sub = { status: x.status, current_period_end: x.current_period_end,
              cancel_at_period_end: !!x.cancel_at_period_end,
              amount: x.items?.data?.[0]?.price?.unit_amount,
              interval: x.items?.data?.[0]?.price?.recurring?.interval };
    } catch {}
  }
  const tier = rec?.tier || 'free';
  res.status(200).json({
    email: s.email,
    tier,
    status: rec?.status || 'none',
    api_key: key || null,                 // signed-in owner may see their own key
    quota: { limit: TIERS[tier]?.quota ?? 0, used, remaining: Math.max(0, (TIERS[tier]?.quota ?? 0) - used) },
    credits_remaining: credits,
    depth_access: !!TIERS[tier]?.depth,
    subscription: sub,
  });
};
