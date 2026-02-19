import PdufaBio from '../../src/App';

export const metadata = {
  title: 'Biotech Options Paper Trading — Practice PDUFA Catalyst Trades',
  description: 'Practice trading biotech options around FDA PDUFA dates and catalysts with zero risk. Paper trading simulator for event-driven biotech strategies.',
  alternates: { canonical: 'https://pdufa.bio/trade' },
  openGraph: {
    title: 'Biotech Paper Trading | PDUFA.BIO',
    description: 'Practice trading biotech options around FDA PDUFA dates with zero risk.',
    url: 'https://pdufa.bio/trade',
  },
  twitter: {
    title: 'Biotech Paper Trading | PDUFA.BIO',
    description: 'Practice biotech options trading around PDUFA catalysts.',
  },
};

export default function TradePage() {
  return <PdufaBio initialTab="trade" />;
}
