-- ═══════════════════════════════════════════════════
-- PDUFA.BIO Database Schema
-- Run this in Supabase Dashboard → SQL Editor → New Query
-- ═══════════════════════════════════════════════════

-- Predictions table: users predict APPROVE or CRL for each catalyst
CREATE TABLE IF NOT EXISTS predictions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_fingerprint TEXT NOT NULL,  -- anonymous device fingerprint
  catalyst_id TEXT NOT NULL,
  prediction TEXT NOT NULL CHECK (prediction IN ('APPROVE', 'CRL')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_fingerprint, catalyst_id)  -- one prediction per user per catalyst
);

-- Catalyst outcomes (filled in when FDA decides)
CREATE TABLE IF NOT EXISTS outcomes (
  catalyst_id TEXT PRIMARY KEY,
  outcome TEXT NOT NULL CHECK (outcome IN ('APPROVE', 'CRL', 'DELAYED')),
  decided_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT
);

-- Leaderboard view (aggregated stats)
CREATE OR REPLACE VIEW leaderboard AS
SELECT
  p.user_fingerprint,
  COUNT(*) as total_predictions,
  COUNT(o.outcome) as scored_predictions,
  COUNT(CASE WHEN p.prediction = o.outcome THEN 1 END) as correct,
  ROUND(
    CASE WHEN COUNT(o.outcome) > 0
      THEN COUNT(CASE WHEN p.prediction = o.outcome THEN 1 END)::numeric / COUNT(o.outcome) * 100
      ELSE 0
    END, 1
  ) as accuracy_pct,
  COUNT(CASE WHEN p.prediction = o.outcome THEN 1 END) * 10 as biocred_points
FROM predictions p
LEFT JOIN outcomes o ON p.catalyst_id = o.catalyst_id
GROUP BY p.user_fingerprint
ORDER BY biocred_points DESC, accuracy_pct DESC;

-- Prediction counts per catalyst (for community sentiment display)
CREATE OR REPLACE VIEW catalyst_sentiment AS
SELECT
  catalyst_id,
  COUNT(*) as total_votes,
  COUNT(CASE WHEN prediction = 'APPROVE' THEN 1 END) as approve_votes,
  COUNT(CASE WHEN prediction = 'CRL' THEN 1 END) as crl_votes,
  ROUND(
    COUNT(CASE WHEN prediction = 'APPROVE' THEN 1 END)::numeric / GREATEST(COUNT(*), 1) * 100, 1
  ) as approve_pct
FROM predictions
GROUP BY catalyst_id;

-- Enable Row Level Security
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes ENABLE ROW LEVEL SECURITY;

-- Allow anonymous reads on everything
CREATE POLICY "Anyone can read predictions" ON predictions FOR SELECT USING (true);
CREATE POLICY "Anyone can insert predictions" ON predictions FOR INSERT WITH CHECK (true);
CREATE POLICY "Anyone can read outcomes" ON outcomes FOR SELECT USING (true);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_predictions_catalyst ON predictions(catalyst_id);
CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_fingerprint);
