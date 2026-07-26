import crypto from 'node:crypto';

/* ---------- KV (Vercel KV / Upstash REST) ---------- */
const KV_URL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const KV_TOK = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
export const kvReady = () => !!(KV_URL && KV_TOK);

export async function kv(...cmd) {
  if (!kvReady()) throw new Error('kv_unconfigured');
  const r = await fetch(KV_URL, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + KV_TOK, 'Content-Type': 'application/json' },
    body: JSON.stringify(cmd),
    signal: AbortSignal.timeout(2500),
  });
  if (!r.ok) throw new Error('kv_' + r.status);
  return (await r.json()).result;
}
export const kvGet  = k => kv('GET', k);
export const kvSet  = (k, v, ttl) => ttl ? kv('SET', k, v, 'EX', String(ttl)) : kv('SET', k, v);
export const kvJson = async k => { const v = await kvGet(k); try { return v ? JSON.parse(v) : null; } catch { return null; } };
export const kvIncrBy = (k, n) => kv('INCRBY', k, String(n));
/** SET key val NX -> returns null if it already existed. The idempotency primitive. */
export const kvSetNX = (k, v, ttl) => kv('SET', k, v, 'NX', 'EX', String(ttl));

/* ---------- Stripe REST (no SDK) ---------- */
const SK = process.env.STRIPE_SECRET_KEY;
export const stripeReady = () => !!SK;

const form = (obj, pre = '', out = []) => {
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null) continue;
    const key = pre ? `${pre}[${k}]` : k;
    if (typeof v === 'object' && !Array.isArray(v)) form(v, key, out);
    else if (Array.isArray(v)) v.forEach((x, i) => {
      if (typeof x === 'object') form(x, `${key}[${i}]`, out);
      else out.push([`${key}[${i}]`, String(x)]);
    });
    else out.push([key, String(v)]);
  }
  return out;
};
export async function stripe(path, body, method = 'POST') {
  if (!SK) throw new Error('stripe_unconfigured');
  const opts = {
    method,
    headers: { Authorization: 'Bearer ' + SK, 'Content-Type': 'application/x-www-form-urlencoded' },
    signal: AbortSignal.timeout(8000),
  };
  if (body && method !== 'GET') opts.body = new URLSearchParams(form(body)).toString();
  const r = await fetch('https://api.stripe.com/v1/' + path, opts);
  const j = await r.json();
  if (!r.ok) throw Object.assign(new Error(j?.error?.message || 'stripe_error'), { stripe: j?.error, status: r.status });
  return j;
}

/* ---------- Webhook signature (manual, per Stripe docs) ---------- */
export function verifyStripeSig(rawBody, header, secret, toleranceSec = 300) {
  if (!header || !secret) return false;
  const parts = Object.fromEntries(
    header.split(',').map(p => p.split('=')).filter(p => p.length === 2).map(([k, v]) => [k.trim(), v.trim()])
  );
  const t = parts.t;
  if (!t) return false;
  // replay defence
  if (Math.abs(Math.floor(Date.now() / 1000) - Number(t)) > toleranceSec) return false;
  const expected = crypto.createHmac('sha256', secret)
    .update(t + '.' + rawBody.toString('utf8'), 'utf8').digest('hex');
  // only the v1 scheme; ignore v0 (downgrade defence)
  const given = header.split(',').map(p => p.trim()).filter(p => p.startsWith('v1=')).map(p => p.slice(3));
  const exp = Buffer.from(expected, 'hex');
  return given.some(g => {
    const b = Buffer.from(g, 'hex');
    return b.length === exp.length && crypto.timingSafeEqual(b, exp);
  });
}
export async function rawBody(req) {
  if (Buffer.isBuffer(req.body)) return req.body;
  if (typeof req.body === 'string') return Buffer.from(req.body);
  const chunks = [];
  for await (const c of req) chunks.push(typeof c === 'string' ? Buffer.from(c) : c);
  return Buffer.concat(chunks);
}

/* ---------- API keys / entitlements ---------- */
export const hashKey = k => crypto.createHash('sha256').update(k).digest('hex');
export const newApiKey = () => 'pk_live_' + crypto.randomBytes(24).toString('base64url');

/** Stored hashed — the plaintext key is shown to the user exactly once. */
export async function issueKey({ tier, customer, subscription, email }) {
  const key = newApiKey();
  const rec = { tier, customer: customer || null, subscription: subscription || null,
                email: email || null, status: 'active', created: new Date().toISOString() };
  await kvSet('key:' + hashKey(key), JSON.stringify(rec));
  if (customer) await kvSet('cust:' + customer, key);          // so renewals/cancels find the key
  return key;
}
export const lookupKey = async plaintext => kvJson('key:' + hashKey(plaintext));
export async function setKeyStatus(customer, patch) {
  const key = await kvGet('cust:' + customer);
  if (!key) return null;
  const rec = await kvJson('key:' + hashKey(key));
  if (!rec) return null;
  const next = { ...rec, ...patch };
  await kvSet('key:' + hashKey(key), JSON.stringify(next));
  return next;
}
export async function addCredits(customer, n, idemKey) {
  const key = await kvGet('cust:' + customer);
  if (!key) return null;
  if (idemKey) {
    const first = await kvSetNX('idem:' + idemKey, '1', 60 * 60 * 24 * 30);
    if (first === null) return 'duplicate';                     // already credited
  }
  return kvIncrBy('credits:' + hashKey(key), n);
}

/* ---------- price catalogue (IDs come from env; never hardcoded) ---------- */
export const PRICES = {
  pro_monthly:  { id: process.env.STRIPE_PRICE_PRO_MONTHLY,  mode: 'subscription', tier: 'pro' },
  pro_annual:   { id: process.env.STRIPE_PRICE_PRO_ANNUAL,   mode: 'subscription', tier: 'pro' },
  quant_monthly:{ id: process.env.STRIPE_PRICE_QUANT_MONTHLY,mode: 'subscription', tier: 'quant' },
  credits_25k:  { id: process.env.STRIPE_PRICE_CREDITS_25K,  mode: 'payment', credits: 25000 },
  credits_100k: { id: process.env.STRIPE_PRICE_CREDITS_100K, mode: 'payment', credits: 100000 },
  credits_300k: { id: process.env.STRIPE_PRICE_CREDITS_300K, mode: 'payment', credits: 300000 },
};
