import PdufaBio from '../../src/App';

export const metadata = {
  title: 'Biotech Market Intel — Social Sentiment & Options Flow',
  description: 'Biotech market intelligence: social sentiment analysis, unusual options activity, and institutional positioning around FDA PDUFA dates and catalysts.',
  alternates: { canonical: 'https://pdufa.bio/intel' },
  openGraph: {
    title: 'Biotech Market Intel | PDUFA.BIO',
    description: 'Social sentiment, options flow, and institutional positioning around PDUFA dates.',
    url: 'https://pdufa.bio/intel',
  },
  twitter: {
    title: 'Biotech Market Intel | PDUFA.BIO',
    description: 'Biotech sentiment and options flow around FDA catalysts.',
  },
};

export default function IntelPage() {
  return <PdufaBio initialTab="intel" />;
}
