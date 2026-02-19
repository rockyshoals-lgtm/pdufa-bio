import PdufaBio from '../../src/App';

export const metadata = {
  title: 'Biotech Catalyst Screener — Filter PDUFA Dates & Readouts',
  description: 'Screen biotech catalysts by type, tier, therapeutic area & date. Find FDA PDUFA dates, phase readouts & earnings for event-driven trading.',
  alternates: { canonical: 'https://pdufa.bio/screener' },
  openGraph: {
    title: 'Biotech Catalyst Screener | PDUFA.BIO',
    description: 'Screen biotech catalysts by type, tier, therapeutic area & date. Find FDA PDUFA dates, phase readouts & earnings.',
    url: 'https://pdufa.bio/screener',
  },
  twitter: {
    title: 'Biotech Catalyst Screener | PDUFA.BIO',
    description: 'Screen biotech catalysts by type, tier, TA & date.',
  },
};

export default function ScreenerPage() {
  return <PdufaBio initialTab="screener" />;
}
