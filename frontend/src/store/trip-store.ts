import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

import type { TripResult } from '../types'

/**
 * UI state shared by the route list, the map and the heatmap slider.
 * Server data (the trip, the heatmap) stays in TanStack Query.
 */
export interface TripUiState {
  /** The trip the selection belongs to; a different trip ignores it. */
  tripId: string | null
  selectedRouteId: string | null
  heatmapHour: number
  isHeatmapVisible: boolean

  selectRoute: (id: string) => void
  setHeatmapHour: (hour: number) => void
  setHeatmapVisible: (visible: boolean) => void
  /** A new trip arrived: clear the previous choice and rewind the slider. */
  startTrip: (tripId: string) => void
}

const initialState = {
  tripId: null,
  selectedRouteId: null,
  heatmapHour: 0,
  isHeatmapVisible: true,
}

export const useTripStore = create<TripUiState>()(
  devtools(
    (set) => ({
      ...initialState,

      selectRoute: (id) => set({ selectedRouteId: id }, false, 'trip/selectRoute'),

      setHeatmapHour: (hour) => set({ heatmapHour: hour }, false, 'trip/setHeatmapHour'),

      setHeatmapVisible: (visible) => set({ isHeatmapVisible: visible }, false, 'trip/setHeatmapVisible'),

      startTrip: (tripId) => set({ tripId, selectedRouteId: null, heatmapHour: 0 }, false, 'trip/startTrip'),
    }),
    { name: 'TripStore', enabled: import.meta.env.DEV },
  ),
)

/**
 * The route to highlight for `trip`: the user's choice on this trip, otherwise the
 * recommended route. This is the only place that rule lives, so a freshly planned
 * trip never renders with every route grey or with the previous trip's choice.
 */
export function useSelectedRouteId(trip: TripResult | undefined): string | null {
  const tripId = useTripStore((s) => s.tripId)
  const selectedRouteId = useTripStore((s) => s.selectedRouteId)
  if (!trip) return null
  return tripId === trip.id && selectedRouteId ? selectedRouteId : trip.recommended_route_id
}
