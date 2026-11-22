// DRAFT (not live): free pdufa.bio email alerts — shared helpers.
//
// Nothing here sends or stores anything unless ALERTS_LIVE=1 is set in Vercel. With the flag
// off, every alerts endpoint answers "not open yet" and touches neither KV nor Resend.
//
// Design:
//  - Double opt-in. A sign-up only creates a pending record (48h TTL) and sends one
//    confirmation email. Nobody is on the list until they click the link.
//  - The confirmed list lives in Vercel KV (the same store the site already uses), so the
//    list belongs to pdufa.bio, not to an email vendor.
//  - Mail goes out through Resend, which the site already uses for sign-in links
//    (RESEND_API_KEY). Sender: alerts@pdufa.bio once the domain is verified in Resend.
//  - We store the email address, chosen frequency, sign-up and confirm times. No IP, no
//    name, no tracking pixels, no click tracking.
import crypto from 'node:crypto';
import { kvReady, kv, kvSet, kvGet } from './_stripe.mjs';

export const SITE = 'https://www.pdufa.bio';
export const LIVE = process.env.ALERTS_LIVE === '1';
export const RESEND = process.env.RESEND_API_KEY || '';
export const FROM = process.env.ALERTS_FROM || 'pdufa.bio alerts <alerts@pdufa.bio>';
const SECRET = process.env.ALERTS_SECRET || '';

export const ready = () => LIVE && kvReady() && !!RESEND && SECRET.length >= 32;

export const normEmail = e => String(e || '').trim().toLowerCase();
export const validEmail = e => e.length <= 254 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e);
export const emailId = e => crypto.createHash('sha256').update(e).digest('hex').slice(0, 24);

// Unsubscribe tokens never expire and need no database lookup: HMAC(email id).
export const unsubToken = id => crypto.createHmac('sha256', SECRET).update('unsub:' + id).digest('base64url');
export function checkUnsub(id, tok) {
  if (!id || !tok || SECRET.length < 32) return false;
  const a = Buffer.from(String(tok)), b = Buffer.from(unsubToken(id));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
export const unsubUrl = id => `${SITE}/api/alerts/unsubscribe?id=${id}&t=${unsubToken(id)}`;

export const FREQS = ['weekly', 'decisions'];   // weekly digest; or decision-day emails too

export async function sendMail({ to, subject, html, text, headers }) {
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + RESEND, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: FROM, to: [to], subject, html, text, headers }),
    signal: AbortSignal.timeout(8000),
  });
  if (!r.ok) throw new Error('resend_' + r.status);
}

export { kv, kvSet, kvGet };

export const notOpen = res => res.status(503).json({
  error: { code: 'alerts_not_open', message: 'Free alerts are not open yet. Check back soon.' },
});
