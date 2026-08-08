// pdufa.bio — live momentum-surge engine (v2, UNBIASED).
// Server-side only: FMP key from Vercel env (never sent to the browser). Rates
// intraday movers with the 9REALMS LEADLAB base rates — built from Polygon
// whole-market data that INCLUDES since-delisted tickers, so winners AND losers
// are counted (the old table was survivorship-biased and over-optimistic).
//
// The odds = historical P(a small/micro name at this move × relative-volume goes
// on to hit +25% intraday vs its prior close). Educational base rate, NOT a
// prediction and NOT investment advice.
import { scoreOpen, classify, GRID_META } from '../lib/scoring.mjs';

const CFG = { MIN_MOVE_PCT: 5, MAX_MCAP: 3_000_000_000, MIN_PRICE: 0.30, MAX_NAMES: 60 };

async function jget(url) {
  try { const r = await fetch(url, { signal: AbortSignal.timeout(9000) }); return r.ok ? await r.json() : null; }
  catch { return null; }
}

function marketSession() {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(new Date()).map(x => [x.type, x.value]));
  if (p.weekday === 'Sat' || p.weekday === 'Sun') return 'CLOSED';
  const mins = (Number(p.hour) % 24) * 60 + Number(p.minute);
  if (mins >= 240 && mins < 570) return 'PRE_OPEN';   // 4:00–9:30 ET → use /api/premarket
  if (mins >= 570 && mins < 960) return 'OPEN';       // 9:30–16:00 ET
  return 'CLOSED';
}

// legacy tier names the current UI still styles, mapped from the new tiers
const LEGACY = { PRIME: 'HIGH_ODDS', BUILDING: 'MODERATE', WATCH: 'MODERATE', NOISE: 'FADE_RISK' };

export default async function handler(req, res) {
  const FK = process.env.FMP_API_KEY;
  const now = new Date();
  const sess = marketSession();
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (sess !== 'OPEN') {
    res.setHeader('Cache-Control', 's-maxage=120, stale-while-revalidate=600');
    const note = sess === 'PRE_OPEN'
      ? 'Pre-market — see the pre-market board (/api/premarket) for extended-hours gappers. The regular-session board is live 9:30am–4:00pm ET.'
      : 'Market closed — the live surge board runs 9:30am–4:00pm ET on weekdays.';
    return res.status(200).json({ session: sess, as_of: stamp(now), note, surges: [] });
  }

  let board = [], err = null;
  try {
    const [gain, act] = await Promise.all([
      jget(`https://financialmodelingprep.com/stable/biggest-gainers?apikey=${FK}`),
      jget(`https://financialmodelingprep.com/stable/most-actives?apikey=${FK}`),
    ]);
    const syms = [...new Set([...(gain || []), ...(act || [])].map(x => x.symbol).filter(Boolean))].slice(0, 120);
    if (!syms.length) throw new Error('no universe');
    const q = await jget(`https://financialmodelingprep.com/stable/batch-quote?symbols=${syms.join(',')}&apikey=${FK}`);
    for (const r of (q || [])) {
      const mc = r.marketCap || 0, chg = r.changePercentage, px = r.price;
      if (px == null || px < CFG.MIN_PRICE) continue;
      if (mc && mc > CFG.MAX_MCAP) continue;
      const move = Math.abs(chg || 0);
      if (move < CFG.MIN_MOVE_PCT) continue;
      const adv = r.avgVolume ?? r.averageVolume ?? null;               // FMP often null → move-only fallback
      const relvol = (adv && r.volume) ? +(r.volume / adv).toFixed(1) : null;
      const s = scoreOpen(move, relvol);
      const c = classify({ p: s.p, movePct: move, relvol });
      board.push({
        ticker: r.symbol, name: r.name || r.symbol, price: px,
        chg: +(chg || 0).toFixed(1), move: +move.toFixed(1),
        relvol, marketCap: mc || null, volume: r.volume || null, avgVolume: adv,
        cont_odds_pct: Math.round(s.p * 100), odds_n: s.n, odds_basis: s.basis,
        tier: LEGACY[c.tier] || 'FADE_RISK', tier_new: c.tier, flags: c.flags, _rank: {PRIME:0,BUILDING:1,WATCH:2,NOISE:3}[c.tier],
      });
    }
    board.sort((a, b) => (a._rank - b._rank) || (b.cont_odds_pct - a.cont_odds_pct) || (b.move - a.move));
    board = board.slice(0, CFG.MAX_NAMES);
  } catch (e) { err = String(e.message || e); }

  res.setHeader('Cache-Control', 's-maxage=20, stale-while-revalidate=60');
  res.status(200).json({
    as_of: stamp(now),
    window: '9:30am–noon ET — ride the morning wave, exit by midday (not a hold-all-day signal)',
    method: `9REALMS LEADLAB unbiased base rates (${GRID_META.events} whole-market gap-up days incl. delisted). Odds = historical P(+25% intraday), NOT predictions.`,
    disclaimer: 'Informational and educational only — NOT investment advice. Base rates are historical; any single name can fail. You make all decisions.',
    session: sess, n: board.length, err, surges: board,
  });
}
function stamp(d) { return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC'; }
