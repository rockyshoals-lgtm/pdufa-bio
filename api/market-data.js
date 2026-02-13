// Vercel Serverless Function — proxies FMP (Financial Modeling Prep) API
// API key stored securely in Vercel Environment Variables, never exposed to browser
// Updated Feb 2026: Uses /stable/ endpoints (v3/v4 are deprecated)
export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { ticker, type } = req.query;
  const apiKey = process.env.FMP_API_KEY;

  if (!apiKey) {
    return res.status(500).json({ error: 'FMP_API_KEY not configured' });
  }
  if (!ticker) {
    return res.status(400).json({ error: 'ticker parameter required' });
  }

  const BASE = 'https://financialmodelingprep.com/stable';

  try {
    let data = {};

    if (type === 'quote') {
      // Stock quote — price, change, volume, market cap
      const resp = await fetch(`${BASE}/quote?symbol=${ticker}&apikey=${apiKey}`);
      const json = await resp.json();
      const q = json[0] || {};
      // Normalize field names for frontend
      data = {
        ...q,
        price: q.price,
        changesPercentage: q.changePercentage || q.changesPercentage || 0,
        change: q.change || 0,
        volume: q.volume || 0,
        marketCap: q.marketCap || 0,
        name: q.name || ticker,
      };
    } else if (type === 'insider') {
      // Insider trading — last 20 transactions
      const resp = await fetch(`${BASE}/insider-trading?symbol=${ticker}&limit=20&apikey=${apiKey}`);
      const json = await resp.json();
      data = Array.isArray(json) ? json : [];
    } else if (type === 'financials') {
      // Balance sheet + cash flow for runway calculation
      const [bsResp, cfResp] = await Promise.all([
        fetch(`${BASE}/balance-sheet-statement?symbol=${ticker}&limit=4&apikey=${apiKey}`),
        fetch(`${BASE}/cash-flow-statement?symbol=${ticker}&limit=4&apikey=${apiKey}`),
      ]);
      const balanceSheet = await bsResp.json();
      const cashFlow = await cfResp.json();

      const latestBS = (Array.isArray(balanceSheet) ? balanceSheet[0] : null) || {};
      const latestCF = (Array.isArray(cashFlow) ? cashFlow[0] : null) || {};

      // Calculate cash runway
      const cashAndEquiv = latestBS.cashAndCashEquivalents || latestBS.cashAndShortTermInvestments || 0;
      const opCF = latestCF.operatingCashFlow || latestCF.netCashProvidedByOperatingActivities || 0;
      const quarterlyBurn = opCF < 0 ? Math.abs(opCF) / 4 : 0;
      const runwayQuarters = quarterlyBurn > 0 ? cashAndEquiv / quarterlyBurn : null;

      data = {
        balanceSheet: latestBS,
        cashFlow: latestCF,
        cashRunway: {
          cash: cashAndEquiv,
          quarterlyBurn,
          runwayQuarters,
          runwayMonths: runwayQuarters ? runwayQuarters * 3 : null,
        },
      };
    } else if (type === 'profile') {
      // Company profile
      const resp = await fetch(`${BASE}/profile?symbol=${ticker}&apikey=${apiKey}`);
      const json = await resp.json();
      data = (Array.isArray(json) ? json[0] : json) || {};
    } else {
      // Default: return quote + profile combo
      const [quoteResp, profileResp] = await Promise.all([
        fetch(`${BASE}/quote?symbol=${ticker}&apikey=${apiKey}`),
        fetch(`${BASE}/profile?symbol=${ticker}&apikey=${apiKey}`),
      ]);
      const quote = await quoteResp.json();
      const profile = await profileResp.json();
      const q = (Array.isArray(quote) ? quote[0] : quote) || {};
      data = {
        quote: { ...q, changesPercentage: q.changePercentage || q.changesPercentage || 0 },
        profile: (Array.isArray(profile) ? profile[0] : profile) || {},
      };
    }

    // Cache for 5 minutes
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');
    return res.status(200).json(data);
  } catch (error) {
    console.error('FMP API error:', error);
    return res.status(500).json({ error: 'Failed to fetch market data' });
  }
}
