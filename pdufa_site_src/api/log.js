// pdufa.bio — daily auto-logger + call scorecard (runs after the close via cron).
//   1) Logs every stock that gained >= 25% today  -> builds the forward "surge" dataset.
//   2) T+1 scoring: scores each PRIOR day's surges once their intraday is available
//      (FMP intraday lags same-day), reconstructing morning signal + open->midday continuation
//      -> rolling "how often did HIGH-ODDS morning setups continue" scorecard.
// Persists to Vercel KV / Upstash (env auto-injected). No-ops gracefully if the store isn't connected.
// Informational and educational only — NOT investment advice.

const FMP = 'https://financialmodelingprep.com/stable';
async function jget(url) {
  try { const r = await fetch(url, { signal: AbortSignal.timeout(9000) }); return r.ok ? await r.json() : null; }
  catch (e) { return null; }
}
function etDate() {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' })
    .formatToParts(new Date()).map(x => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}
const round = (x, d = 1) => x == null ? null : +Number(x).toFixed(d);
const shift = (ymd, days) => { const d = new Date(ymd + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); };

// score one prior day's surges from intraday (open -> ~10:30 -> ~noon)
async function scoreDay(kv, FK, dt) {
  const list = await kv.get(`day:${dt}`);
  const tickers = Array.isArray(list) ? list : (list ? JSON.parse(list) : null);
  if (!tickers || !tickers.length) return null;
  let n = 0, hi = 0, hiHit = 0, cont = 0;
  const from = shift(dt, -4);
  for (const t of tickers) {
    const bars = await jget(`${FMP}/historical-chart/15min?symbol=${t}&from=${from}&to=${dt}&apikey=${FK}`);
    const day = (Array.isArray(bars) ? bars : []).filter(b => b.date && b.date.slice(0, 10) === dt);
    if (day.length < 3) continue;
    const asc = day.slice().reverse();               // FMP is newest-first
    const open = asc[0].open ?? asc[0].close;
    const at = (hh, mm) => { const b = asc.filter(x => x.date.slice(11, 16) <= `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`); return b.length ? b[b.length - 1].close : null; };
    const t1030 = at(10, 30), noon = at(12, 0);
    if (!open) continue;
    n++;
    const fh = (t1030) ? (t1030 / open - 1) * 100 : null;
    const continued = (noon) ? noon > open : null;
    if (continued === true) cont++;
    if (fh != null && fh >= 2 && fh <= 25) { hi++; if (continued === true) hiHit++; } // controlled morning surge
  }
  return { n, hi, hiHit, cont };
}

export default async function handler(req, res) {
  const FK = process.env.FMP_API_KEY;
  const KVURL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const KVTOK = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  let kv = null;
  try { const { createClient } = await import('@vercel/kv'); if (KVURL && KVTOK) kv = createClient({ url: KVURL, token: KVTOK }); } catch (e) { /* dep missing */ }
  if (!kv) { res.setHeader('Content-Type', 'application/json'); return res.status(200).json({ ok: false, note: 'KV store not connected — add a Vercel KV/Upstash store, then redeploy.' }); }

  const today = etDate();
  const sc = (await kv.get('scorecard')) || { days: 0, surges: 0, scored_surges: 0, hi_calls: 0, hi_hits: 0, cont: 0, scored_days: 0 };
  for (const k of ['days', 'surges', 'scored_surges', 'hi_calls', 'hi_hits', 'cont', 'scored_days']) sc[k] = sc[k] || 0;

  // ---- 1) log today's >=25% gainers (dataset). Skip if already done today. ----
  let loggedToday = 0;
  if (!(await kv.get(`logged:${today}`))) {
    const [gain, act] = await Promise.all([
      jget(`${FMP}/biggest-gainers?apikey=${FK}`), jget(`${FMP}/most-actives?apikey=${FK}`),
    ]);
    const syms = [...new Set([...(gain || []), ...(act || [])].map(x => x.symbol).filter(Boolean))].slice(0, 150);
    const q = await jget(`${FMP}/batch-quote?symbols=${syms.join(',')}&apikey=${FK}`) || [];
    const big = q.filter(x => (x.changePercentage || 0) >= 25).slice(0, 40);
    for (const g of big) {
      await kv.lpush('surge_log', JSON.stringify({ date: today, t: g.symbol, name: g.name || g.symbol, day_pct: round(g.changePercentage), price: g.price, vol: g.volume, mcap: g.marketCap }));
    }
    await kv.set(`day:${today}`, JSON.stringify(big.map(g => g.symbol)), { ex: 60 * 60 * 24 * 10 });
    await kv.set(`logged:${today}`, 1, { ex: 60 * 60 * 30 });
    sc.days += 1; sc.surges += big.length; loggedToday = big.length;
  }

  // ---- 2) T+1 scoring: score the last few prior days that aren't scored yet ----
  const scored = [];
  for (let back = 1; back <= 4; back++) {
    const dt = shift(today, -back);
    if (await kv.get(`scored:${dt}`)) continue;
    const r = await scoreDay(kv, FK, dt);
    if (r && r.n > 0) {
      sc.scored_surges += r.n; sc.hi_calls += r.hi; sc.hi_hits += r.hiHit; sc.cont += r.cont; sc.scored_days += 1;
      await kv.set(`scored:${dt}`, 1, { ex: 60 * 60 * 24 * 40 });
      scored.push({ date: dt, ...r });
    }
  }

  sc.hi_hit_rate_pct = sc.hi_calls ? round(sc.hi_hits / sc.hi_calls * 100, 0) : null;
  sc.overall_continuation_pct = sc.scored_surges ? round(sc.cont / sc.scored_surges * 100, 0) : null;
  sc.updated = today;
  await kv.set('scorecard', sc);

  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({ ok: true, date: today, logged_today: loggedToday, scored_prior_days: scored, scorecard: sc,
    note: 'Surges logged same-day; call scoring is T+1 (intraday lags), so the scorecard fills in a day after each session. Educational only — not advice.' });
}
