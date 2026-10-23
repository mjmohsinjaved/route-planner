import { createTheme } from '@mui/material/styles'

import { tokens } from './tokens'

// Map colors as a palette group so MUI components (Legend) can read them and
// `cssVariables: true` emits them as --mui-palette-map-* for plain CSS.
declare module '@mui/material/styles' {
  interface Palette {
    map: { routeOther: string; casing: string }
  }
  interface PaletteOptions {
    map?: { routeOther: string; casing: string }
  }
}

const { color, font, radius } = tokens

export const theme = createTheme({
  cssVariables: true,
  // `md` is the tablet width from the PRD (768 px): the map sits beside the sidebar from there up
  breakpoints: { values: { xs: 0, sm: 600, md: 768, lg: 1200, xl: 1536 } },
  palette: {
    mode: 'light',
    primary: { main: color.primary, contrastText: color.onPrimary },
    secondary: { main: color.secondary },
    background: { default: color.background, paper: color.surface },
    text: { primary: color.textPrimary, secondary: color.textSecondary },
    divider: color.divider,
    map: { routeOther: color.map.routeOther, casing: color.map.casing },
  },
  shape: { borderRadius: radius.md },
  typography: {
    fontFamily: font.sans,
    h1: { fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.01em' },
    subtitle2: { fontWeight: 600 },
    overline: { fontWeight: 700, letterSpacing: '0.08em', lineHeight: 1.6 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiCard: { defaultProps: { variant: 'outlined' } },
    MuiTextField: { defaultProps: { size: 'small', fullWidth: true } },
    MuiToggleButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } } },
  },
})
