// pdufa.bio — UNBIASED momentum-surge scoring.
// Odds come from the 9REALMS LEADLAB study: Polygon whole-market grouped-daily
// (INCLUDES since-delisted tickers → NOT survivorship-biased), 5,810 small/micro
// gap-up ticker-days + 641 with pre-market minute data. The number scored is the
// historical base rate P(hit +25% intraday vs prev close) for a name at this
// move × relative-volume — winners AND losers included.
//
// Informational/educational only — NOT investment advice.
const grid = {"meta":{"events":5810,"label":"P(intraday +25% vs prev close) | small/micro gap-up","source":"Polygon whole-market grouped-daily (incl. delisted) \u2014 unbiased","gap_edges":[3,5,10,20,40],"rv_edges":[0,1,2,5,10],"min_gap":3},"open_grid":[[{"p":0.007,"n":1782},{"p":0.019,"n":981},{"p":0.072,"n":349},{"p":0.161,"n":56},{"p":0.396,"n":48}],[{"p":0.016,"n":883},{"p":0.051,"n":602},{"p":0.129,"n":248},{"p":0.271,"n":48},{"p":0.431,"n":58}],[{"p":0.124,"n":153},{"p":0.184,"n":163},{"p":0.314,"n":105},{"p":0.548,"n":31},{"p":0.712,"n":52}],[{"p":0.875,"n":16},{"p":0.783,"n":23},{"p":0.871,"n":31},{"p":0.895,"n":19},{"p":1.0,"n":49}],[null,null,null,null,{"p":1.0,"n":93}]],"gap_marginal":[{"p":0.026,"n":3216},{"p":0.063,"n":1839},{"p":0.27,"n":504},{"p":0.906,"n":138},{"p":1.0,"n":113}],"rv_marginal":[{"p":0.021,"n":2834},{"p":0.057,"n":1772},{"p":0.166,"n":739},{"p":0.406,"n":165},{"p":0.743,"n":300}],"base_rate":0.099,"pm_edges":[3,5,10,20,40],"pm0900_marginal":[{"p":0.012,"n":86},{"p":0.109,"n":129},{"p":0.474,"n":95},{"p":0.922,"n":51},{"p":1.0,"n":68}],"pm0900_x_relvol_grid":[[{"p":0.021,"n":48},{"p":0.0,"n":25},{"p":0.0,"n":11},null,null],[{"p":0.0,"n":46},{"p":0.02,"n":51},{"p":0.375,"n":24},null,null],[{"p":0.292,"n":24},{"p":0.3,"n":20},{"p":0.409,"n":22},{"p":0.667,"n":12},{"p":0.882,"n":17}],[null,null,{"p":0.9,"n":10},null,{"p":0.962,"n":26}],[null,null,null,null,{"p":1.0,"n":60}]],"pm_sample":641};

const GAP = grid.meta.gap_edges;   // [3,5,10,20,40]
const RV  = grid.meta.rv_edges;    // [0,1,2,5,10]
const PM  = grid.pm_edges;         // [3,5,10,20,40]

const bucket = (edges, x) => {
  if (x == null || isNaN(x)) return null;
  for (let i = 0; i < edges.length - 1; i++) if (x >= edges[i] && x < edges[i + 1]) return i;
  return x >= edges[edges.length - 1] ? edges.length - 1 : null;
};

// P(surge) from the OPEN-session grid (move% vs prev close, relvol vs 20d ADV).
// Falls back to the gap marginal when a cell is sparse, then to base rate.
export function scoreOpen(movePct, relvol) {
  const gi = bucket(GAP, movePct);
  if (gi == null) return { p: grid.base_rate, n: 0, basis: 'below_min_gap' };
  const vi = bucket(RV, relvol);
  if (vi != null && grid.open_grid[gi] && grid.open_grid[gi][vi]) {
    return { p: grid.open_grid[gi][vi].p, n: grid.open_grid[gi][vi].n, basis: 'gap_x_relvol' };
  }
  const m = grid.gap_marginal[gi];
  return { p: m.p, n: m.n, basis: relvol == null ? 'gap_only(no_relvol)' : 'gap_marginal' };
}

// P(surge) from the PRE-MARKET grid (pm move% at ~09:00 vs prev close, relvol).
export function scorePremarket(pmMovePct, relvol) {
  const pi = bucket(PM, pmMovePct);
  if (pi == null) return { p: grid.base_rate, n: 0, basis: 'below_min_pm' };
  const vi = bucket(RV, relvol);
  const g2 = grid.pm0900_x_relvol_grid;
  if (vi != null && g2 && g2[pi] && g2[pi][vi]) {
    return { p: g2[pi][vi].p, n: g2[pi][vi].n, basis: 'pm_x_relvol' };
  }
  const m = grid.pm0900_marginal[pi];
  return { p: m.p, n: m.n, basis: 'pm_marginal' };
}

// Educational tier + flags. Tuned "earlier, accept more noise": we surface a
// candidate as soon as move × volume clears a modest bar, and only DOWNGRADE
// on blow-off exhaustion. Confluence (big move AND heavy volume) = ROCKET.
export function classify({ p, movePct, relvol, uoaBull }) {
  const flags = [];
  const big = movePct >= 20, mid = movePct >= 10;
  const heavyVol = relvol != null && relvol >= 5;
  const modVol = relvol != null && relvol >= 2;
  const rocket = (big || (mid && heavyVol)) && heavyVol;     // volume-confirmed real move
  if (rocket) flags.push('ROCKET');
  if (relvol != null && relvol >= 10 && movePct < 10) flags.push('VOL_NO_PRICE'); // volume before price — early tell
  if (movePct >= 50 && (relvol == null || relvol < 3)) flags.push('EXHAUSTION_RISK');
  if (modVol && mid && !big) flags.push('CONTROLLED');
  if (uoaBull) flags.push('UOA_BULL');
  let tier;
  if (rocket || p >= 0.70) tier = 'PRIME';        // volume-confirmed / high base rate
  else if (p >= 0.40 || (mid && modVol)) tier = 'BUILDING';  // fire EARLY, accept noise
  else if (p >= 0.15) tier = 'WATCH';
  else tier = 'NOISE';
  return { tier, flags };
}

export const GRID_META = grid.meta;
export { grid as SCORING_GRID };
