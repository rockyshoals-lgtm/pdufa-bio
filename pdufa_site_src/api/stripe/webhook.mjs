import { rawBody, verifyStripeSig, kvReady, kvSetNX, kvSet, kvGet, kvJson,
         issueKey, setKeyStatus, addCredits, hashKey, stripe } from '../_stripe.mjs';

// Stripe signature verification needs the UNPARSED body.
export const config = { api: { bodyParser: false } };

const WHSEC = process.env.STRIPE_WEBHOOK_SECRET;

export default async (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'method_not_allowed' });
  res.setHeader('Cache-Control', 'no-store');

  let buf;
  try { buf = await rawBody(req); } catch { return res.status(400).json({ error: 'unreadable_body' }); }

  const sig = req.headers['stripe-signature'];
  if (!WHSEC || !verifyStripeSig(buf, sig, WHSEC)) {
    return res.status(400).json({ error: 'signature_verification_failed' });
  }

  let ev;
  try { ev = JSON.parse(buf.toString('utf8')); } catch { return res.status(400).json({ error: 'invalid_json' }); }

  // ACK fast (Stripe times out at ~20s and retries); then do the work.
  res.status(200).json({ received: true, id: ev.id });

  try { await handle(ev); }
  catch (e) { console.error('webhook_handler_error', ev?.id, ev?.type, e?.message); }
};

async function handle(ev) {
  if (!kvReady()) { console.error('kv_unconfigured; cannot persist entitlement for', ev.id); return; }

  // at-least-once delivery -> event.id is the idempotency key
  const first = await kvSetNX('evt:' + ev.id, '1', 60 * 60 * 24 * 30);
  if (first === null) return;                       // already processed

  const o = ev.data?.object || {};
  switch (ev.type) {

    case 'checkout.session.completed': {
      const md = o.metadata || {};
      if (o.mode === 'subscription') {
        const key = await issueKey({
          tier: md.tier || 'pro', customer: o.customer,
          subscription: o.subscription, email: o.customer_details?.email,
        });
        // let the success page reveal the key exactly once, keyed by session id
        await kvSet('sess:' + o.id, key, 60 * 60 * 24);
      } else if (o.mode === 'payment') {
        const n = Number(md.credits || 0);
        if (n > 0) {
          // ensure the customer has a key even if they only bought credits
          let k = o.customer ? await kvGet('cust:' + o.customer) : null;
          if (!k && o.customer) {
            k = await issueKey({ tier: 'free', customer: o.customer, email: o.customer_details?.email });
          }
          await addCredits(o.customer, n, o.payment_intent || o.id);
          if (k) await kvSet('sess:' + o.id, k, 60 * 60 * 24);
        }
      }
      break;
    }

    // Renewals do NOT fire checkout.session.completed — this is what keeps Pro alive.
    case 'invoice.paid': {
      if (o.customer) await setKeyStatus(o.customer, { status: 'active', last_paid: new Date().toISOString() });
      break;
    }

    case 'invoice.payment_failed': {
      // warn, don't revoke — Stripe will retry (dunning)
      if (o.customer) await setKeyStatus(o.customer, { status: 'past_due' });
      break;
    }

    case 'customer.subscription.updated': {
      const status = o.status;                       // active|past_due|canceled|unpaid|trialing
      const tier = o.metadata?.tier;
      const patch = { status: status === 'trialing' ? 'active' : status };
      if (tier) patch.tier = tier;
      if (o.cancel_at_period_end) patch.cancel_at_period_end = true;
      if (o.customer) await setKeyStatus(o.customer, patch);
      break;
    }

    case 'customer.subscription.deleted': {
      // Pro ends -> drop to free; Depth fields re-lock automatically
      if (o.customer) await setKeyStatus(o.customer, { status: 'canceled', tier: 'free' });
      break;
    }

    case 'charge.refunded': {
      // claw back credits so a refunded pack doesn't leave free quota behind
      const pi = o.payment_intent;
      if (!pi || !o.customer) break;
      let credits = 0;
      try {
        const p = await stripe('payment_intents/' + pi, null, 'GET');
        credits = Number(p?.metadata?.credits || 0);
      } catch {}
      if (credits > 0) await addCredits(o.customer, -credits, 'refund:' + pi);
      break;
    }
  }
}
