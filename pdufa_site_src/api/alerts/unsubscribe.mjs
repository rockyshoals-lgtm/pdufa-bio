// DRAFT (not live): /api/alerts/unsubscribe?id=…&t=…
// POST = the actual unsubscribe. Used by the mail app's own button (RFC 8058,
//        List-Unsubscribe-Post) and by the one button on /alerts?unsub=…
// GET  = the link in the email footer. It only shows the one-button page, because mail
//        security scanners open every link in an email and would otherwise unsubscribe
//        people who never clicked.
// The record is deleted outright, not flagged, so nothing about the person is kept.
import { SITE, checkUnsub, kv } from '../_alerts.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const q = req.query || {};
  const id = String(q.id || ''), t = String(q.t || '');
  const ok = /^[0-9a-f]{24}$/.test(id) && checkUnsub(id, t);
  if (req.method === 'GET') {
    res.setHeader('Location', ok ? `${SITE}/alerts?unsub=${id}&t=${encodeURIComponent(t)}` : `${SITE}/alerts?s=badlink`);
    return res.status(302).end();
  }
  if (req.method !== 'POST') return res.status(405).end();
  if (!ok) return res.status(400).json({ error: { code: 'bad_link' } });
  try {
    await kv('SREM', 'alerts:list', id);
    await kv('DEL', 'alerts:sub:' + id);
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error('alerts_unsub_error', e.message);
    return res.status(503).json({ error: { code: 'store_unavailable' } });
  }
};
