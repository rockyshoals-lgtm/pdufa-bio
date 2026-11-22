// DRAFT (not live): GET /api/alerts/confirm?token=…  — the double opt-in click.
import { SITE, ready, emailId, kv, kvGet, kvSet } from '../_alerts.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const go = s => { res.setHeader('Location', `${SITE}/alerts?s=${s}`); return res.status(302).end(); };
  if (!ready()) return go('closed');
  const token = String((req.query || {}).token || '');
  if (!/^[A-Za-z0-9_-]{30,64}$/.test(token)) return go('expired');
  try {
    const raw = await kvGet('alerts:pending:' + token);
    if (!raw) return go('expired');
    const p = JSON.parse(raw);
    const id = emailId(p.email);
    await kvSet('alerts:sub:' + id, JSON.stringify({ email: p.email, freq: p.freq, signed_up: p.at, confirmed: new Date().toISOString() }));
    await kv('SADD', 'alerts:list', id);
    await kv('DEL', 'alerts:pending:' + token);
    return go('confirmed');
  } catch (e) {
    console.error('alerts_confirm_error', e.message);
    return go('error');
  }
};
