import type { Place } from '../types'

export interface TripPreset {
  label: string
  origin: Place
  destination: Place
}

/** Example trips offered as one-click chips under the form. */
export const TRIP_PRESETS: TripPreset[] = [
  {
    label: 'Chicago → Denver',
    origin: { name: 'Chicago, IL', lat: 41.8781, lon: -87.6298 },
    destination: { name: 'Denver, CO', lat: 39.7392, lon: -104.9903 },
  },
  {
    label: 'Salt Lake City → Cheyenne',
    origin: { name: 'Salt Lake City, UT', lat: 40.7608, lon: -111.891 },
    destination: { name: 'Cheyenne, WY', lat: 41.14, lon: -104.8202 },
  },
  {
    label: 'Minneapolis → Fargo',
    origin: { name: 'Minneapolis, MN', lat: 44.9778, lon: -93.265 },
    destination: { name: 'Fargo, ND', lat: 46.8772, lon: -96.7898 },
  },
]
