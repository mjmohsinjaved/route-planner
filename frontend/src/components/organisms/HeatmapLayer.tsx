import { useEffect, useMemo } from 'react'

import type { FeatureCollection } from 'geojson'
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl'

import { EMPTY_COLLECTION, MAP_LAYERS, MAP_SOURCES } from '../../hooks/use-planner-map'
import { useTripStore } from '../../store'
import { riskColorExpression } from '../../theme/risk'
import { tokens } from '../../theme/tokens'
import type { Heatmap } from '../../types'

const { transparent } = tokens.color.map

export interface HeatmapLayerProps {
  /** null until the map's style has loaded */
  map: MapLibreMap | null
  heatmap: Heatmap | undefined
}

/**
 * Every grid point becomes one feature carrying all 49 hourly scores (h0..h48).
 * The slider then only changes which property colors the circles, so moving
 * it never re-sends data or hits the network.
 */
function toFeatures(heatmap: Heatmap): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: heatmap.points.map(([lat, lon], i) => {
      const properties: Record<string, number> = {}
      heatmap.values.forEach((row, h) => (properties[`h${h}`] = row[i]))
      return { type: 'Feature', properties, geometry: { type: 'Point', coordinates: [lon, lat] } }
    }),
  }
}

/** Soft colored blobs around the routes; each point shows its own level. Renders nothing itself. */
export function HeatmapLayer({ map, heatmap }: HeatmapLayerProps) {
  // Read the slider state here so its ticks re-render only this (render-null) component
  const hour = useTripStore((s) => s.heatmapHour)
  const isVisible = useTripStore((s) => s.isHeatmapVisible)
  const features = useMemo(() => (heatmap ? toFeatures(heatmap) : EMPTY_COLLECTION), [heatmap])

  // Source and layer once per map, below the routes so they draw on top
  useEffect(() => {
    if (!map || map.getSource(MAP_SOURCES.heatmap)) return
    map.addSource(MAP_SOURCES.heatmap, { type: 'geojson', data: EMPTY_COLLECTION })
    map.addLayer(
      {
        id: MAP_LAYERS.heatmap,
        type: 'circle',
        source: MAP_SOURCES.heatmap,
        layout: { visibility: 'none' },
        paint: {
          // Blob radius follows the ~55 km grid spacing: blobs merge into a band at trip zoom
          'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 5, 5, 20, 8, 160, 11, 1200],
          'circle-color': riskColorExpression('h0', transparent),
          'circle-opacity': 0.32,
          'circle-blur': 0.7,
        },
      },
      MAP_LAYERS.routesOther,
    )
  }, [map])

  // Data: only when a new heatmap arrives
  useEffect(() => {
    if (!map) return
    const source = map.getSource(MAP_SOURCES.heatmap) as GeoJSONSource | undefined
    source?.setData(features)
  }, [map, features])

  // Hour and toggle: paint and layout changes only
  useEffect(() => {
    if (!map || !map.getLayer(MAP_LAYERS.heatmap)) return
    map.setPaintProperty(MAP_LAYERS.heatmap, 'circle-color', riskColorExpression(`h${hour}`, transparent))
    map.setLayoutProperty(MAP_LAYERS.heatmap, 'visibility', isVisible && heatmap ? 'visible' : 'none')
  }, [map, hour, isVisible, heatmap])

  return null
}
