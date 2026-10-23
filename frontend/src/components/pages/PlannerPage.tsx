import { Suspense, lazy } from 'react'

import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Typography from '@mui/material/Typography'

import { errorMessage, heatmapStatus, useHeatmap, usePlanTrip } from '../../api'
import { useTripStore } from '../../store'
import { EmptyState, HeatmapSlider, MapBanner } from '../molecules'
import { RouteList, TripForm } from '../organisms'
import { PlannerLayout } from '../templates'
import type { TripRequest } from '../../types'

// MapLibre is the largest dependency; loading it in its own chunk lets the form paint first.
const MapView = lazy(() => import('../organisms/MapView'))
// Shown over the empty map, including while the map chunk is still downloading
const MAP_HINT = 'Plan a trip to see the routes, checkpoints and weather heatmap here.'

export default function PlannerPage() {
  const plan = usePlanTrip()
  const trip = plan.data
  const heatmap = useHeatmap(trip?.id) // loads once per trip, right after it is planned
  const startTrip = useTripStore((s) => s.startTrip)

  const handleSubmit = (request: TripRequest) =>
    plan.mutate(request, { onSuccess: (data) => startTrip(data.id) })

  const isEmpty = !trip && !plan.isPending && !plan.isError

  return (
    <PlannerLayout
      isLoading={plan.isPending}
      sidebar={
        <>
          <Typography variant="h1">Route Planner</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2.5 }}>
            Compare 3 truck routes by the weather you'll meet on the way.
          </Typography>

          <TripForm onSubmit={handleSubmit} isLoading={plan.isPending} />

          <Divider sx={{ my: 2.5 }} />

          {plan.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errorMessage(plan.error)}
            </Alert>
          )}

          {isEmpty ? <EmptyState /> : <RouteList trip={trip} isLoading={plan.isPending} />}
        </>
      }
      map={
        <>
          <Suspense
            fallback={
              <Box sx={{ position: 'absolute', inset: 0, bgcolor: 'background.default' }}>
                {isEmpty && <MapBanner>{MAP_HINT}</MapBanner>}
              </Box>
            }
          >
            <MapView trip={trip} heatmap={heatmap.data} hint={isEmpty ? MAP_HINT : undefined} />
          </Suspense>
          {trip && <HeatmapSlider heatmap={heatmap.data} statusText={heatmapStatus(heatmap)} />}
        </>
      }
    />
  )
}
