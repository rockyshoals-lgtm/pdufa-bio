import { stripe, stripeReady, kvSet, kvReady } from '../_stripe.mjs';
import { sign } from '../_session.mjs';
import crypto from 'node:crypto';

const SITE = 'https://www.pdufa.bio';
const RESEND = process.env.RESEND_API_KEY;

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Access-Control-Allow-Origin', SITE);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: { code: 'method_not_allowed' } });

  let email = '';
  try { email = String((req.body && req.body.email) || (req.query && req.query.email) || '').trim().toLowerCase(); }
  catch {}
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
    return res.status(400).json({ error: { code: 'invalid_param', message: 'Enter a valid email address.' } });

  if (!stripeReady() || !kvReady())
    return res.status(503).json({ error: { code: 'unconfigured', message: 'Accounts are not available yet.' } });

  // Always answer the same way — never reveal whether an email has an account.
  const generic = { ok: true, message: 'If that email has a pdufa.bio subscription, a sign-in link is on its way.' };

  try {
    const found = await stripe('customers?email=' + encodeURIComponent(email) + '&limit=1', null, 'GET');
    const cust = found?.data?.[0];
    if (!cust) return res.status(200).json(generic);

    const token = crypto.randomBytes(32).toString('base64url');
    await kvSet('magic:' + token, JSON.stringify({ email, customer: cust.id }), 900);   // 15 min
    const link = `${SITE}/api/auth/verify?token=${token}`;

    if (!RESEND) {
      // No mail provider configured — fail loudly in logs, generically to the user.
      console.error('RESEND_API_KEY unset; magic link for', email, '->', link);
      return res.status(503).json({ error: { code: 'unconfigured',
        message: 'Email sign-in is not configured yet. Please contact support@pdufa.bio and we will send your key.' } });
    }
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + RESEND, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'pdufa.bio <noreply@pdufa.bio>',
        to: [email],
        subject: 'Your pdufa.bio sign-in link',
        html: `<p>Click to sign in to your pdufa.bio account:</p>
               <p><a href="${link}" style="background:#f0c86a;color:#081426;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700">Sign in</a></p>
               <p style="color:#667">This link expires in 15 minutes and can be used once. If you didn't request it, ignore this email.</p>`,
      }),
      signal: AbortSignal.timeout(8000),
    });
    if (!r.ok) console.error('resend_failed', await r.text());
    return res.status(200).json(generic);
  } catch (e) {
    console.error('auth_request_error', e.message);
    return res.status(200).json(generic);      // don't leak existence on error either
  }
};
