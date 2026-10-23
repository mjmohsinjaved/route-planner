import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

export interface StatProps {
  label: string
  value: string
  /** Show the value in the error color, for example miles at a dangerous level. */
  isWarning?: boolean
}

/** A small labelled figure, used in route cards. */
export function Stat({ label, value, isWarning = false }: StatProps) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" component="div">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600, color: isWarning ? 'error.main' : 'text.primary' }}>
        {value}
      </Typography>
    </Box>
  )
}
