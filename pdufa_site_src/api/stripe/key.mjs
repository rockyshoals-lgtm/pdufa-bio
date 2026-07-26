import { kvGet, kvReady, kv } from '../_stripe.mjs';
// Reveal the issued API key ONCE, keyed by the Checkout session id, then burn it.
export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Access-Control-Allow-Origin', 'https://www.pdufa.bio');
  const sid = req.query && req.query.session_id;
  if (!sid || !/^cs_[A-Za-z0-9_]+$/.test(String(sid)))
    return res.status(400).json({ error: { code: 'invalid_param', message: 'Missing or malformed session_id.' } });
  if (!kvReady())
    return res.status(503).json({ error: { code: 'unconfigured', message: 'Key store unavailable.' } });
  try {
    const key = await kvGet('sess:' + sid);
    if (!key) return res.status(404).json({ error: { code: 'not_found',
      message: 'No key for that session. It may have already been revealed, or the payment is still processing — refresh in a few seconds.' } });
    await kv('DEL', 'sess:' + sid);          // show once, then burn
    return res.status(200).json({ api_key: key });
  } catch {
    return res.status(503).json({ error: { code: 'unavailable', message: 'Could not retrieve the key.' } });
  }
};
