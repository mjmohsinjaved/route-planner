import { useMutation } from '@tanstack/react-query'

import { api } from '../client'
import type { TripRequest, TripResult } from '../../types'

/** POST /api/trips/: plans a trip and returns routes, checkpoints and the recommendation. */
export function usePlanTrip() {
  return useMutation({
    mutationFn: async (body: TripRequest) => (await api.post<TripResult>('/trips/', body)).data,
  })
}
