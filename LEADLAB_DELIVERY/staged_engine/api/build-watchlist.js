// pdufa.bio — nightly ADV / watchlist builder.
// Pulls the Unusual Whales stock screener (/api/screener/stocks) for small/micro
// names with their 30-day average volume, and caches a { TICKER: {adv, mcap} }
// map to KV. The pre-market board reads this so it can compute pre-market
// relative-volume — the "move AND volume" confluence that hit +25% intraday
// 91.8% of the time in the LEADLAB study (vs move-alone).
//
// Cron: run ~once after close (e.g. "0 22 * * 1-5"). Auth via CRON_SECRET.
// Reads UW_API_KEY from env — never sent to the browser.
const UW = 'https://api.unusualwhales.com/api/screener/stocks';

async function pull(params, key) {
  const qs = new URLSearchParams(params).toString();
  const r = await fetch(`${UW}?${qs}`, {
    headers: { Authorization: `Bearer ${key}`, Accept: 'application/json' },
    signal: AbortSignal.timeout(12000),
  });
  if (!r.ok) throw new Error(`UW ${r.status}`);
  const j = await r.json();
  return j.data || j.result || j || [];
}

export default async function handler(req, res) {
  // allow Vercel Cron (CRON_SECRET) or manual with the same secret
  const secret = process.env.CRON_SECRET;
  const auth = req.headers.authorization || '';
  if (secret && auth !== `Bearer ${secret}` && req.query?.key !== secret) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  const KEY = process.env.UW_API_KEY;
  res.setHeader('Content-Type', 'application/json');
  if (!KEY) return res.status(500).json({ error: 'no UW_API_KEY' });

  const map = {};
  let pages = 0, err = null;
  try {
    // small/micro, ranked by relative volume; a few pages for breadth
    for (let off = 0; off < 5; off++) {
      const rows = await pull({
        max_marketcap: '3000000000', min_underlying_price: '0.30',
        issue_types: 'Common Stock', order: 'volume', order_direction: 'desc',
        limit: '250', offset: String(off),
      }, KEY);
      if (!rows.length) break;
      pages++;
      for (const r of rows) {
        const adv = Number(r.avg30_volume || r.avg_30_day_volume);
        if (!r.ticker || !adv) continue;
        map[r.ticker] = { adv: Math.round(adv), mcap: Number(r.marketcap) || null };
      }
    }
    const { kv } = await import('@vercel/kv');
    await kv.set('adv_map', map, { ex: 60 * 60 * 36 });   // expire in 36h (refreshed nightly)
    await kv.set('adv_map_built', new Date().toISOString());
  } catch (e) { err = String(e.message || e); }

  res.status(200).json({ built: new Date().toISOString(), names: Object.keys(map).length, pages, err });
}
