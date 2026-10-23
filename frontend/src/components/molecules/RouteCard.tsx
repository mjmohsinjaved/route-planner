import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import { formatDuration, formatMiles, formatTime } from '../../utils/format'
import { Stat } from '../atoms'
import { RiskBar } from './RiskBar'
import type { RouteResult } from '../../types'

export interface RouteCardProps {
  route: RouteResult
  isRecommended: boolean
  isSelected: boolean
  reason?: string
  onSelect: () => void
}

export function RouteCard({ route, isRecommended, isSelected, reason, onSelect }: RouteCardProps) {
  return (
    <Card
      sx={{
        borderColor: isSelected ? 'primary.main' : 'divider',
        borderWidth: isSelected ? 2 : 1,
        transition: 'border-color 120ms',
      }}
    >
      <CardActionArea onClick={onSelect} aria-pressed={isSelected} sx={{ p: isSelected ? 1.75 : 1.875 }}>
        <Stack direction="row" sx={{ alignItems: 'center', mb: 1.25 }} spacing={1}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            Route {route.id}
          </Typography>
          {isRecommended && <Chip label="Recommended" color="primary" size="small" />}
          <Box sx={{ flex: 1 }} />
          <Typography variant="body2" color="text.secondary">
            Avg risk {route.avg_risk.toFixed(2)}
          </Typography>
        </Stack>

        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', rowGap: 1, columnGap: 1.5, mb: 1.5 }}>
          <Stat label="Distance" value={formatMiles(route.distance_mi)} />
          <Stat label="Drive time" value={formatDuration(route.duration_min)} />
          <Stat label="Arrives" value={formatTime(route.arrival)} />
          {/* One decimal so a short bad stretch (0.4 mi) never reads as 0, matching the reason sentence */}
          <Stat label="No Travel" value={formatMiles(route.no_travel_mi, 1)} isWarning={route.no_travel_mi > 0} />
          <Stat label="Severe" value={formatMiles(route.severe_mi, 1)} isWarning={route.severe_mi > 0} />
          <Stat label="High" value={formatMiles(route.high_mi, 1)} />
        </Box>

        <RiskBar checkpoints={route.checkpoints} />

        {reason && (
          <Typography variant="body2" sx={{ mt: 1.5, color: 'text.secondary' }}>
            {reason}
          </Typography>
        )}
      </CardActionArea>
    </Card>
  )
}
