import { kvGet, kv, kvReady } from '../_stripe.mjs';
import { sign, cookie } from '../_session.mjs';

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const token = req.query && req.query.token;
  const bounce = (q) => { res.writeHead(303, { Location: '/login?' + q }); return res.end(); };
  if (!token || !kvReady()) return bounce('e=invalid');
  try {
    const raw = await kvGet('magic:' + token);
    if (!raw) return bounce('e=expired');
    await kv('DEL', 'magic:' + token);                    // single use
    const { email, customer } = JSON.parse(raw);
    res.setHeader('Set-Cookie', cookie('pd_session', sign({ email, customer }), 60 * 60 * 24 * 30));
    res.writeHead(303, { Location: '/account' });
    return res.end();
  } catch { return bounce('e=invalid'); }
};
