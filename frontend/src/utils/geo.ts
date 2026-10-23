import type { Feature, FeatureCollection, LineString } from 'geojson'
import type { Checkpoint } from '../types'

export type LngLat = [number, number]

/** Decode a Google encoded polyline into [lng, lat] pairs (MapLibre order). */
export function decodePolyline(encoded: string, precision = 5): LngLat[] {
  const factor = 10 ** precision
  const out: LngLat[] = []
  let index = 0
  let lat = 0
  let lng = 0
  while (index < encoded.length) {
    for (const axis of [0, 1]) {
      let result = 0
      let shift = 0
      let byte: number
      do {
        byte = encoded.charCodeAt(index++) - 63
        result |= (byte & 0x1f) << shift
        shift += 5
      } while (byte >= 0x20)
      const delta = result & 1 ? ~(result >> 1) : result >> 1
      if (axis === 0) lat += delta
      else lng += delta
    }
    out.push([lng / factor, lat / factor])
  }
  return out
}

function haversineMi(a: LngLat, b: LngLat): number {
  const R = 3958.8
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(b[1] - a[1])
  const dLng = toRad(b[0] - a[0])
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

/**
 * Split a route line into one piece per checkpoint, each colored by that
 * checkpoint's level (a checkpoint owns the road since the previous one).
 * Distances are scaled to the route's official length, like the backend does.
 */
export function riskSegments(
  coords: LngLat[],
  distanceMi: number,
  checkpoints: Checkpoint[],
): FeatureCollection<LineString> {
  const along = [0]
  for (let i = 1; i < coords.length; i++) along.push(along[i - 1] + haversineMi(coords[i - 1], coords[i]))
  const scale = along[along.length - 1] ? distanceMi / along[along.length - 1] : 1
  for (let i = 0; i < along.length; i++) along[i] *= scale

  const pointAt = (mile: number): LngLat => {
    const i = along.findIndex((d) => d >= mile)
    if (i <= 0) return i === 0 ? coords[0] : coords[coords.length - 1]
    const t = (mile - along[i - 1]) / (along[i] - along[i - 1] || 1)
    return [coords[i - 1][0] + (coords[i][0] - coords[i - 1][0]) * t, coords[i - 1][1] + (coords[i][1] - coords[i - 1][1]) * t]
  }

  const features: Feature<LineString>[] = []
  for (let k = 1; k < checkpoints.length; k++) {
    const from = checkpoints[k - 1].mile
    const to = checkpoints[k].mile
    const line: LngLat[] = [pointAt(from)]
    for (let i = 0; i < coords.length; i++) if (along[i] > from && along[i] < to) line.push(coords[i])
    line.push(pointAt(to))
    features.push({
      type: 'Feature',
      properties: { level_score: checkpoints[k].level_score },
      geometry: { type: 'LineString', coordinates: line },
    })
  }
  return { type: 'FeatureCollection', features }
}

export function boundsOf(lines: LngLat[][]): [LngLat, LngLat] {
  let minLng = Infinity
  let minLat = Infinity
  let maxLng = -Infinity
  let maxLat = -Infinity
  for (const line of lines)
    for (const [lng, lat] of line) {
      minLng = Math.min(minLng, lng)
      minLat = Math.min(minLat, lat)
      maxLng = Math.max(maxLng, lng)
      maxLat = Math.max(maxLat, lat)
    }
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ]
}
