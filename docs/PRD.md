# Product Requirements Document: Route Planner

**Project:** Weather-Aware Truck Routing (`route-planner`)
**Stack:** React + MUI (frontend), Django + DRF (backend), one Vercel project
**Status:** Built and deployed; walkthrough video and screenshot pending (see [task.md](task.md))
**Last updated:** 2026-10-23, reconciled with the code

This document started as the requirements and now also records what was built. Where the build differs from the original plan, the text says so. Work that was planned or considered but not built is collected in section 15, Future scope.

---

## 1. Overview

### 1.1 Problem
Truck drivers choose routes mostly on distance and time. Weather along the way (high wind, heavy rain, snow) is a major safety risk, and heavier loads are more exposed to wind. Drivers have no simple way to compare routes by the weather they will actually meet at the time they will be at each point.

### 1.2 Goal
A web app that takes a trip (origin, destination, departure time, load weight), generates 3 route options, checks the forecast at checkpoints along each route for the truck's estimated arrival time, scores the risk, and recommends the safest route while balancing travel time.

### 1.3 Success criteria and where they landed

| Criterion | Result |
|---|---|
| Every trip returns exactly 3 route options | Met whenever TomTom can route the trip. If it cannot find three distinct routes even with via-points, fewer are returned; if it finds none the API answers 422 |
| Every checkpoint shows its ETA, weather values, risk level and the rule that set it | Met (map popup) |
| The recommendation follows the ranking rules exactly and explains why in one sentence | Met; the sentence names the first comparison that decided it |
| The heatmap slider (0–48 h) changes hours instantly, with no network call | Met; all 49 hours load once per trip |
| First trip result in about 3 s or less; a repeated trip in under 1 s | **Repeat met** (about 0.06 s from cache). **First trip not met:** 6 to 9 s for a 1,000 mile trip. About 6 s of that is TomTom computing alternatives for a long truck route (one route takes about 2.5 s). Shorter trips are faster. See Future scope for options |

---

## 2. Users and core use case

**Primary user:** a truck driver or dispatcher planning a single trip.

**Core flow:**
1. Enter origin, destination, departure date/time and load weight (or tap one of three example trips).
2. Choose a checkpoint interval (10, 25 or 50 miles).
3. See 3 routes on a map, with colored checkpoints and a summary card for each route.
4. See which route is recommended and why.
5. Use the heatmap slider to see how weather along the corridor changes over the next 48 hours.

---

## 3. Scope

### 3.1 In scope (all built)
- Geocoding with autocomplete for origin and destination
- 3 route options from a third-party routing API (truck profile)
- Checkpoint sampling every 10 / 25 / 50 miles
- ETA at each checkpoint
- Hourly weather at each checkpoint for its ETA
- Risk classification using the provided wind, rain, snow and load rules
- Route ranking and recommendation with a reason
- Map showing routes, checkpoints, risk levels, ETAs and summaries
- Weather heatmap along the trip corridor with a 0–48 hour slider
- Hosted app and README

Added during the build, beyond the original scope: per-IP rate limiting, an error body with `detail` on every failure, saved trips reopenable by id through the API, tablet layout, empty and map-error states, and a lazy-loaded map bundle.

### 3.2 Out of scope
- Building a routing engine
- User accounts and authentication
- Turn-by-turn navigation
- Live traffic re-routing during the trip
- Native mobile apps
- Truck restrictions beyond weight (height, hazmat), unless the routing API applies them by default

---

## 4. User inputs

| Field | Type | Rules |
|---|---|---|
| Origin | Place (text → coordinates) | Required; must geocode to a point |
| Destination | Place (text → coordinates) | Required; at least 1 km from the origin |
| Departure | Date and time (local) | Required; from 15 minutes ago (counts as "now") up to 14 days ahead |
| Load weight | Whole number, lb | Required; 1 to 100,000 |
| Checkpoint interval | 10 / 25 / 50 miles | Default 25 |

The form validates the same rules before sending, and the API validates them again. The form's departure picker does not offer dates earlier than the grace window.

