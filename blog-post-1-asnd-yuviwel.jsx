import Link from 'next/link';
import StructuredData from '../../../components/StructuredData';

export const metadata = {
  title: 'ODIN Called ASND YUVIWEL Before the Street Blinked | PDUFA.BIO',
  description: 'How ODIN scored ASND YUVIWEL (navepegritide) at 88.9% approval probability weeks before the Feb 27 FDA decision — and why the market still underpriced it.',
  alternates: {
    canonical: 'https://www.pdufa.bio/blog/odin-calls-asnd-yuviwel-approval',
  },
  openGraph: {
    title: 'ODIN Called ASND YUVIWEL Before the Street Blinked',
    description: 'ASND YUVIWEL scored 88.9% by ODIN. FDA approved Feb 27. Here\'s the breakdown.',
    type: 'article',
    url: 'https://www.pdufa.bio/blog/odin-calls-asnd-yuviwel-approval',
    publishedTime: '2026-03-01T00:00:00Z',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ODIN Called ASND YUVIWEL Before the Street Blinked',
    description: 'ASND YUVIWEL: 88.9% ODIN score → FDA APPROVED Feb 27. The data was there.',
  },
  keywords: [
    'ASND YUVIWEL approval',
    'ASND PDUFA',
    'navepegritide FDA approval',
    'ODIN prediction ASND',
    'achondroplasia treatment FDA',
    'ASND stock FDA',
    'biotech catalyst prediction',
    'PDUFA AI prediction',
    'ODIN track record',
  ],
};

const jsonLdSchemas = [
  {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": "ODIN Called ASND YUVIWEL Before the Street Blinked",
    "description": "How ODIN scored ASND YUVIWEL at 88.9% approval probability — and the FDA agreed on Feb 27, 2026.",
    "datePublished": "2026-03-01T00:00:00Z",
    "dateModified": "2026-03-01T00:00:00Z",
    "author": { "@type": "Organization", "name": "PDUFA.BIO" },
    "publisher": {
      "@type": "Organization",
      "name": "PDUFA.BIO",
      "logo": { "@type": "ImageObject", "url": "https://www.pdufa.bio/odin-favicon-512.png" }
    },
    "mainEntityOfPage": { "@type": "WebPage", "@id": "https://www.pdufa.bio/blog/odin-calls-asnd-yuviwel-approval" }
  }
];

