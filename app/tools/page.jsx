import PdufaBio from '../../src/App';

export const metadata = {
  title: 'Biotech Trading Tools — IV Crush Calculator & More',
  description: 'Free biotech trading tools: IV crush calculator, options profit/loss estimator, catalyst timeline builder. Built for event-driven biotech traders.',
  alternates: { canonical: 'https://pdufa.bio/tools' },
  openGraph: {
    title: 'Biotech Trading Tools | PDUFA.BIO',
    description: 'IV crush calculator, options P/L estimator, catalyst timeline builder.',
    url: 'https://pdufa.bio/tools',
  },
  twitter: {
    title: 'Biotech Trading Tools | PDUFA.BIO',
    description: 'Free biotech trading tools for event-driven strategies.',
  },
};

export default function ToolsPage() {
  return <PdufaBio initialTab="tools" />;
}
