// Vercel serverless function  —  POST /api/stripe-webhook
// Register this URL as a Stripe webhook endpoint. Verifies the signature and records each
// subscriber's Pro status on subscription lifecycle events.
// Requires env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
// Optional (recommended) env for persistence: a Vercel KV / Upstash Redis binding.
//
// IMPORTANT: raw body required for signature verification, so body parsing is disabled.
const Stripe = require('stripe');

module.exports.config = { api: { bodyParser: false } };

async function rawBody(readable) {
  const chunks = [];
  for await (const chunk of readable) chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  return Buffer.concat(chunks);
}

// --- swap this for real persistence (Vercel KV, Upstash, Supabase, etc.) ---
async function setProStatus(email, active) {
  if (!email) return;
  // Example with @vercel/kv (uncomment after adding the KV integration):
  //   const { kv } = require('@vercel/kv');
  //   await kv.set('pro:' + email.toLowerCase(), active ? '1' : '0');
  console.log('[stripe-webhook] pro status', email.toLowerCase(), active);
}

module.exports = async (req, res) => {
  if (!process.env.STRIPE_SECRET_KEY || !process.env.STRIPE_WEBHOOK_SECRET) {
    res.status(500).send('Stripe not configured'); return;
  }
  const stripe = Stripe(process.env.STRIPE_SECRET_KEY);
  let event;
  try {
    const buf = await rawBody(req);
    event = stripe.webhooks.constructEvent(buf, req.headers['stripe-signature'], process.env.STRIPE_WEBHOOK_SECRET);
  } catch (e) {
    res.status(400).send(`Webhook signature verification failed: ${e.message}`); return;
  }
  try {
    const o = event.data.object;
    switch (event.type) {
      case 'checkout.session.completed':
        await setProStatus(o.customer_details && o.customer_details.email, true);
        break;
      case 'customer.subscription.created':
      case 'customer.subscription.updated': {
        const active = ['active', 'trialing', 'past_due'].includes(o.status);
        let email = null;
        try { const c = await stripe.customers.retrieve(o.customer); email = c && c.email; } catch (_) {}
        await setProStatus(email, active);
        break;
      }
      case 'customer.subscription.deleted': {
        let email = null;
        try { const c = await stripe.customers.retrieve(o.customer); email = c && c.email; } catch (_) {}
        await setProStatus(email, false);
        break;
      }
      default: break;
    }
    res.status(200).json({ received: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
