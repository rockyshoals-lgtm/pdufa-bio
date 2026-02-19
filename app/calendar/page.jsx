import PdufaBio from '../../src/App';

export const metadata = {
  title: 'FDA PDUFA Calendar 2026 — Biotech Catalyst Dates by Ticker',
  description: 'Complete FDA PDUFA dates for 2026. PDUFA decisions, phase readouts, earnings dates. Filter by ticker, type & date. AI approval scores from ODIN.',
  alternates: { canonical: 'https://pdufa.bio/calendar' },
  openGraph: {
    title: 'FDA PDUFA Calendar 2026 | PDUFA.BIO',
    description: 'Complete FDA PDUFA dates for 2026. PDUFA decisions, phase readouts, earnings dates. Filter by ticker, type & date.',
    url: 'https://pdufa.bio/calendar',
  },
  twitter: {
    title: 'FDA PDUFA Calendar 2026 | PDUFA.BIO',
    description: 'Complete FDA PDUFA dates for 2026 with AI approval scores.',
  },
};

export default function CalendarPage() {
  return <PdufaBio initialTab="calendar" />;
}
