import { useEffect, useRef, useState, type RefObject } from 'react'

import type { FeatureCollection } from 'geojson'
import { Map as MapLibreMap, NavigationControl, Popup, setWorkerUrl, type MapLayerMouseEvent } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css' // imported here, not in main.tsx, so it loads with the lazy map chunk

import { RISK_COLOR_EXPRESSION } from '../theme/risk'
import { tokens } from '../theme/tokens'
import { checkpointPopupHtml } from '../utils/checkpoint-popup'
import type { LngLat } from '../utils/geo'
import type { Checkpoint } from '../types'

// Bundlers move MapLibre's code, so tell it where its web worker file ended up.
setWorkerUrl(workerUrl)

const MAP_STYLE = import.meta.env.VITE_MAP_STYLE ?? 'https://tiles.openfreemap.org/styles/positron'
const US_CENTER: LngLat = [-98.5, 39.8]
const INITIAL_ZOOM = 3.4
export const EMPTY_COLLECTION: FeatureCollection = { type: 'FeatureCollection', features: [] }

export const MAP_UNSUPPORTED_MESSAGE = 'This browser cannot draw the map (WebGL is off or unsupported). Routes are still listed in the sidebar.'
export const MAP_LOAD_FAILED_MESSAGE = 'The map could not be loaded. Check your connection and reload the page.'

/** Source and layer ids shared with the components that update them. */
export const MAP_SOURCES = { routes: 'routes', risk: 'risk', checkpoints: 'checkpoints', heatmap: 'heatmap' } as const
export const MAP_LAYERS = {
  routesOther: 'routes-other',
  riskCasing: 'risk-casing',
  riskLine: 'risk-line',
  checkpoints: 'checkpoints',
  heatmap: 'heatmap', // added by HeatmapLayer, below routesOther
} as const
const { routeOther, casing } = tokens.color.map // map layers are not themed at runtime

export interface UsePlannerMapReturn {
  containerRef: RefObject<HTMLDivElement | null>
  /** null until the style has loaded and the sources and layers exist. */
  map: MapLibreMap | null
  /** One sentence when the map cannot be created or its style failed to load. */
  error: string | null
}

/** Creates the MapLibre map once, with the route, risk and checkpoint layers and their interactions. */
export function usePlannerMap(onSelectRoute: (id: string) => void): UsePlannerMapReturn {
  const containerRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<MapLibreMap | null>(null)
  const [error, setError] = useState<string | null>(null)
  const onSelectRef = useRef(onSelectRoute)

  useEffect(() => {
    onSelectRef.current = onSelectRoute
  }, [onSelectRoute])

  useEffect(() => {
    if (!containerRef.current) return
    let instance: MapLibreMap
    try {
      instance = new MapLibreMap({
        container: containerRef.current,
        style: MAP_STYLE,
        center: US_CENTER,
        zoom: INITIAL_ZOOM,
        attributionControl: { compact: true },
      })
    } catch (cause) {
      // MapLibre throws synchronously when WebGL 2 is unavailable; the only way to learn
      // that is to try, so this one setState inside the effect is deliberate.
      console.error('MapLibre could not start', cause)
      const isWebGL = /webgl/i.test(cause instanceof Error ? cause.message : String(cause))
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setError(isWebGL ? MAP_UNSUPPORTED_MESSAGE : MAP_LOAD_FAILED_MESSAGE)
      return
    }
    instance.addControl(new NavigationControl({ showCompass: false }), 'top-right')

    // Until the style has loaded, any error means the base map is not coming. Later
    // tile errors are transient (MapLibre retries them) and are only logged.
    let isLoaded = false
    instance.on('error', (e) => {
      console.error('MapLibre error', e.error)
      if (!isLoaded) setError(MAP_LOAD_FAILED_MESSAGE)
    })

    instance.on('load', () => {
      isLoaded = true
      setError(null)
      for (const source of [MAP_SOURCES.routes, MAP_SOURCES.risk, MAP_SOURCES.checkpoints])
        instance.addSource(source, { type: 'geojson', data: EMPTY_COLLECTION })

      const rounded = { 'line-cap': 'round', 'line-join': 'round' } as const
      instance.addLayer({
        id: MAP_LAYERS.routesOther,
        type: 'line',
        source: MAP_SOURCES.routes,
        filter: ['!=', ['get', 'selected'], true],
        layout: rounded,
        paint: { 'line-color': routeOther, 'line-width': 5, 'line-opacity': 0.75 },
      })
      instance.addLayer({
        id: MAP_LAYERS.riskCasing,
        type: 'line',
        source: MAP_SOURCES.risk,
        layout: rounded,
        paint: { 'line-color': casing, 'line-width': 10 },
      })
      instance.addLayer({
        id: MAP_LAYERS.riskLine,
        type: 'line',
        source: MAP_SOURCES.risk,
        layout: rounded,
        paint: { 'line-color': RISK_COLOR_EXPRESSION, 'line-width': 6 },
      })
      instance.addLayer({
        id: MAP_LAYERS.checkpoints,
        type: 'circle',
        source: MAP_SOURCES.checkpoints,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3.5, 8, 6],
          'circle-color': RISK_COLOR_EXPRESSION,
          'circle-stroke-color': casing,
          'circle-stroke-width': 1.5,
        },
      })

      // Click a grey route to select it
      instance.on('click', MAP_LAYERS.routesOther, (e: MapLayerMouseEvent) => {
        const id = e.features?.[0]?.properties?.id
        if (typeof id === 'string') onSelectRef.current(id)
      })
      for (const layer of [MAP_LAYERS.routesOther, MAP_LAYERS.checkpoints]) {
        instance.on('mouseenter', layer, () => (instance.getCanvas().style.cursor = 'pointer'))
        instance.on('mouseleave', layer, () => (instance.getCanvas().style.cursor = ''))
      }

      // Checkpoint details on hover (desktop) and tap (touch)
      const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 10, maxWidth: '280px' })
      const showPopup = (e: MapLayerMouseEvent) => {
        const feature = e.features?.[0]
        if (!feature || feature.geometry.type !== 'Point') return
        const checkpoint = JSON.parse(feature.properties.data as string) as Checkpoint
        popup.setLngLat(feature.geometry.coordinates as LngLat).setHTML(checkpointPopupHtml(checkpoint)).addTo(instance)
      }
      instance.on('mousemove', MAP_LAYERS.checkpoints, showPopup)
      instance.on('click', MAP_LAYERS.checkpoints, showPopup)
      instance.on('mouseleave', MAP_LAYERS.checkpoints, () => popup.remove())
      // Touch screens never fire mouseleave: a tap anywhere off a checkpoint closes the popup
      instance.on('click', (e) => {
        const onCheckpoint = instance.queryRenderedFeatures(e.point, { layers: [MAP_LAYERS.checkpoints] }).length > 0
        if (!onCheckpoint) popup.remove()
      })

      setMap(instance)
    })

    return () => {
      instance.remove()
      setMap(null)
    }
  }, [])

  return { containerRef, map, error }
}
