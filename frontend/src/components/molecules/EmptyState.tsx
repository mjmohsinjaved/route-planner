import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

const STEPS = [
  'Pick an origin and a destination, or tap an example below the form.',
  'Three truck routes are scored by the wind, rain and snow forecast at each checkpoint.',
  'The safest route is recommended and colored on the map; a slider shows the next 48 hours.',
]

/** Sidebar guidance before the first trip is planned, where the route cards will appear. */
export function EmptyState() {
  return (
    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default', borderStyle: 'dashed' }}>
      <Typography variant="subtitle2" gutterBottom>
        Your routes will appear here
      </Typography>
      <Stack component="ol" spacing={0.75} sx={{ m: 0, pl: 2.25, color: 'text.secondary' }}>
        {STEPS.map((step) => (
          <Typography key={step} component="li" variant="body2">
            {step}
          </Typography>
        ))}
      </Stack>
    </Paper>
  )
}
