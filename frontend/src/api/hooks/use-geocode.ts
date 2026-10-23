import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { useDebounced } from '../../hooks/use-debounced'
import { api } from '../client'
import { queryKeys } from '../query-keys'
import type { Place } from '../../types'

const DEBOUNCE_MS = 300
/** Shortest text that triggers a search; the field's hint text uses it too. */
export const MIN_QUERY_LENGTH = 2
const STALE_MS = 24 * 60 * 60 * 1000 // the backend caches geocode results for a day too

/** Place suggestions for the autocomplete, debounced and cached per query. */
export function useGeocode(text: string) {
  const query = useDebounced(text.trim(), DEBOUNCE_MS)
  return useQuery({
    queryKey: queryKeys.geocode(query),
    queryFn: async ({ signal }) => (await api.get<Place[]>('/geocode/', { params: { q: query }, signal })).data,
    enabled: query.length >= MIN_QUERY_LENGTH,
    staleTime: STALE_MS,
    placeholderData: keepPreviousData,
  })
}