---

## 5. Functional requirements

### FR-1 Geocoding
- `GET /api/geocode/?q=` returns up to 5 suggestions with name and coordinates. Queries shorter than 2 characters return an empty list.
- Search is TomTom Search with `typeahead` and restricted to the United States and Canada (`countrySet=US,CA`), which matches the truck-routing use case.
- Debounced on the frontend (300 ms) and cached there for 24 h; cached on the backend for 24 h by lower-cased query text.

### FR-2 Route generation
- Call the routing API in truck mode, passing departure time and vehicle weight in kg.
- **Vehicle weight = load + 35,000 lb tractor-trailer tare.** The user enters the cargo; road restrictions apply to the whole truck. The risk rules use the load alone, as the brief specifies.
- Request 2 alternatives, for 3 routes in total.
- **Fallback:** if fewer than 3 distinct routes come back, route through a via-point placed to the side of the first route's midpoint. The offset is 10% of the route length, clamped to 30–80 km. Round one tries one via-point on each side in parallel; if still short, round two repeats at 1.8 times the offset. A via-point that cannot be routed is skipped.
- Near-duplicates are dropped: two routes within 1% on both distance and time count as the same.
- Keep for each route: geometry, total distance (miles), total duration, and cumulative distance and time along the geometry (TomTom's coded instruction points).
- If TomTom finds no route at all, the API answers 422 "No truck route found between these places."

### FR-3 Checkpoint sampling
- Walk each route's geometry using haversine distance, scaled to TomTom's official route length so mile markers match the distance on the card.
- Place a checkpoint every N miles (the chosen interval), plus the origin and the destination. A mark that falls on the destination is skipped.
- Each checkpoint covers the route segment from the previous checkpoint to itself (`segment_mi`).

### FR-4 ETA per checkpoint
- ETA = departure time + travel time to that checkpoint.
- Travel time is interpolated from the route's own cumulative time data, not from an average speed.
- All times are stored and computed in UTC and shown in the user's local time.

### FR-5 Weather lookup
- Source: Open-Meteo hourly forecast.
- Variables: `wind_speed_10m`, `wind_gusts_10m`, `rain`, `snowfall`.
- Units: `wind_speed_unit=mph`, `precipitation_unit=inch`, `timezone=GMT`.
- Batch all checkpoints of all three routes: coordinates in groups of 50 per request, up to 8 requests at once.
- **Rain and snowfall** are totals for the **preceding** hour. An ETA inside an hour uses the value at the end of that hour (ETA 14:20 → the 15:00 value).
- **Wind** is an instant value, so it uses the **nearest** hour (14:29 → 14:00, 14:30 → 15:00).
- Coordinates are rounded to 0.1° for caching and de-duplication.
- **A missing wind, rain or snow value is an error, not calm weather.** The plan fails with a 502 and a message. Gusts are informational and may be absent.
- Timeout (15 s) and one retry on network errors and 5xx. A 429 from Open-Meteo is not retried because its allowance resets per minute; it is returned as a 429 with `Retry-After: 60`.

### FR-6 Risk classification
See section 6. Each checkpoint gets one level: Low, Moderate, High, Severe or No Travel. The level is the worst of wind, rain and snow, after load rules are applied. Classification uses the raw forecast value; rounding happens only for display. Each checkpoint also returns the reason, for example `Wind 47.0 mph + 38,000 lb load → No Travel`.

### FR-7 Route metrics
For each route:
- No Travel miles, Severe miles, High miles (sum of segment lengths at that level, one decimal)
- Average risk: distance-weighted mean of level scores (Low 0, Moderate 1, High 2, Severe 3, No Travel 4)
- Total distance, total duration, arrival time

### FR-8 Recommendation
See section 7. Returns the recommended route, the full ranking, a plain-English reason and the unsafe flag.

### FR-9 Map and summaries
- All 3 routes drawn; the selected route (the recommended one by default) is colored segment by segment by risk. Clicking a grey route or a card selects it.
- Checkpoint markers colored by risk, with a popup (hover on desktop, tap on touch) showing mile, ETA, wind, gusts, rain, snow, level and reason.
- One summary card per route with distance, drive time, arrival time, No Travel / Severe / High miles, average risk, a stacked bar of miles per level, and a "Recommended" badge on the winner. Cards are listed in ranking order; the reason sentence sits on the winner.
- A legend using the same colors as markers, segments, cards and the heatmap.
- Loading skeletons while a plan runs, an empty state before the first trip, a banner when the map cannot start (no WebGL) or its style fails to load, and an error alert with the API's `detail` when a plan fails.
- The base map is OpenFreeMap "positron" vector tiles (no key); `VITE_MAP_STYLE` overrides it.

### FR-10 Weather heatmap
- Corridor grid: a point every 25 km along all 3 routes plus one point 30 km to each side, snapped to 0.5° cells and de-duplicated. About 250 points for a 1,000 mile trip. The cell size is set by Open-Meteo's free tier (600 location-calls a minute), not by map resolution.
- One batched weather fetch for 49 hours (hour 0 to hour 48), plus one extra stamp for the last rain and snow value.
- Backend returns a load-aware risk score per point per hour, using the same hour rules and risk rules as checkpoints.
- Frontend loads it once per trip and keeps all hours in memory. The slider only changes which property colors the layer, with no network call.
- Slider labels show absolute time, for example "Wed 14:00 · +6 h". Hour 0 = the current clock hour, not the departure.
- A switch turns the heatmap off. If Open-Meteo's limit is hit, the slider says so and the page retries once after a minute.
- Detail in [features/heatmap/](features/heatmap/spec.md).

---

## 6. Risk rules

### 6.1 Weather thresholds

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 to < 35 | 35 to < 45 | 45 to < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 to < 0.25 | 0.25 to < 0.50 | 0.50 to 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 to < 1.0 | 1.0 to < 2.0 | 2.0 to 3.0 | > 3.0 |

**Boundary decision:** the brief's ranges share edge values (for example 0.25 appears in both Moderate and High). This app uses the ranges above: each edge value belongs to the higher level, except the Severe/No Travel edge for rain and snow, where "> 1.00" and "> 3.0" are exclusive as written.

**Wind source:** sustained wind (`wind_speed_10m`) is used for classification. Gusts are shown in the popup for context.

### 6.2 Load rules
Applied after the weather level; the checkpoint takes the more severe of the two.

| Wind (mph) | Load | Result |
|---|---|---|
| ≥ 55 | Any | No Travel |
| 45–54 | > 30,000 lb | No Travel |
| 35–44 | > 40,000 lb | Severe |

Loads of exactly 30,000 lb or 40,000 lb do **not** trigger the rule ("greater than").

---

## 7. Recommendation logic

Routes are sorted by these keys, in order; the first route wins:

1. Fewest No Travel miles *(added: No Travel is worse than Severe, so it ranks first)*
2. Fewest Severe miles
3. Fewest High miles
4. Lowest average risk
5. Shortest travel time

The reason sentence names the first key on which the winner and the runner-up differ, with miles to one decimal, and says how much longer the winner is than the fastest route (or that it is also the fastest). For example: "Route B recommended: no Severe miles vs 42.0 on Route A, 18 min longer than the fastest (Route A)."

If **every** route has No Travel miles, the app still shows the best-ranked route but flags the trip as **unsafe to travel at this departure time**, in the reason and in an alert above the cards.

---

## 8. API specification

All paths end with a slash. Times are ISO 8601 UTC with a `Z` suffix.

### `GET /api/health/`
Returns `{"status": "ok"}`.

### `GET /api/geocode/?q=<text>`
```json
[
  { "name": "Chicago, IL, USA", "lat": 41.8781, "lon": -87.6298 }
]
```

### `POST /api/trips/`
Request:
```json
{
  "origin": { "name": "Chicago, IL", "lat": 41.8781, "lon": -87.6298 },
  "destination": { "name": "Denver, CO", "lat": 39.7392, "lon": -104.9903 },
  "departure": "2026-10-21T08:00:00Z",
  "load_lb": 38000,
  "interval_mi": 25
}
```
Response `201` (shortened):
```json
{
  "id": "0b6f3a52-6c3d-4f5e-9c1e-5d7a3f1b2a10",
  "origin": { "name": "Chicago, IL", "lat": 41.8781, "lon": -87.6298 },
  "destination": { "name": "Denver, CO", "lat": 39.7392, "lon": -104.9903 },
  "departure": "2026-10-21T08:00:00Z",
  "load_lb": 38000,
  "interval_mi": 25,
  "recommended_route_id": "B",
  "ranking": ["B", "A", "C"],
  "recommendation_reason": "Route B recommended: no Severe miles vs 42.0 on Route A, 18 min longer than the fastest (Route A).",
  "unsafe": false,
  "routes": [
    {
      "id": "A",
      "distance_mi": 1003.4,
      "duration_min": 905,
      "arrival": "2026-10-21T23:05:00Z",
      "no_travel_mi": 0,
      "severe_mi": 42.0,
      "high_mi": 75.0,
      "avg_risk": 0.84,
      "geometry": "<encoded polyline, at most 1,500 points>",
      "checkpoints": [
        {
          "index": 1,
          "mile": 25,
          "segment_mi": 25,
          "lat": 41.62,
          "lon": -88.10,
          "eta": "2026-10-21T08:28:00Z",
          "wind_mph": 18.2,
          "gust_mph": 27.0,
          "rain_in_hr": 0.02,
          "snow_in_hr": 0.0,
          "level": "Low",
          "level_score": 0,
          "reason": "All conditions Low"
        }
      ]
    }
  ]
}
```
`gust_mph` is `null` when the forecast has no gust value. Weather values are the raw forecast values, not rounded.

### `GET /api/trips/{id}/`
Returns a saved trip in the same shape as above. `{id}` is a UUID. The UI does not use this endpoint yet (see Future scope).

### `GET /api/trips/{id}/heatmap/`
```json
{
  "points": [[41.62, -88.10], [41.70, -88.40]],
  "hours": ["2026-10-20T11:00:00Z", "2026-10-20T12:00:00Z"],
  "values": [[0, 1], [0, 2]]
}
```
`values[hour][point]` = risk score 0–4. `hours` has 49 entries; `hours[0]` is the clock hour the heatmap was built.

### Errors
Every error body has a `detail` sentence the UI shows as is. Validation errors also keep their field messages.

| Status | When |
|---|---|
| `400` | Invalid input (field messages plus `detail`) |
| `404` | Unknown trip id |
| `422` | TomTom finds no truck route between the places |
| `429` | Per-IP throttle, or Open-Meteo's per-minute limit. Always with `Retry-After` |
| `502` | A third-party API failed, or a forecast value is missing. No partial recommendation |
| `504` | A third-party API timed out |

---

## 9. Non-functional requirements

| Area | Requirement | Status |
|---|---|---|
| Performance | First trip about 3 s; cached repeat under 1 s; heatmap slider with no visible delay | Repeat and slider met; first trip is 6–9 s for 1,000 miles (see 1.3) |
| Caching | Geocode 24 h; routes 1 h (key: origin, destination, departure hour, load); weather per coordinate series 30 min; heatmap per trip and clock hour 1 h | Met. Caches are in memory, per function instance on Vercel |
| Reliability | Timeout on every outbound call and one retry on routing and weather; clear error messages | Met. Geocoding has a timeout and no retry; the user can type again |
| Rate limits | One client must not exhaust the TomTom and Open-Meteo allowances | Per-IP: plans 10/min and 150/day; geocode, trip and heatmap reads 60/min and 2,000/day |
| Security | API keys only in environment variables; never in the repo or frontend bundle | Met. Keys are never logged; the geocode query is URL-encoded as one path segment |
| Usability | Works at laptop (1280 px) and tablet (768 px) widths; loading skeletons; empty and error states | Met. Below 768 px the map stacks above the sidebar |
| Code quality | Thin views; logic outside the framework; tests for every risk rule | Met. Domain, application, infrastructure and interface layers with imports pointing inward (enforced by a test); 139 backend tests, no network or key needed |

---

## 10. Tech stack and services

| Layer | Choice |
|---|---|
| Frontend | React 19, Vite, TypeScript, MUI, TanStack Query, Axios, Zustand, React Select, MapLibre GL |
| Backend | Python 3.12, Django 6, Django REST Framework, httpx, WhiteNoise |
| Database | Postgres in production (`DATABASE_URL`), SQLite locally |
| Cache | Django cache framework, local memory (Redis is a settings change) |
| Routing + geocoding | TomTom Routing API (truck mode) and Search API (free tier) |
| Weather | Open-Meteo forecast API (free, no key) |
| Base map | OpenFreeMap vector tiles (no key) |
| Hosting | One Vercel project: static frontend plus Django as a Python serverless function (60 s limit) |

The original plan was SQLite and a separate backend host. Vercel's function file system is read-only, so production uses Postgres, and one project serves both halves from one origin (no CORS setup).

---

## 11. Code structure

```
route-planner/
├── api/index.py                # Vercel entrypoint: Django WSGI
├── vercel.json                 # builds and routes
├── backend/
│   ├── config/                 # settings, root urls, wsgi
│   ├── trips/
│   │   ├── domain/             # plain Python rules: risk, sampling, forecast hours, ranking, heatmap grid
│   │   ├── application/        # use cases (PlanTrip, BuildHeatmap, ...) and the ports they need
│   │   ├── infrastructure/     # adapters: TomTom, Open-Meteo, Django cache, database
│   │   ├── interfaces/         # DRF views, serializers, throttling, error handler, urls
│   │   ├── container.py        # wires adapters to ports
│   │   ├── models.py           # TripPlan
│   │   └── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/                # client and hooks
│       ├── components/         # atoms, molecules, organisms, templates, pages
│       ├── hooks/ store/ theme/ utils/ constants/
│       └── types.ts
└── docs/                       # this file, architecture, plan, tasks, git rules, features/heatmap
```

Full layout and layer rules: [architecture.md](architecture.md#4-backend).

---

## 12. Edge cases

| Case | Behavior |
|---|---|
| Origin = destination (within 1 km) | 400: "Destination must be different from the origin." |
| Departure in the past | 400: "Departure can't be in the past." Up to 15 minutes ago is accepted and treated as now |
| Departure beyond the forecast range | 400: "Forecast is available up to 14 days ahead." |
| Load missing, 0 or above 100,000 lb | 400 with a field message |
| Place not found | Autocomplete shows "No matches" |
| Routing API returns fewer than 3 routes | Via-point fallback (FR-2) |
| Routing API finds no route | 422 with a message |
| A checkpoint ETA falls past 48 h | Still uses the hourly forecast (available up to ~16 days) |
| Weather API fails | 502 with a retry suggestion; no partial recommendation |
| Weather has no value for a checkpoint hour | 502 "Forecast is not available for part of this trip. Try another departure time." |
| Open-Meteo per-minute limit | 429 with `Retry-After: 60`; the heatmap retries once after a minute |
| Very short trip (< interval) | Checkpoints at origin and destination only |
| All routes have No Travel miles | Show the ranking, flag the trip as unsafe |
| Map cannot start (no WebGL) or style fails | Banner over the map; route cards still work |

---

## 13. Testing

139 backend tests (Django test runner), organised by layer. Use cases run against in-memory fakes of the ports; only the adapter tests stub HTTP:
- Every threshold edge for wind, rain and snow (for example 24.9, 25, 34.9, 35, 54.9, 55)
- Each load rule, including exactly 30,000 lb and 40,000 lb
- Checkpoint spacing and inclusion of origin and destination
- ETA interpolation
- ETA → forecast-hour mapping (preceding-hour rule, nearest-hour wind) and missing-value handling
- Recommendation order at each tie-break level
- Unsafe-trip flag
- Routing fallback, duplicate dropping and the route cache
- Open-Meteo 429 and 5xx handling, and partial caching when one batch fails (adapter tests)
- Heatmap grid, scoring and endpoint
- Trip, heatmap and geocode endpoints end to end: validation errors, 404, 422, 429, 502, 504, per-IP throttling and the `detail` on every error
- Adapters: retry rules, no URL or key in error messages, response parsing, the trip repository round trip
- The dependency rule between layers

Not covered by automated tests: the frontend (checked by type check, lint and manual runs).

Manual checks:
- Chicago → Denver returns 3 routes with colored checkpoints
- Raising load from 25,000 lb to 45,000 lb on a windy route changes risk as expected
- Heatmap slider is smooth across all 49 hours, with no requests in the network tab

---

## 14. Milestones

The original two-day plan is in [plan.md](plan.md) and the task list with status in [task.md](task.md). All build blocks are done. Open delivery items: test the live app from an incognito window, record the walkthrough, add the screenshot, run the submission checklist, tag `v1.0`.

---

## 15. Future scope

Not built. Listed roughly by value.

**Product**
- **Faster first plan.** Request alternatives with `traffic=false` (about 1 s saved, at the cost of traffic-aware ETAs), or show the direct route as soon as it arrives and stream the alternatives in.
- **Shareable trip links.** The API already saves trips by id and serves them; the UI needs a `/trips/{id}` route.
- **Heatmap extras.** Play button; a truck marker moving along the recommended route with the slider; a metric switch between risk, wind, rain and snow.
- **Risk-along-route chart.** A strip or chart of risk against mile for the selected route.
- **Mandatory rest breaks and hours-of-service in ETAs.** Today ETAs are pure driving time.
- **Time trade-off in the recommendation.** For example, accept slightly more High miles to save several hours. Today the strict order in section 7 applies.
- **Heatmap hour 0 = departure** as an option, for trips planned days ahead.
- **Truck restrictions beyond weight** (height, hazmat), passed to the routing API.
- **Geocoding outside the US and Canada**, and a metric-units toggle.
- **An "API connected" indicator** in the UI (the Vite proxy already exists).
- **Trip history** (list of saved trips), which would need accounts or a device id.

**Platform**
- **A shared cache.** Redis or the database cache, so repeat trips, weather and throttle counters survive across function instances.
- **One weather fetch for checkpoints and heatmap.** Today they sample the corridor on two grids and two time windows and rarely share cache entries. One canonical fetch window per coordinate, with the heatmap grid seeded from the checkpoint cells, would cut Open-Meteo usage per trip by roughly half and allow a finer heatmap.
- **A paid or self-hosted weather plan**, which would remove the 600-calls-a-minute ceiling that sizes the heatmap grid.
- **Automated migrations on deploy.** They are run by hand from a developer machine today.
- **Frontend tests and CI** (type check, lint and tests on every push). There is no `.github` workflow yet.
- **Register `TripPlan` in the Django admin.** `/admin/` is routed but the model is not registered.
- **Error and timing monitoring.** Step timings are logged to the console only.

---

## 16. Deliverables and assumptions

**Deliverables**
- GitHub repository (`route-planner`)
- Hosted application: https://route-planner-five-gules.vercel.app/
- README covering setup, assumptions and the decisions in this document
- 5–10 minute Loom walkthrough and README screenshot: **pending**

**Assumptions**
- Sustained wind is used for risk; gusts are informational.
- Raw forecast values are classified; rounding is display only.
- Heatmap hour 0 = the current clock hour, not the departure time.
- No Travel miles rank above Severe miles in the recommendation.
- Imperial units throughout (miles, mph, in/hr, lb).
- Driver breaks and hours-of-service rules are not modelled in ETAs.
- Locations are in the United States or Canada (geocoding is restricted to them).
- The truck's own weight is 35,000 lb for routing restrictions.
- Public endpoints are rate-limited per IP so one client cannot burn the third-party allowances.