export default function AsndBlogPost() {
  return (
    <>
      <StructuredData schemas={jsonLdSchemas} />

      <article style={{ backgroundColor: '#030712', color: '#e5e7eb', fontFamily: 'system-ui, sans-serif', lineHeight: '1.8' }}>
        {/* Hero */}
        <div style={{ maxWidth: '720px', margin: '0 auto', padding: '3rem 1.5rem 1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <span style={{ background: '#166534', color: '#bbf7d0', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', letterSpacing: '0.05em' }}>ODIN WIN</span>
            <span style={{ background: '#1e3a5f', color: '#93c5fd', padding: '0.25rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', letterSpacing: '0.05em' }}>ASND</span>
          </div>

          <h1 style={{ fontSize: '2.25rem', fontWeight: '800', color: '#f9fafb', lineHeight: '1.2', marginBottom: '0.75rem' }}>
            ODIN Called ASND YUVIWEL Before the Street Blinked
          </h1>

          <p style={{ color: '#9ca3af', fontSize: '0.9rem', marginBottom: '2rem' }}>
            March 1, 2026 &middot; 3 min read
          </p>
        </div>

        {/* Body */}
        <div style={{ maxWidth: '720px', margin: '0 auto', padding: '0 1.5rem 3rem' }}>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            On February 27th, the FDA approved Ascendis Pharma&apos;s YUVIWEL (navepegritide) for pediatric achondroplasia.
            If you were watching ODIN, you weren&apos;t surprised.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            Weeks before the decision, our 45-feature LightGBM ensemble scored ASND YUVIWEL at <strong style={{ color: '#4ade80' }}>88.9% approval probability</strong> — TIER_1.
            That&apos;s not a gut call. That&apos;s 2,200+ historical PDUFA outcomes, walk-forward validated at 0.9193 AUC, saying the data package was clean and the regulatory path was clear.
          </p>

          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f9fafb', marginTop: '2rem', marginBottom: '1rem' }}>
            Why ODIN Was Confident
          </h2>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            ASND had almost every box checked: Breakthrough Therapy Designation.
            Orphan Drug status. Phase 3 data showing statistically significant improvement in annualized height velocity.
            No AdCom — which historically signals the FDA doesn&apos;t need external convincing.
            Ascendis already had TransCon hGH approved earlier this month (Feb 7, ODIN score 95.5%) — proving their manufacturing and regulatory infrastructure was solid.
            When a sponsor walks in with back-to-back clean submissions, the model notices.
          </p>

          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f9fafb', marginTop: '2rem', marginBottom: '1rem' }}>
            The Market Underpriced It
          </h2>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            ASND moved +6% on the approval. Decent — but modest relative to the TIER_1 confidence level.
            The stock had already priced in much of the approval during the T-25 runup window, which ODIN&apos;s runup model flagged as an R2-tier expected move.
            Translation: the smart money was already positioning. If you waited for the headline, you caught the tail end.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            This is the whole point. ODIN doesn&apos;t tell you what happened. It tells you what&apos;s <em>likely</em> to happen — and gives you the probability with receipts.
          </p>

          <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '0.75rem', padding: '1.5rem', margin: '2rem 0' }}>
            <h3 style={{ color: '#4ade80', fontWeight: '700', fontSize: '1rem', marginBottom: '0.75rem' }}>ASND YUVIWEL — ODIN Scorecard</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.95rem' }}>
              <span style={{ color: '#9ca3af' }}>ODIN Score:</span><span style={{ color: '#4ade80', fontWeight: '600' }}>88.9%</span>
              <span style={{ color: '#9ca3af' }}>Tier:</span><span style={{ color: '#f9fafb' }}>TIER_1 (Favorable)</span>
              <span style={{ color: '#9ca3af' }}>PDUFA Date:</span><span style={{ color: '#f9fafb' }}>Feb 27, 2026</span>
              <span style={{ color: '#9ca3af' }}>Outcome:</span><span style={{ color: '#4ade80', fontWeight: '600' }}>✅ APPROVED</span>
              <span style={{ color: '#9ca3af' }}>Stock Move:</span><span style={{ color: '#f9fafb' }}>+6%</span>
              <span style={{ color: '#9ca3af' }}>Key Factors:</span><span style={{ color: '#f9fafb' }}>BTD, Orphan, No AdCom, Strong P3</span>
            </div>
          </div>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>
            ASND marks ODIN&apos;s 5th consecutive correct call in February 2026 on the approval side.
            Combined with 3 correctly predicted CRLs (IRON, RGNX, PHAR), that&apos;s 8 for 8 this month.
          </p>

          <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem', fontWeight: '600', color: '#f9fafb' }}>
            Not bad for a machine that doesn&apos;t read Twitter.
          </p>

          <div style={{ display: 'flex', gap: '1rem', marginTop: '2.5rem', flexWrap: 'wrap' }}>
            <Link href="/february-2026-pdufa-approvals" style={{ background: '#2563eb', color: '#fff', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', textDecoration: 'none', fontWeight: '600', fontSize: '0.95rem' }}>
              See Full February 2026 Roundup →
            </Link>
            <Link href="/odin" style={{ background: '#1f2937', color: '#e5e7eb', padding: '0.75rem 1.5rem', borderRadius: '0.5rem', textDecoration: 'none', fontWeight: '600', fontSize: '0.95rem', border: '1px solid #374151' }}>
              How ODIN Works
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
