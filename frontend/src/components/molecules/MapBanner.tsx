import type { ReactNode } from 'react'

import Alert from '@mui/material/Alert'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'

export interface MapBannerProps {
  /** An error alert; omitted, the banner is a quiet hint. */
  severity?: 'error'
  children: ReactNode
}

// The one place that knows where a sentence over the map goes
const PLACEMENT = {
  position: 'absolute',
  top: 12,
  left: '50%',
  transform: 'translateX(-50%)',
  maxWidth: 'calc(100% - 24px)',
  zIndex: 2,
} as const

/** One line floating at the top of the map: a hint before the first trip, or a map error. */
export function MapBanner({ severity, children }: MapBannerProps) {
  if (severity) {
    return (
      <Alert severity={severity} sx={{ ...PLACEMENT, width: 'max-content' }}>
        {children}
      </Alert>
    )
  }
  return (
    <Paper elevation={2} sx={{ ...PLACEMENT, px: 1.5, py: 0.75, borderRadius: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
        {children}
      </Typography>
    </Paper>
  )
}
