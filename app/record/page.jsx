import PdufaBio from '../../src/App';

export const metadata = {
  title: 'ODIN Track Record — FDA Approval Prediction Accuracy',
  description: 'Verified track record of ODIN\'s FDA approval predictions. SHA-256 proofs, historical accuracy by tier, therapeutic area success rates across 2,200+ PDUFA decisions.',
  alternates: { canonical: 'https://pdufa.bio/record' },
  openGraph: {
    title: 'ODIN Prediction Track Record | PDUFA.BIO',
    description: 'Verified track record of ODIN\'s FDA approval predictions with SHA-256 proofs.',
    url: 'https://pdufa.bio/record',
  },
  twitter: {
    title: 'ODIN Prediction Track Record | PDUFA.BIO',
    description: 'ODIN FDA approval prediction accuracy with SHA-256 verification.',
  },
};

export default function RecordPage() {
  return <PdufaBio initialTab="record" />;
}
