import PdufaBio from '../../src/App';

export const metadata = {
  title: 'PDUFA Prediction Leaderboard — Top Biotech Forecasters',
  description: 'See who\'s best at predicting FDA PDUFA outcomes. Community leaderboard ranked by prediction accuracy on biotech catalyst events.',
  alternates: { canonical: 'https://pdufa.bio/leaderboard' },
  openGraph: {
    title: 'Prediction Leaderboard | PDUFA.BIO',
    description: 'Community leaderboard ranked by PDUFA prediction accuracy.',
    url: 'https://pdufa.bio/leaderboard',
  },
  twitter: {
    title: 'Prediction Leaderboard | PDUFA.BIO',
    description: 'Top biotech catalyst forecasters ranked by accuracy.',
  },
};

export default function LeaderboardPage() {
  return <PdufaBio initialTab="leaderboard" />;
}
