// WakeQuest design tokens — dark neon glassmorphic
export const colors = {
  bg: '#070B14',
  bgElevated: '#0C1220',
  glass: 'rgba(255,255,255,0.055)',
  glassBorder: 'rgba(255,255,255,0.10)',
  glassBright: 'rgba(255,255,255,0.12)',

  violet: '#8B5CF6',
  cyan: '#22D3EE',
  pink: '#F472B6',
  amber: '#FBBF24',
  green: '#34D399',
  red: '#F87171',

  text: '#F4F6FB',
  textDim: 'rgba(244,246,251,0.55)',
  textFaint: 'rgba(244,246,251,0.30)',
} as const;

export const gradients = {
  primary: [colors.violet, colors.cyan] as const,
  sunrise: ['#F472B6', '#FBBF24'] as const,
  danger: ['#F87171', '#F472B6'] as const,
  pet: ['#22D3EE', '#8B5CF6'] as const,
};

export const radius = { sm: 12, md: 18, lg: 26, pill: 999 } as const;

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 36 } as const;

export const glow = (color: string, r = 18) => ({
  shadowColor: color,
  shadowOpacity: 0.55,
  shadowRadius: r,
  shadowOffset: { width: 0, height: 0 },
  elevation: 8,
});

export const type = {
  clock: { fontSize: 72, fontWeight: '200' as const, letterSpacing: -2, color: colors.text },
  h1: { fontSize: 28, fontWeight: '700' as const, color: colors.text },
  h2: { fontSize: 20, fontWeight: '600' as const, color: colors.text },
  body: { fontSize: 15, fontWeight: '400' as const, color: colors.textDim },
  label: {
    fontSize: 12,
    fontWeight: '600' as const,
    letterSpacing: 1.4,
    textTransform: 'uppercase' as const,
    color: colors.textFaint,
  },
};
