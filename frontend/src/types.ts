// Shapes returned by the Django API (see docs/PRD.md section 8).

export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel'

export interface Place {
  name: string
  lat: number
  lon: number
}

export interface Checkpoint {
  index: number
  mile: number
  segment_mi: number
  lat: number
  lon: number
  eta: string // ISO, UTC
  wind_mph: number
  gust_mph: number | null // null when the forecast has no gust value for that hour
  rain_in_hr: number
  snow_in_hr: number
  level: RiskLevel
  level_score: number // 0 = Low ... 4 = No Travel
  reason: string
}

export interface RouteResult {
  id: string // "A" | "B" | "C"
  distance_mi: number
  duration_min: number
  arrival: string
  no_travel_mi: number
  severe_mi: number
  high_mi: number
  avg_risk: number
  geometry: string // Google encoded polyline
  checkpoints: Checkpoint[]
}

export interface TripResult {
  id: string
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: number
  recommended_route_id: string
  ranking: string[]
  recommendation_reason: string
  unsafe: boolean
  routes: RouteResult[]
}

export interface TripRequest {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: 10 | 25 | 50
}

/** Corridor weather risk for the next 48 hours; loaded once per trip. */
export interface Heatmap {
  points: [number, number][] // [lat, lon]
  hours: string[] // ISO, UTC; index 0 = the current hour
  values: number[][] // values[hour][point] = risk score 0-4
}
