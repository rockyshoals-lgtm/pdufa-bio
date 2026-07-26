import { session } from '../_session.mjs';
import { kvGet, kv, kvSet, kvJson, kvReady, hashKey, newApiKey } from '../_stripe.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).json({ error: { code: 'method_not_allowed' } });
  const s = session(req);
  if (!s) return res.status(401).json({ error: { code: 'not_signed_in' } });
  if (!kvReady()) return res.status(503).json({ error: { code: 'unconfigured' } });

  const old = await kvGet('cust:' + s.customer);
  const rec = old ? await kvJson('key:' + hashKey(old)) : null;
  if (!rec) return res.status(404).json({ error: { code: 'not_found', message: 'No key on this account.' } });

  const key = newApiKey();
  await kvSet('key:' + hashKey(key), JSON.stringify({ ...rec, rotated: new Date().toISOString() }));
  // carry credits across, then retire the old key
  const credits = Number(await kvGet('credits:' + hashKey(old)).catch(() => 0)) || 0;
  if (credits) await kvSet('credits:' + hashKey(key), String(credits));
  await kv('DEL', 'key:' + hashKey(old));
  await kv('DEL', 'credits:' + hashKey(old));
  await kvSet('cust:' + s.customer, key);
  res.status(200).json({ api_key: key, rotated: true });
};
