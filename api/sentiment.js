// Vercel Serverless Function — proxies social sentiment data
// Uses LunarCrush API for crypto/stock social metrics
// API key stored securely in Vercel Environment Variables
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { ticker } = req.query;
  const apiKey = process.env.LUNARCRUSH_API_KEY;

  if (!ticker) {
    return res.status(400).json({ error: 'ticker parameter required' });
  }

  try {
    let data = {};

    if (apiKey) {
      // Use LunarCrush API
      const resp = await fetch(
        `https://lunarcrush.com/api4/public/topic/${ticker.toLowerCase()}/v1`,
        { headers: { Authorization: `Bearer ${apiKey}` } }
      );
      if (resp.ok) {
        data = await resp.json();
      }
    }

    // Cache for 15 minutes
    res.setHeader('Cache-Control', 's-maxage=900, stale-while-revalidate=1800');
    return res.status(200).json(data);
  } catch (error) {
    console.error('Sentiment API error:', error);
    return res.status(500).json({ error: 'Failed to fetch sentiment data' });
  }
}
