// DRAFT (not live): POST /api/alerts/subscribe  { email, freq, consent }
// Creates a pending sign-up and sends one confirmation email. Off unless ALERTS_LIVE=1.
import crypto from 'node:crypto';
import { SITE, ready, notOpen, normEmail, validEmail, emailId, FREQS, sendMail, kv, kvSet, kvGet } from '../_alerts.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Access-Control-Allow-Origin', SITE);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: { code: 'method_not_allowed' } });
  if (!ready()) return notOpen(res);

  const b = req.body || {};
  if (b.website) return res.status(200).json({ ok: true });          // honeypot: bots fill it
  const email = normEmail(b.email);
  const freq = FREQS.includes(b.freq) ? b.freq : 'weekly';
  if (!validEmail(email))
    return res.status(400).json({ error: { code: 'invalid_param', message: 'Enter a valid email address.' } });
  if (b.consent !== true)
    return res.status(400).json({ error: { code: 'consent_required', message: 'Please tick the box to agree to the terms and privacy policy.' } });

  // Same answer whether or not the address is already on the list, so the form can't be
  // used to find out who subscribes.
  const generic = { ok: true, message: 'Check your inbox for a confirmation link. You are not subscribed until you click it.' };
  const id = emailId(email);
  try {
    if (await kv('SISMEMBER', 'alerts:list', id) === 1) return res.status(200).json(generic);

    // At most one confirmation email per address per 10 minutes, 3 per day.
    const n = await kv('INCR', 'alerts:rl:' + id);
    if (n === 1) await kv('EXPIRE', 'alerts:rl:' + id, '86400');
    if (n > 3 || (await kvGet('alerts:rl10:' + id))) return res.status(200).json(generic);
    await kv('SET', 'alerts:rl10:' + id, '1', 'EX', '600');

    const token = crypto.randomBytes(32).toString('base64url');
    await kvSet('alerts:pending:' + token, JSON.stringify({ email, freq, at: new Date().toISOString() }), 172800);
    const link = `${SITE}/api/alerts/confirm?token=${token}`;
    await sendMail({
      to: email,
      subject: 'Confirm your free pdufa.bio alerts',
      text: `Someone (hopefully you) asked to get free FDA calendar alerts from pdufa.bio at this address.\n\nConfirm: ${link}\n\nThe link works for 48 hours. If you didn't ask for this, ignore this email and nothing will happen.\n\npdufa.bio publishes sourced facts only. Not investment advice.`,
      html: `<p>Someone (hopefully you) asked to get free FDA calendar alerts from pdufa.bio at this address.</p>
<p><a href="${link}" style="background:#f0c86a;color:#081426;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700">Confirm my alerts</a></p>
<p style="color:#667">The link works for 48 hours. If you didn't ask for this, ignore this email and nothing will happen.</p>
<p style="color:#667;font-size:12px">pdufa.bio publishes sourced facts only. Not investment advice.</p>`,
    });
    return res.status(200).json(generic);
  } catch (e) {
    console.error('alerts_subscribe_error', e.message);      // never log the address
    return res.status(503).json({ error: { code: 'store_unavailable', message: "We couldn't sign you up just now. Please try again later." } });
  }
};
