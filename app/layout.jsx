import './globals.css';
import StructuredData from '../components/StructuredData';

const jsonLdSchemas = [
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "PDUFA.BIO",
    "url": "https://pdufa.bio",
    "description": "FDA PDUFA Calendar & Biotech Catalyst Intelligence Platform",
    "potentialAction": {
      "@type": "SearchAction",
      "target": "https://pdufa.bio/?search={search_term_string}",
      "query-input": "required name=search_term_string"
    }
  },
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "PDUFA.BIO",
    "url": "https://pdufa.bio",
    "logo": "https://pdufa.bio/odin-favicon-512.png",
    "description": "AI-powered FDA PDUFA date tracking and biotech catalyst intelligence for quantitative investors",
    "sameAs": ["https://twitter.com/pdufa_bio"]
  },
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {
        "@type": "Question",
        "name": "What is a PDUFA date?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "A PDUFA (Prescription Drug User Fee Act) date is the FDA's target action date for making a regulatory decision on a drug application. These dates are critical binary events for biotech investors as they can cause significant stock price movements."
        }
      },
      {
        "@type": "Question",
        "name": "How does ODIN predict FDA approvals?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "ODIN is a machine learning scoring engine that analyzes 63 parameters across 40 billion+ simulated scenarios to generate approval probability scores for FDA PDUFA decisions. It is trained on 2,200+ historical PDUFA outcomes and 2,000+ phase readouts from 2015-2026."
        }
      },
      {
        "@type": "Question",
        "name": "What is a biotech catalyst calendar?",
        "acceptedAnswer": {
          "@type": "Answer",
          "text": "A biotech catalyst calendar tracks upcoming events that can significantly impact biotech stock prices, including FDA PDUFA dates, Phase 2/3 clinical trial readouts, advisory committee meetings, and quarterly earnings dates."
        }
      }
    ]
  }
];

export const metadata = {
  metadataBase: new URL('https://pdufa.bio'),
  title: {
    default: 'PDUFA Calendar & Biotech Catalyst Tracker 2026 | PDUFA.BIO',
    template: '%s | PDUFA.BIO',
  },
  description: 'Track FDA PDUFA dates, Phase 2/3 readouts & biotech earnings. AI-powered approval scores from ODIN. Free catalyst calendar for quant biotech investors.',
  keywords: ['PDUFA dates', 'FDA calendar', 'biotech catalyst calendar', 'PDUFA calendar 2026', 'FDA approval dates', 'biotech earnings calendar', 'phase 3 readouts', 'biotech catalyst tracker', 'FDA PDUFA date tracker', 'biotech trading'],
  robots: 'index, follow',
  verification: {
    google: 'wxUYp9cIYmJBBhioSJySRRU0SXCKtZKCFOI3nQPE0k8',
  },
  openGraph: {
    type: 'website',
    siteName: 'PDUFA.BIO',
    locale: 'en_US',
    images: [{ url: '/odin-favicon-512.png', width: 512, height: 512 }],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@pdufa_bio',
    images: ['/odin-favicon-512.png'],
  },
  icons: {
    icon: [
      { url: '/favicon.ico', type: 'image/x-icon' },
      { url: '/favicon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-16.png', sizes: '16x16', type: 'image/png' },
      { url: '/odin-favicon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/odin-favicon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <StructuredData schemas={jsonLdSchemas} />
      </head>
      <body className="bg-gray-950 text-white antialiased">
        <noscript>
          <div style={{ maxWidth: '800px', margin: '40px auto', padding: '20px', fontFamily: 'sans-serif', color: '#e5e7eb' }}>
            <h1>PDUFA.BIO — FDA PDUFA Calendar & Biotech Catalyst Intelligence</h1>
            <p>Track every FDA PDUFA date, Phase 2/3 readout, and biotech earnings event — scored by AI. PDUFA.BIO&apos;s ODIN scoring engine analyzes 2,200+ historical FDA decisions to generate real-time approval probability scores.</p>
            <h2>FDA PDUFA Calendar 2026</h2>
            <p>Complete calendar of upcoming FDA PDUFA target action dates for biotech stocks. Filter by ticker, drug, indication, and therapeutic area.</p>
            <h2>Biotech Catalyst Calendar</h2>
            <p>Track PDUFA dates, Phase 2 and Phase 3 clinical trial readouts, and biotech earnings in a unified, filterable catalyst calendar updated daily.</p>
            <h2>Biotech Earnings Calendar 2026</h2>
            <p>Upcoming biotech earnings dates alongside FDA catalysts. Plan event-driven trades around earnings and regulatory decisions.</p>
            <h2>ODIN AI Scoring Engine</h2>
            <p>ODIN v10.69 scores every upcoming FDA PDUFA date using 63 parameters across 40 billion+ simulated scenarios. Trained on 2,200+ PDUFAs and 2,000+ phase readouts from 2015-2026.</p>
            <h2>Built for Quantitative Investors</h2>
            <p>Screener, heatmaps, paper trading, IV crush analysis — all calibrated around FDA binary events. Export PDUFA dates to .ICS or CSV for your trading workflow.</p>
            <p><a href="https://pdufa.bio/">View the full FDA PDUFA Calendar</a></p>
          </div>
        </noscript>
        {children}
      </body>
    </html>
  );
}
