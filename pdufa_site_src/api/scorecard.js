// pdufa.bio — returns the rolling call scorecard (how often HIGH-ODDS calls continued to midday).
// Read-only; built by /api/log after each close. Educational only — not investment advice.
export default async function handler(req, res) {
  const KVURL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const KVTOK = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  let sc = null;
  try {
    const { createClient } = await import('@vercel/kv');
    if (KVURL && KVTOK) { const kv = createClient({ url: KVURL, token: KVTOK }); sc = await kv.get('scorecard'); }
  } catch (e) { /* dep missing or not yet populated */ }
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate=3600');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.status(200).json({
    scorecard: sc,
    note: sc ? 'Reconstructed from intraday (open→midday); survivorship-biased; educational only.'
             : 'Scorecard populates after the daily logger runs (needs a Vercel KV store connected).',
  });
}
