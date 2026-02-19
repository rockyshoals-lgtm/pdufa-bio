import PdufaBio from '../../src/App';

export const metadata = {
  title: 'Biotech Catalyst Heatmap — PDUFA & Readout Visualization',
  description: 'Visual heatmap of upcoming biotech catalysts. See PDUFA dates, phase readouts & earnings at a glance. Color-coded by ODIN approval probability tier.',
  alternates: { canonical: 'https://pdufa.bio/heatmap' },
  openGraph: {
    title: 'Biotech Catalyst Heatmap | PDUFA.BIO',
    description: 'Visual heatmap of upcoming biotech catalysts. Color-coded by ODIN approval probability tier.',
    url: 'https://pdufa.bio/heatmap',
  },
  twitter: {
    title: 'Biotech Catalyst Heatmap | PDUFA.BIO',
    description: 'Visual heatmap of biotech catalysts color-coded by approval probability.',
  },
};

export default function HeatmapPage() {
  return <PdufaBio initialTab="heatmap" />;
}
