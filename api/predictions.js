// Supabase Predictions API — handles predictions CRUD and leaderboard
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY;

async function supabaseRequest(path, options = {}) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...options,
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': options.prefer || 'return=representation',
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Supabase ${res.status}: ${err}`);
  }
  return res.json();
}

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    const { action } = req.query;

    // GET /api/predictions?action=sentiment — community sentiment per catalyst
    if (action === 'sentiment') {
      const data = await supabaseRequest('catalyst_sentiment?select=*');
      return res.status(200).json(data);
    }

    // GET /api/predictions?action=leaderboard — top predictors
    if (action === 'leaderboard') {
      const data = await supabaseRequest('leaderboard?select=*&limit=25');
      return res.status(200).json(data);
    }

    // GET /api/predictions?action=user&fingerprint=xxx — user's predictions
    if (action === 'user') {
      const fp = req.query.fingerprint;
      if (!fp) return res.status(400).json({ error: 'fingerprint required' });
      const data = await supabaseRequest(`predictions?user_fingerprint=eq.${fp}&select=*`);
      return res.status(200).json(data);
    }

    // POST /api/predictions — submit a prediction
    if (req.method === 'POST') {
      const { fingerprint, catalyst_id, prediction } = req.body;
      if (!fingerprint || !catalyst_id || !prediction) {
        return res.status(400).json({ error: 'fingerprint, catalyst_id, prediction required' });
      }
      if (!['APPROVE', 'CRL'].includes(prediction)) {
        return res.status(400).json({ error: 'prediction must be APPROVE or CRL' });
      }

      // Upsert (one prediction per user per catalyst)
      const data = await supabaseRequest('predictions', {
        method: 'POST',
        body: JSON.stringify({
          user_fingerprint: fingerprint,
          catalyst_id,
          prediction,
        }),
        headers: { 'Prefer': 'resolution=merge-duplicates,return=representation' },
        prefer: 'resolution=merge-duplicates,return=representation',
      });
      return res.status(200).json(data);
    }

    return res.status(400).json({ error: 'Invalid action. Use: sentiment, leaderboard, user, or POST to submit.' });
  } catch (err) {
    console.error('Predictions API error:', err);
    return res.status(500).json({ error: err.message });
  }
}
