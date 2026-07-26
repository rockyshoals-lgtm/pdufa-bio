// pdufa.bio — PRE-MARKET momentum board (the earliness unlock).
// LEADLAB research: of every small/micro name that eventually surged +25% intraday,
// 83% were ALREADY up >=10% by 9:00am and 69% by 8:00am. So we detect them BEFORE
// the open instead of waiting for the +8% regular-session move the old board needed.
//
// Data: FMP extended-hours quotes (batch-aftermarket-quote) over a candidate
// watchlist (FMP's prior-session movers/actives — names that carry overnight
// interest). Optional ADV map (from a nightly UW screener cache in KV) enables
// pre-market relative-volume; without it we score on pre-market move alone.
//
// Educational only — NOT investment advice. Pre-market micro-cap quotes are THIN:
// a few shares wide, often not executable size. Treat these as the least-reliable
// numbers in the whole product.
import { scorePremarket, classify, GRID_META } from '../lib/scoring.mjs';
const LEGACY = { PRIME: 'HIGH_ODDS', BUILDING: 'MODERATE', WATCH: 'MODERATE', NOISE: 'FADE_RISK' };

const CFG = { MIN_PM_MOVE: 5, MAX_MCAP: 3_000_000_000, MIN_PRICE: 0.30, MAX_NAMES: 50, POOL: 250 };

async function jget(url) {
  try { const r = await fetch(url, { signal: AbortSignal.timeout(9000) }); return r.ok ? await r.json() : null; }
  catch { return null; }
}
function stamp(d) { return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC'; }

function session() {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(new Date()).map(x => [x.type, x.value]));
  if (p.weekday === 'Sat' || p.weekday === 'Sun') return { s: 'CLOSED', mins: 0 };
  const mins = (Number(p.hour) % 24) * 60 + Number(p.minute);
  if (mins >= 240 && mins < 570) return { s: 'PRE_OPEN', mins };
  if (mins >= 570 && mins < 960) return { s: 'OPEN', mins };
  return { s: 'CLOSED', mins };
}

// Optional ADV map cached nightly in KV (built from UW screener avg30_volume).
async function advMap() {
  try {
    const { kv } = await import('@vercel/kv');
    const m = await kv.get('adv_map');           // { TICKER: {adv, mcap} }
    return m && typeof m === 'object' ? m : null;
  } catch { return null; }
}

export default async function handler(req, res) {
  const FK = process.env.FMP_API_KEY;
  const now = new Date();
  const { s: sess } = session();
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (sess !== 'PRE_OPEN') {
    res.setHeader('Cache-Control', 's-maxage=120, stale-while-revalidate=600');
    const note = sess === 'OPEN'
      ? 'Market open — see the live board (/api/surges).'
      : 'Pre-market board runs 4:00–9:30am ET on weekdays.';
    return res.status(200).json({ session: sess, as_of: stamp(now), note, premarket: [] });
  }

  let board = [], err = null, advN = 0;
  try {
    // 1) candidate watchlist = names with overnight interest (prior-session movers/actives)
    const [gain, act] = await Promise.all([
      jget(`https://financialmodelingprep.com/stable/biggest-gainers?apikey=${FK}`),
      jget(`https://financialmodelingprep.com/stable/most-actives?apikey=${FK}`),
    ]);
    const syms = [...new Set([...(gain || []), ...(act || [])].map(x => x.symbol).filter(Boolean))].slice(0, CFG.POOL);
    if (!syms.length) throw new Error('no watchlist');

    // 2) static context (prevClose, mcap, name) + 3) live extended-hours quotes
    const adv = await advMap(); if (adv) advN = Object.keys(adv).length;
    const [ctx, am] = await Promise.all([
      jget(`https://financialmodelingprep.com/stable/batch-quote?symbols=${syms.join(',')}&apikey=${FK}`),
      jget(`https://financialmodelingprep.com/stable/batch-aftermarket-quote?symbols=${syms.join(',')}&apikey=${FK}`),
    ]);
    const cx = Object.fromEntries((ctx || []).map(r => [r.symbol, r]));
    for (const a of (am || [])) {
      const base = cx[a.symbol]; if (!base) continue;
      const prev = base.previousClose; if (!prev) continue;
      const mid = (a.bidPrice && a.askPrice) ? (a.bidPrice + a.askPrice) / 2 : (a.askPrice || a.bidPrice);
      if (!mid || mid < CFG.MIN_PRICE) continue;
      const mc = base.marketCap || 0; if (mc && mc > CFG.MAX_MCAP) continue;
      const pmMove = (mid / prev - 1) * 100;
      if (pmMove < CFG.MIN_PM_MOVE) continue;               // pre-market gappers only (long side)
      const a30 = adv && adv[a.symbol] ? adv[a.symbol].adv : (base.avgVolume || null);
      const relvol = (a30 && a.volume) ? +(a.volume / a30).toFixed(2) : null;   // pre-market vol / ADV
      const s = scorePremarket(pmMove, relvol);
      const c = classify({ p: s.p, movePct: pmMove, relvol });
      const thin = (a.bidSize != null && a.bidSize < 5) || (a.askSize != null && a.askSize < 5);
      const flags = c.flags.concat(thin ? ['THIN_QUOTE'] : []);
      board.push({
        ticker: a.symbol, name: base.name || a.symbol,
        price: +mid.toFixed(4), prev_close: prev,
        pm_move: +pmMove.toFixed(1), move: +pmMove.toFixed(1), chg: +pmMove.toFixed(1),
        relvol, pm_volume: a.volume ? Math.round(a.volume) : null, marketCap: mc || null,
        cont_odds_pct: Math.round(s.p * 100), odds_n: s.n, odds_basis: s.basis,
        tier: LEGACY[c.tier] || 'FADE_RISK', tier_new: c.tier, flags, thin,
        _rank: {PRIME:0,BUILDING:1,WATCH:2,NOISE:3}[c.tier],
      });
    }
    board.sort((x, y) => (x._rank - y._rank) || (y.cont_odds_pct - x.cont_odds_pct) || (y.pm_move - x.pm_move));
    board = board.slice(0, CFG.MAX_NAMES);
  } catch (e) { err = String(e.message || e); }

  res.setHeader('Cache-Control', 's-maxage=20, stale-while-revalidate=60');
  res.status(200).json({
    as_of: stamp(now), session: sess,
    window: 'Pre-market 4:00–9:30am ET. 83% of eventual +25% surgers are already up ≥10% by 9:00am (LEADLAB).',
    method: `LEADLAB pre-market base rates (n=${GRID_META ? 641 : 0} events with minute data). Odds = historical P(+25% intraday). Watchlist = prior-session movers/actives${advN ? `; ADV map ${advN} names` : '; no ADV map (move-only)'}.`,
    disclaimer: 'Educational only — NOT investment advice. Pre-market micro-cap quotes are extremely thin and often not executable. Highest-uncertainty numbers in the product.',
    relvol_enabled: advN > 0, n: board.length, err, premarket: board,
  });
}
