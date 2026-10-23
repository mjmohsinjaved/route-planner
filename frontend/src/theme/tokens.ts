import type { RiskLevel } from '../types'

/**
 * Design tokens: the only place in the project where raw colors, fonts and radii live.
 * Everything else reads them through the MUI theme (`theme.palette.*`), the CSS
 * variables MUI emits from it (`--mui-palette-*`), or the helpers in `risk.ts`.
 */
export const tokens = {
  color: {
    primary: '#0E4A5A',
    onPrimary: '#ffffff',
    secondary: '#E8505B',
    background: '#F4F6F7',
    surface: '#ffffff',
    textPrimary: '#14232A',
    textSecondary: '#5A6B72',
    divider: '#E1E6E8',
    risk: {
      Low: '#2E9E5B',
      Moderate: '#E0B000',
      High: '#EF7D22',
      Severe: '#D62839',
      'No Travel': '#5B1A6E',
    } satisfies Record<RiskLevel, string>,
    map: {
      routeOther: '#8A9BA2',
      casing: '#ffffff',
      transparent: 'rgba(0,0,0,0)',
    },
  },
  font: {
    sans: '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  },
  radius: {
    md: 10,
  },
} as const
