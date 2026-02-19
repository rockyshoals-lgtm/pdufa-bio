import PdufaBio from '../src/App';

export const metadata = {
  title: 'PDUFA Calendar & Biotech Catalyst Tracker 2026 | PDUFA.BIO',
  description: 'Track FDA PDUFA dates, Phase 2/3 readouts & biotech earnings. AI-powered approval scores from ODIN. Free catalyst calendar for quant biotech investors.',
  alternates: { canonical: 'https://pdufa.bio/' },
  openGraph: {
    title: 'PDUFA.BIO — FDA PDUFA Calendar & Biotech Catalyst Intelligence',
    description: 'Track FDA PDUFA dates, Phase 2/3 readouts & biotech earnings. AI-powered approval scores from ODIN for quant biotech investors.',
    url: 'https://pdufa.bio/',
  },
  twitter: {
    title: 'PDUFA.BIO — FDA PDUFA Calendar & Biotech Catalyst Intelligence',
    description: 'Track FDA PDUFA dates, Phase 2/3 readouts & biotech earnings. AI approval scores from ODIN.',
  },
};

export default function DashboardPage() {
  return <PdufaBio initialTab="dashboard" />;
}
