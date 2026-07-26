import { kvReady, kv, kvSet } from './_stripe.mjs';
import crypto from 'node:crypto';

/** Pro launch waitlist. No card, no Stripe — just an email so the interest isn't wasted
 *  while the paywall is finished. */
export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Access-Control-Allow-Origin', 'https://www.pdufa.bio');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: { code: 'method_not_allowed' } });

  let email = '', interest = 'pro';
  try {
    const b = req.body || {};
    email = String(b.email || '').trim().toLowerCase();
    interest = String(b.interest || 'pro').slice(0, 24);
  } catch {}
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
    return res.status(400).json({ error: { code: 'invalid_param', message: 'Enter a valid email address.' } });

  // NEVER return ok:true unless the address is actually in durable storage.
  //
  // The previous version logged the email to console and returned 200 when KV was down.
  // That does not "avoid losing the lead" — it loses the lead AND tells the person they're
  // on the list. A function log is not a database; it rotates away. During a coming-soon
  // window, a silently-dropped signup is unrecoverable, so we fail LOUD and give the person
  // a route that actually works.
  const FALLBACK = 'pro@pdufa.bio';

  if (!kvReady()) {
    console.error('waitlist_no_store', { interest });   // no email in the log line
    return res.status(503).json({
      error: {
        code: 'store_unavailable',
        message: `We couldn't save your address just now. Email ${FALLBACK} and we'll add you by hand — sorry about that.`,
        contact: FALLBACK,
      },
    });
  }

  try {
    const id = crypto.createHash('sha256').update(email).digest('hex').slice(0, 20);
    await kvSet('wait:' + id, JSON.stringify({ email, interest, at: new Date().toISOString() }));
    await kv('SADD', 'waitlist', email);                 // set -> dedupes automatically
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error('waitlist_error', e.message);         // never log the address itself
    return res.status(503).json({
      error: {
        code: 'store_unavailable',
        message: `We couldn't save your address just now. Email ${FALLBACK} and we'll add you by hand — sorry about that.`,
        contact: FALLBACK,
      },
    });
  }
};
