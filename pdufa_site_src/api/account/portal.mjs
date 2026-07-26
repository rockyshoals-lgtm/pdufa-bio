import { session } from '../_session.mjs';
import { stripe, stripeReady } from '../_stripe.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const s = session(req);
  if (!s) { res.writeHead(303, { Location: '/login' }); return res.end(); }
  if (!stripeReady()) return res.status(503).json({ error: { code: 'unconfigured' } });
  try {
    // Stripe-hosted portal: update card, view invoices, cancel. We never touch payment details.
    const p = await stripe('billing_portal/sessions', {
      customer: s.customer, return_url: 'https://www.pdufa.bio/account',
    });
    res.writeHead(303, { Location: p.url });
    return res.end();
  } catch (e) {
    return res.status(502).json({ error: { code: 'portal_error', message: e.message } });
  }
};
