import Link from 'next/link';
import StructuredData from '../../../components/StructuredData';

export const metadata = {
  title: '8 for 8: ODIN\'s Perfect February 2026 Prediction Record | PDUFA.BIO',
  description: 'ODIN went 8 for 8 in February 2026 — correctly predicting all 5 FDA approvals and all 3 CRLs. Here\'s the full scorecard and what it means for March.',
  alternates: {
    canonical: 'https://www.pdufa.bio/blog/odin-february-2026-perfect-record',
  },
  openGraph: {
    title: '8 for 8: ODIN\'s Perfect February 2026 Prediction Record',
    description: 'ODIN called every FDA PDUFA decision in February 2026 correctly. 5 approvals, 3 CRLs. 100%.',
    type: 'article',
    url: 'https://www.pdufa.bio/blog/odin-february-2026-perfect-record',
    publishedTime: '2026-03-01T00:00:00Z',
  },
  twitter: {
    card: 'summary_large_image',
    title: '8 for 8: ODIN\'s Perfect February 2026 Prediction Record',
    description: 'ODIN went 8/8 in Feb 2026: ASND, ETON, REGN, VNDA approved. IRON, RGNX, PHAR CRL. All called correctly.',
  },
  keywords: [
    'ODIN track record',
    'ODIN February 2026',
    'PDUFA prediction accuracy',
    'FDA approval prediction AI',
    'ODIN 8 for 8',
    'biotech catalyst AI',
    'PDUFA calendar AI predictions',
    'FDA decision predictions 2026',
    'ODIN perfect record',
    'biotech AI scoring engine',
  ],
};

const jsonLdSchemas = [
  {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": "8 for 8: ODIN's Perfect February 2026 Prediction Record",
    "description": "ODIN correctly predicted all 8 FDA PDUFA decisions in February 2026 — 5 approvals and 3 CRLs.",
    "datePublished": "2026-03-01T00:00:00Z",
    "dateModified": "2026-03-01T00:00:00Z",
    "author": { "@type": "Organization", "name": "PDUFA.BIO" },
    "publisher": {
      "@type": "Organization",
      "name": "PDUFA.BIO",
      "logo": { "@type": "ImageObject", "url": "https://www.pdufa.bio/odin-favicon-512.png" }
    },
    "mainEntityOfPage": { "@type": "WebPage", "@id": "https://www.pdufa.bio/blog/odin-february-2026-perfect-record" }
  }
];

const febResults = [
  { ticker: 'ASND', drug: 'TransCon hGH Weekly', date: 'Feb 7', score: '95.5%', tier: 'TIER_1', outcome: 'APPROVED', move: '+19%', correct: true },
  { ticker: 'RGNX', drug: 'RGX-121', date: 'Feb 7', score: '45.0%', tier: 'TIER_4', outcome: 'CRL', move: '-21%', correct: true },
  { ticker: 'IRON', drug: 'Bitopertin', date: 'Feb 13', score: '39.4%', tier: 'TIER_4', outcome: 'CRL', move: '-52%', correct: true },
  { ticker: 'VNDA', drug: 'Bysanti', date: 'Feb 20', score: '89.7%', tier: 'TIER_1', outcome: 'APPROVED', move: '+44%', correct: true },
  { ticker: 'REGN', drug: 'Dupixent AFRS', date: 'Feb 24', score: '94.8%', tier: 'TIER_1', outcome: 'APPROVED', move: '+7.3%', correct: true },
  { ticker: 'ETON', drug: 'ET-600', date: 'Feb 25', score: '85.5%', tier: 'TIER_2', outcome: 'APPROVED', move: '+14.7%', correct: true },
  { ticker: 'ASND', drug: 'YUVIWEL', date: 'Feb 27', score: '88.9%', tier: 'TIER_1', outcome: 'APPROVED', move: '+6%', correct: true },
  { ticker: 'PHAR', drug: 'Leniolisib sNDA', date: 'Feb 1', score: '58.0%', tier: 'TIER_3', outcome: 'CRL', move: '-28%', correct: true },
];

