// Vercel Serverless Function — proxies FMP (Financial Modeling Prep) API
// API key stored securely in Vercel Environment Variables, never exposed to browser
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

  const BASE = 'https://financialmodelingprep.com/api';

  try {
    let data = {};

    if (type === 'quote') {
      // Stock quote — price, change, volume, market cap
      const resp = await fetch(`${BASE}/v3/quote/${ticker}?apikey=${apiKey}`);
      const json = await resp.json();
      data = json[0] || {};
    } else if (type === 'insider') {
      // Insider trading — last 20 transactions
      const resp = await fetch(`${BASE}/v4/insider-trading?symbol=${ticker}&limit=20&apikey=${apiKey}`);
      data = await resp.json();
    } else if (type === 'financials') {
      // Key metrics + balance sheet for cash runway
      const [metricsResp, bsResp, cfResp] = await Promise.all([
        fetch(`${BASE}/v3/key-metrics/${ticker}?limit=4&apikey=${apiKey}`),
        fetch(`${BASE}/v3/balance-sheet-statement/${ticker}?limit=4&apikey=${apiKey}`),
        fetch(`${BASE}/v3/cash-flow-statement/${ticker}?limit=4&apikey=${apiKey}`),
      ]);
      const metrics = await metricsResp.json();
      const balanceSheet = await bsResp.json();
      const cashFlow = await cfResp.json();

      // Calculate cash runway
      const latestBS = balanceSheet[0] || {};
      const latestCF = cashFlow[0] || {};
      const cashAndEquiv = latestBS.cashAndCashEquivalents || 0;
      const quarterlyBurn = Math.abs(latestCF.operatingCashFlow || 0) / 4;
      const runwayQuarters = quarterlyBurn > 0 ? cashAndEquiv / quarterlyBurn : null;

      data = {
        metrics: metrics[0] || {},
        balanceSheet: latestBS,
        cashFlow: latestCF,
        cashRunway: {
          cash: cashAndEquiv,
          quarterlyBurn,
          runwayQuarters,
          runwayMonths: runwayQuarters ? runwayQuarters * 3 : null,
        },
      };
    } else if (type === 'options') {
      // Stock price change for IV proxy (FMP doesn't have full options chain on free tier)
      const resp = await fetch(`${BASE}/v3/stock_price_change/${ticker}?apikey=${apiKey}`);
      data = await resp.json();
    } else if (type === 'profile') {
      // Company profile
      const resp = await fetch(`${BASE}/v3/profile/${ticker}?apikey=${apiKey}`);
      const json = await resp.json();
      data = json[0] || {};
    } else {
      // Default: return quote + profile combo
      const [quoteResp, profileResp] = await Promise.all([
        fetch(`${BASE}/v3/quote/${ticker}?apikey=${apiKey}`),
        fetch(`${BASE}/v3/profile/${ticker}?apikey=${apiKey}`),
      ]);
      const quote = await quoteResp.json();
      const profile = await profileResp.json();
      data = {
        quote: quote[0] || {},
        profile: profile[0] || {},
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
