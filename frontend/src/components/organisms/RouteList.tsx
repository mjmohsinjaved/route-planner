import Alert from '@mui/material/Alert'
import Skeleton from '@mui/material/Skeleton'
import Stack from '@mui/material/Stack'

import { useSelectedRouteId, useTripStore } from '../../store'
import { RouteCard } from '../molecules'
import type { TripResult } from '../../types'

export interface RouteListProps {
  trip: TripResult | undefined
  isLoading: boolean
}

const SKELETON_COUNT = 3

export function RouteList({ trip, isLoading }: RouteListProps) {
  const selectedRouteId = useSelectedRouteId(trip)
  const selectRoute = useTripStore((s) => s.selectRoute)

  if (isLoading) {
    return (
      <Stack spacing={1.5} aria-busy="true">
        {Array.from({ length: SKELETON_COUNT }, (_, i) => (
          <Skeleton key={i} variant="rounded" height={150} />
        ))}
      </Stack>
    )
  }
  if (!trip) return null

  // Recommended route first, then the ranking order from the backend
  const order = trip.ranking.length ? trip.ranking : trip.routes.map((r) => r.id)
  const routes = [...trip.routes].sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))

  return (
    <Stack spacing={1.5}>
      {trip.unsafe && (
        <Alert severity="error" variant="outlined">
          Every route crosses No Travel weather at this departure time. Consider leaving later.
        </Alert>
      )}
      {routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          isRecommended={route.id === trip.recommended_route_id}
          isSelected={route.id === selectedRouteId}
          reason={route.id === trip.recommended_route_id ? trip.recommendation_reason : undefined}
          onSelect={() => selectRoute(route.id)}
        />
      ))}
    </Stack>
  )
}
