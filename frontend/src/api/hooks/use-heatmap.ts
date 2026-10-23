import { useQuery, type UseQueryResult } from '@tanstack/react-query'

import { api, errorMessage, statusOf } from '../client'
import { queryKeys } from '../query-keys'
import type { Heatmap } from '../../types'

const RATE_LIMITED = 429
// The backend sends 429 when Open-Meteo's per-minute allowance is used up; it resets every minute.
const RATE_LIMIT_RETRY_MS = 61_000

const isRateLimited = (error: unknown) => statusOf(error) === RATE_LIMITED

/** All 49 hours of corridor risk for a trip, fetched once; the slider never refetches. */
export function useHeatmap(tripId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.heatmap(tripId),
    queryFn: async ({ signal }) => (await api.get<Heatmap>(`/trips/${tripId}/heatmap/`, { signal })).data,
    enabled: Boolean(tripId),
    staleTime: Infinity,
    // Only a rate limit is worth waiting for; any other failure surfaces at once
    retry: (failureCount, error) => isRateLimited(error) && failureCount < 1,
    retryDelay: RATE_LIMIT_RETRY_MS,
  })
}

/** One line for the slider while the heatmap is not available yet, or empty once it is. */
export function heatmapStatus(query: UseQueryResult<Heatmap>): string {
  if (query.data) return ''
  if (query.isPending && query.failureCount > 0) return 'Weather limit reached, retrying in a minute…'
  if (query.isPending) return 'Loading heatmap…'
  if (query.isError) return errorMessage(query.error)
  return ''
}