export default function PerfectRecordBlogPost() {
  return (
    <>
      <StructuredData schemas={jsonLdSchemas} />

      <article style={{ backgroundColor: '#030712', color: '#e5e7eb', fontFamily: 'system-ui, sans-serif', lineHeight: '1.8' }}>
        {/* Hero */}
        <div style={{ maxWidth: '720px', margin: '0 auto', padding: '3rem 1.5rem 1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <span style={{ background: '#166534', color: '#bbf7d0', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', letterSpacing: '0.05em' }}>TRACK RECORD</span>
            <span style={{ background: '#92400e', color: '#fde68a', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', letterSpacing: '0.05em' }}>8/8 PERFECT</span>
          </div>

          <h1 style={{ fontSize: '2.25rem', fontWeight: '800', color: '#f9fafb', lineHeight: '1.2', marginBottom: '0.75rem' }}>
            8 for 8: ODIN&apos;s Perfect February 2026
          </h1>

          <p style={{ color: '#9ca3af', fontSize: '0.9rem', marginBottom: '2rem' }}>
            March 1, 2026 &middot; 4 min read
          </p>
        </div>

        {/* Body */}
        <div style={{ maxWidth: '720px', margin: '0 auto', padding: '0 1.5rem 3rem' }}>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            February is done. Let&apos;s count the tape.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            Eight PDUFA decisions hit in February 2026. ODIN called every single one correctly — 5 approvals, 3 Complete Response Letters.
            100% directional accuracy for the month.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            I&apos;m not going to pretend this is normal. It&apos;s not. Even with a 0.9193 walk-forward AUC, a perfect month is the upper tail of what the model is capable of.
            But that&apos;s the point — ODIN is designed to be right when it&apos;s confident, and cautious when the signal is mixed.
            February happened to be a month where the signal was clear, and the model read it correctly across the board.
          </p>

          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f9fafb', marginTop: '2rem', marginBottom: '1rem' }}>
            The Full Scorecard
          </h2>

          {/* Results table */}
          <div style={{ overflowX: 'auto', margin: '1.5rem 0' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #374151' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', color: '#9ca3af', fontWeight: '600' }}>Ticker</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', color: '#9ca3af', fontWeight: '600' }}>Drug</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem', color: '#9ca3af', fontWeight: '600' }}>ODIN</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem', color: '#9ca3af', fontWeight: '600' }}>Tier</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem', color: '#9ca3af', fontWeight: '600' }}>Result</th>
                  <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem', color: '#9ca3af', fontWeight: '600' }}>Move</th>
                </tr>
              </thead>
              <tbody>
                {febResults.map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #1f2937' }}>
                    <td style={{ padding: '0.6rem 0.5rem', fontWeight: '700', color: '#f9fafb' }}>{r.ticker}</td>
                    <td style={{ padding: '0.6rem 0.5rem', color: '#d1d5db' }}>{r.drug}</td>
                    <td style={{ padding: '0.6rem 0.5rem', textAlign: 'center', color: r.outcome === 'APPROVED' ? '#4ade80' : '#f87171', fontWeight: '600' }}>{r.score}</td>
                    <td style={{ padding: '0.6rem 0.5rem', textAlign: 'center', color: '#d1d5db' }}>{r.tier}</td>
                    <td style={{ padding: '0.6rem 0.5rem', textAlign: 'center' }}>
                      <span style={{
                        background: r.outcome === 'APPROVED' ? '#166534' : '#7f1d1d',
                        color: r.outcome === 'APPROVED' ? '#bbf7d0' : '#fecaca',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.8rem',
                        fontWeight: '600'
                      }}>{r.outcome}</span>
                    </td>
                    <td style={{ padding: '0.6rem 0.5rem', textAlign: 'right', color: r.move.startsWith('+') ? '#4ade80' : '#f87171', fontWeight: '600' }}>{r.move}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f9fafb', marginTop: '2rem', marginBottom: '1rem' }}>
            The CRLs Matter More Than the Approvals
          </h2>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            Anybody can predict approvals — the base rate is ~68%.
            The real alpha is in calling the CRLs.
            When ODIN scored IRON (Bitopertin) at 39.4% and RGNX (RGX-121) at 45.0%, those weren&apos;t popular opinions.
            IRON had the rare disease narrative. RGNX had the gene therapy excitement.
            Both had the kind of community conviction that makes you second-guess the data.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            But the model doesn&apos;t have conviction bias. It has 45 features and 2,200+ outcomes.
            IRON tanked 52%. RGNX dropped 21%. PHAR fell 28%. If you were on the wrong side of those, you felt it.
            If you were watching ODIN, you were either flat or short.
          </p>

          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f9fafb', marginTop: '2rem', marginBottom: '1rem' }}>
            What This Means Going Forward
          </h2>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            One perfect month doesn&apos;t make a model. But it validates the approach:
            train on real outcomes, validate with walk-forward methodology (not overfitted backtests),
            and let the probabilities speak for themselves.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            March has its own slate of catalysts lining up. LNTH, ALDX, MESO — each with its own risk profile.
            ODIN is already scoring them.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem', fontWeight: '600', color: '#f9fafb' }}>
            The model doesn&apos;t celebrate. It just reloads.
          </p>

          <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '0.75rem', padding: '1.5rem', margin: '2rem 0' }}>
            <h3 style={{ color: '#fbbf24', fontWeight: '700', fontSize: '1rem', marginBottom: '0.75rem' }}>February 2026 — ODIN Summary</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.95rem' }}>
              <span style={{ color: '#9ca3af' }}>Total Decisions:</span><span style={{ color: '#f9fafb', fontWeight: '600' }}>8</span>
              <span style={{ color: '#9ca3af' }}>Correct Calls:</span><span style={{ color: '#4ade80', fontWeight: '600' }}>8 (100%)</span>
              <span style={{ color: '#9ca3af' }}>Approvals Called:</span><span style={{ color: '#f9fafb' }}>5/5</span>
              <span style={{ color: '#9ca3af' }}>CRLs Called:</span><span style={{ color: '#f9fafb' }}>3/3</span>
              <span style={{ color: '#9ca3af' }}>Biggest Winner:</span><span style={{ color: '#4ade80' }}>VNDA +44%</span>
              <span style={{ color: '#9ca3af' }}>Biggest CRL Dodge:</span><span style={{ color: '#f87171' }}>IRON -52%</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginTop: '2.5rem', flexWrap: 'wrap' }}>
            <Link href="/pdufa-dates-march-2026" style={{ background: '#2563eb', color: '#fff', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', textDecoration: 'none', fontWeight: '600', fontSize: '0.95rem' }}>
              March 2026 PDUFA Dates →
            </Link>
            <Link href="/odin-track-record" style={{ background: '#1f2937', color: '#e5e7eb', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', textDecoration: 'none', fontWeight: '600', fontSize: '0.95rem', border: '1px solid #374151' }}>
              Full ODIN Track Record
            </Link>
            <Link href="/february-2026-pdufa-approvals" style={{ background: '#1f2937', color: '#e5e7eb', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', textDecoration: 'none', fontWeight: '600', fontSize: '0.95rem', border: '1px solid #374151' }}>
              February 2026 Detail
            </Link>
          </div>

          <p style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: '2.5rem', fontStyle: 'italic' }}>
            Disclaimer: PDUFA.BIO provides data and analysis for informational purposes only. ODIN scores are probabilistic estimates, not investment advice. Past performance does not guarantee future results. Always do your own due diligence.
          </p>
        </div>
      </article>
    </>
  );
}
