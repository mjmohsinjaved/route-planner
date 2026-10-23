/** Hierarchical query keys, one place so invalidation and caching stay consistent. */
export const queryKeys = {
  geocode: (query: string) => ['geocode', query.toLowerCase()] as const,
  heatmap: (tripId: string | undefined) => ['heatmap', tripId] as const,
}
