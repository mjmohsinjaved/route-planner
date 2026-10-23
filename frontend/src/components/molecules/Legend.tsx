import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import { useTheme } from '@mui/material/styles'
import Typography from '@mui/material/Typography'

import { RISK_COLORS, RISK_LEVELS } from '../../theme/risk'
import { Swatch } from '../atoms'

const OTHER_ROUTES_LABEL = 'Other routes'

/** Risk color key. A column on wide screens, one compact row on phones. */
export function Legend() {
  const theme = useTheme()
  const items: [string, string][] = [
    ...RISK_LEVELS.map((level) => [level, RISK_COLORS[level]] as [string, string]),
    [OTHER_ROUTES_LABEL, theme.palette.map.routeOther],
  ]

  return (
    <Paper
      elevation={2}
      sx={{
        position: 'absolute',
        left: { xs: 8, md: 12 },
        right: { xs: 8, md: 'auto' },
        bottom: { xs: 8, md: 28 },
        px: 1.5,
        py: { xs: 0.75, md: 1 },
        zIndex: 1,
        borderRadius: 2,
        display: 'flex',
        flexDirection: { xs: 'row', md: 'column' },
        flexWrap: 'wrap',
        columnGap: 1.5,
      }}
    >
      <Typography variant="overline" color="text.secondary" component="div" sx={{ fontSize: 10, display: { xs: 'none', md: 'block' } }}>
        Risk
      </Typography>
      {items.map(([label, color]) => (
        <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, md: 1 }, py: 0.25 }}>
          <Swatch color={color} width={{ xs: 12, md: 22 }} />
          <Typography variant="caption" color={label === OTHER_ROUTES_LABEL ? 'text.secondary' : 'text.primary'}>
            {label}
          </Typography>
        </Box>
      ))}
    </Paper>
  )
}
