import PdufaBio from '../../src/App';

export const metadata = {
  title: 'Biotech Catalyst Feed — Live PDUFA & Readout Updates',
  description: 'Live feed of biotech catalyst updates including FDA PDUFA decisions, phase readouts & earnings. Community predictions and ODIN AI scoring.',
  alternates: { canonical: 'https://pdufa.bio/feed' },
  openGraph: {
    title: 'Biotech Catalyst Feed | PDUFA.BIO',
    description: 'Live feed of biotech catalyst updates. Community predictions and ODIN AI scoring.',
    url: 'https://pdufa.bio/feed',
  },
  twitter: {
    title: 'Biotech Catalyst Feed | PDUFA.BIO',
    description: 'Live biotech catalyst feed with community predictions.',
  },
};

export default function FeedPage() {
  return <PdufaBio initialTab="feed" />;
}
