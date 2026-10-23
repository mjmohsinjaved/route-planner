# Tasks: Route Planner

Tick tasks as you finish them. Schedule is in [plan.md](plan.md); requirements in [PRD.md](PRD.md).

Status key: `[ ]` to do · `[x]` done

---

## Day 1 morning: Setup + routing

### Setup
- [x] T01 Install Python 3.12 and Node.js
- [x] T02 Create the Django project (`config`) and `trips` app
- [x] T03 Create the React + TypeScript frontend with Vite
- [x] T04 Install MUI, TanStack Query, axios, MapLibre GL
- [x] T05 Add DRF, CORS and `trips` to Django settings
- [x] T06 `GET /api/health/` endpoint
- [x] T07a Vite proxy for `/api`
- [ ] T07b "API connected" indicator on the page (not built; see Future scope)
- [x] T08 `.gitignore`, `.gitattributes`, `.env.example`
- [x] T09 Add `docs/` (PRD, architecture, plan, tasks, git rules)

### Geocoding
- [x] T10 Get a TomTom API key; load it from `.env` with django-environ
- [x] T11 `infrastructure/tomtom_geocoder.py`: TomTom Search, returns name + lat/lon
- [x] T12 `GET /api/geocode?q=` endpoint

### Routing
- [x] T13 `infrastructure/tomtom_routing.py` and `application/find_routes.py`: TomTom truck route with `vehicleWeight` and `maxAlternatives=2`
- [x] T14 Parse distance (miles), duration, geometry and time along the route
- [x] T15 Via-point fallback when fewer than 3 routes come back
- [x] T16 Timeout and one retry on outbound calls

**Check:** Chicago → Denver returns 3 routes.

---

## Day 1 afternoon: Weather + risk engine

### Checkpoints
- [x] T17 `domain/sampling.py`: checkpoint every 10 / 25 / 50 miles + origin and destination
- [x] T18 ETA per checkpoint from route time data

### Weather
- [x] T19 `infrastructure/openmeteo_forecast.py`: batched Open-Meteo call (wind, gusts, rain, snowfall; mph, inch, GMT)
- [x] T20 Map each ETA to the right forecast hour (preceding-hour rule)
- [x] T21 Round coordinates to 0.1° and de-duplicate

### Risk and recommendation
- [x] T22 `domain/risk.py`: wind, rain and snow levels (thresholds from PRD section 6)
- [x] T23 Load rules (> 30,000 lb and > 40,000 lb)
- [x] T24 Reason text per checkpoint
- [x] T25 Route metrics: No Travel, Severe, High miles; average risk
- [x] T26 `domain/ranking.py`: ranking + reason sentence + unsafe flag
- [x] T27 `TripPlan` model and migration
- [x] T28 Serializer with input validation
- [x] T29 `POST /api/trips/` endpoint

### Tests
- [x] T30 Threshold edge tests (wind, rain, snow)
- [x] T31 Load rule tests, including exactly 30,000 and 40,000 lb
- [x] T32 Sampling and ETA tests
- [x] T33 Forecast-hour mapping test
- [x] T34 Recommender ordering and unsafe-flag tests

**Check:** tests pass and the API names the best route.

---

## Day 1 evening: Map screen

- [x] T35 Shared types (`types.ts`) and API hooks
- [x] T36 Risk color scale (`theme/risk.ts`)
- [x] T37 `TripForm`: autocomplete, date/time, load, interval, presets
- [x] T38 `RouteCard` + `RouteList` with "Recommended" badge and reason
- [x] T39 `MapView`: 3 routes, selected route colored by risk
- [x] T40 Checkpoint markers with tooltips (ETA, weather, level, reason)
- [x] T41 `Legend`
- [x] T42 Loading, error and empty states

**Check:** a sample trip shows everything on one screen.

---

## Day 2 morning: Heatmap + speed

- [x] T43 `domain/heatmap_grid.py` and `application/build_heatmap.py`: corridor grid + 49-hour risk scores
- [x] T44 `GET /api/trips/{id}/heatmap/` endpoint
- [x] T45 `HeatmapLayer` fed from in-memory hour data
- [x] T46 `HeatmapSlider` with absolute time labels
- [x] T47 Heatmap on/off toggle
- [x] T48 Cache geocode, routes and weather
- [x] T49 Quick UI pass: spacing, alignment, number formats

**Check:** the slider moves smoothly with no loading.

---

## Day 2 afternoon: Ship

- [x] T50 Production settings (env vars, `ALLOWED_HOSTS`, CORS, static files)
- [x] T51 Deploy backend (Django as a Python function on Vercel, Postgres via `DATABASE_URL`)
- [x] T52 Deploy frontend (same Vercel project; calls `/api` on the same origin, so no API URL is needed)
- [ ] T53 Test the live app from an incognito window
- [x] T54 README: links, screenshot, setup, assumptions, tests
- [ ] T55 Record the Loom (5–10 min)
- [ ] T56 Run the submission checklist in plan.md
- [ ] T57 Tag `v1.0` and submit the links

**Check:** repo, app and Loom links are sent.

---

## Done beyond the plan

- [x] X1 Per-IP throttling on every public endpoint (10 plans a minute, 150 a day)
- [x] X2 `detail` message on every error response (DRF exception handler)
- [x] X3 Open-Meteo rate-limit handling: clear 429, partial batches cached, one automatic retry in the UI
- [x] X4 Missing forecast value is a 502, never calm weather
- [x] X5 Postgres for production, because Vercel's file system is read-only
- [x] X6 Tablet layout (768 px), empty state, map error banner, past-date check
- [x] X7 MapLibre lazy-loaded in its own chunk; vendor chunks split
- [x] X8 Step timings logged for each plan

## Optional, not built (future scope)

Full list with context in [PRD section 15](PRD.md#15-future-scope).

- [ ] O1 Heatmap play button
- [ ] O2 Truck marker moving along the recommended route with the slider
- [ ] O3 Heatmap metric switch (risk / wind / rain / snow)
- [ ] O4 Risk-along-route chart
- [ ] O5 Shareable trip link in the UI (the API already serves `GET /api/trips/{id}/`)
- [ ] O6 Shared cache (Redis or database cache)
- [ ] O7 One weather fetch shared by checkpoints and heatmap
- [ ] O8 Faster first plan (`traffic=false` or streaming alternatives)
- [ ] O9 Frontend tests and CI
- [ ] O10 Register `TripPlan` in the Django admin
