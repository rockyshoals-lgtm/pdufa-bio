import PdufaBio from '../../src/App';

export const metadata = {
  title: 'About ODIN — FDA Approval Prediction Engine',
  description: 'How ODIN predicts FDA approvals: 63 parameters, 40B+ simulated scenarios, trained on 2,200+ PDUFA decisions & 2,000+ readouts (2015-2026). Machine learning meets biotech catalysts.',
  alternates: { canonical: 'https://pdufa.bio/about' },
  openGraph: {
    title: 'About ODIN Engine | PDUFA.BIO',
    description: 'How ODIN predicts FDA approvals using 63 parameters and 40B+ simulated scenarios.',
    url: 'https://pdufa.bio/about',
  },
  twitter: {
    title: 'About ODIN Engine | PDUFA.BIO',
    description: 'ODIN: 63 parameters, 40B+ scenarios, 2,200+ PDUFA training set.',
  },
};

export default function AboutPage() {
  return <PdufaBio initialTab="about" />;
}
