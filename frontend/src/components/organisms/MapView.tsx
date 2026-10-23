import { useEffect, useMemo, useRef } from 'react'

import Box from '@mui/material/Box'
import { Marker, type GeoJSONSource } from 'maplibre-gl'

import { EMPTY_COLLECTION, MAP_SOURCES, usePlannerMap } from '../../hooks/use-planner-map'
import { useSelectedRouteId, useTripStore } from '../../store'
import { boundsOf, decodePolyline, riskSegments, type LngLat } from '../../utils/geo'
import { Legend, MapBanner } from '../molecules'
import { HeatmapLayer } from './HeatmapLayer'
import type { Heatmap, TripResult } from '../../types'

export interface MapViewProps {
  trip: TripResult | undefined
  heatmap: Heatmap | undefined
  /** One line over the empty map before the first trip; a map error replaces it. */
  hint?: string
}

const FIT_PADDING = { top: 60, bottom: 60, left: 60, right: 60 }

export function MapView({ trip, heatmap, hint }: MapViewProps) {
  const selectedRouteId = useSelectedRouteId(trip)
  const selectRoute = useTripStore((s) => s.selectRoute)

  const { containerRef, map, error } = usePlannerMap(selectRoute)
  const markersRef = useRef<Marker[]>([])

  // Decode each route once per trip
  const lines = useMemo(() => {
    const out: Record<string, LngLat[]> = {}
    for (const r of trip?.routes ?? []) out[r.id] = decodePolyline(r.geometry)
    return out
  }, [trip])

  // New trip: place origin/destination markers and fit the view
  useEffect(() => {
    if (!map) return
    markersRef.current.forEach((m) => m.remove())
    markersRef.current = []
    if (!trip) return

    for (const [place, label] of [
      [trip.origin, 'Start'],
      [trip.destination, 'End'],
    ] as const) {
      const el = document.createElement('div')
      el.className = 'endpoint-marker'
      el.textContent = label
      el.title = `${label}: ${place.name}`
      markersRef.current.push(new Marker({ element: el }).setLngLat([place.lon, place.lat]).addTo(map))
    }

    const all = Object.values(lines)
    if (all.length) map.fitBounds(boundsOf(all), { padding: FIT_PADDING, duration: 600 })
  }, [map, trip, lines])

  // Selection: grey for other routes, risk colors + checkpoints for the selected one
  useEffect(() => {
    if (!map) return
    const routes = trip?.routes ?? []
    const selected = routes.find((r) => r.id === selectedRouteId)
    const source = (name: string) => map.getSource(name) as GeoJSONSource

    source(MAP_SOURCES.routes).setData({
      type: 'FeatureCollection',
      features: routes.map((r) => ({
        type: 'Feature',
        properties: { id: r.id, selected: r.id === selectedRouteId },
        geometry: { type: 'LineString', coordinates: lines[r.id] ?? [] },
      })),
    })
    source(MAP_SOURCES.risk).setData(
      selected && lines[selected.id]
        ? riskSegments(lines[selected.id], selected.distance_mi, selected.checkpoints)
        : EMPTY_COLLECTION,
    )
    source(MAP_SOURCES.checkpoints).setData({
      type: 'FeatureCollection',
      features: (selected?.checkpoints ?? []).map((c) => ({
        type: 'Feature',
        properties: { level_score: c.level_score, data: JSON.stringify(c) },
        geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
      })),
    })
  }, [map, trip, selectedRouteId, lines])

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      <Box ref={containerRef} sx={{ position: 'absolute', inset: 0 }} />
      {error && <MapBanner severity="error">{error}</MapBanner>}
      {!error && hint && <MapBanner>{hint}</MapBanner>}
      <HeatmapLayer map={map} heatmap={heatmap} />
      <Legend />
    </Box>
  )
}

export default MapView
