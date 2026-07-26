// Vercel serverless function  —  POST /api/create-checkout-session
// Creates a Stripe Checkout (subscription) session for pdufa.bio Pro and returns its URL.
// Requires env: STRIPE_SECRET_KEY, STRIPE_PRO_PRICE_ID
//
//   const r = await fetch('/api/create-checkout-session', {method:'POST'});
//   const {url} = await r.json(); location.href = url;
//
const Stripe = require('stripe');

module.exports = async (req, res) => {
  if (req.method !== 'POST') { res.status(405).json({ error: 'POST only' }); return; }
  if (!process.env.STRIPE_SECRET_KEY || !process.env.STRIPE_PRO_PRICE_ID) {
    res.status(500).json({ error: 'Stripe not configured (set STRIPE_SECRET_KEY + STRIPE_PRO_PRICE_ID)' }); return;
  }
  const stripe = Stripe(process.env.STRIPE_SECRET_KEY);
  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      line_items: [{ price: process.env.STRIPE_PRO_PRICE_ID, quantity: 1 }],
      allow_promotion_codes: true,
      billing_address_collection: 'auto',
      // Stripe collects the email; the webhook + verify-access tie access to it.
      success_url: 'https://pdufa.bio/app?checkout=success&session_id={CHECKOUT_SESSION_ID}',
      cancel_url:  'https://pdufa.bio/pricing?checkout=cancel',
      // 1 month FREE, then the annual plan ($10/mo billed yearly = $120/yr, set in the Stripe price).
      subscription_data: {
        trial_period_days: 30,
        metadata: { product: 'pdufa_bio_pro' },
      },
    });
    res.setHeader('Cache-Control', 'no-store');
    res.status(200).json({ url: session.url });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
