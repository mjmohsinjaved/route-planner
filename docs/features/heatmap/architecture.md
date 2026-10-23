# Heatmap: architecture

How the corridor heatmap is built, served and drawn. For the feature itself see [spec.md](spec.md).

## 1. Flow

```mermaid
flowchart LR
    T[TripPlan.result<br/>3 route polylines] --> G[corridor_points<br/>25 km along, 30 km each side]
    G --> W[fetch_hourly<br/>Open-Meteo, 49 h, batches in parallel]
    W --> S[score_hours<br/>risk.level_score per point per hour]
    S --> C[(Django cache<br/>heatmap:trip id:hour, 1 h)]
    C --> E[GET /api/trips/id/heatmap/]
    E --> F[useHeatmap<br/>TanStack Query, staleTime infinite]
    F --> L[HeatmapLayer<br/>one circle per point, 49 score properties]
    L --> SL[HeatmapSlider<br/>changes the paint property only]
```

## 2. Backend

The grid and scoring are pure functions in `backend/trips/domain/heatmap_grid.py`. The `BuildHeatmap` use case (`application/build_heatmap.py`) loads the trip, asks the `ForecastPort` for the weather, scores it and caches the result. The view only calls the use case; the exception handler maps errors to 429, 502 or 504.

### 2.1 Grid

- Each route's encoded polyline from the saved trip is decoded with `geo.decode_polyline`.
- `_sample_along` walks the line and emits a point every 25 km plus the end point, each with its unit direction of travel.
- For each sample, three points are added: the sample itself and one 30 km to the left and right of travel, using `geo.offset_km`.
- Every point is snapped to a 0.5° cell (`_cell`) and de-duplicated in a stable order, so overlapping routes and neighbouring samples share cells. Chicago to Denver gives about 250 points.
- The cell size is set by Open-Meteo's free tier, not by map resolution: every location in a request counts against a limit of 600 per minute, and the trip's own checkpoint weather uses about 100 of them. See section 2.5.

### 2.2 Weather

- `hour_range(now)` gives 49 hours starting at the current hour, floored.
- The forecast adapter (`infrastructure/openmeteo_forecast.py`) is called once for all points from hour 0 to hour 49. The extra hour is needed because rain and snowfall values are totals for the preceding hour (see `domain/forecast.py`): hour `h` reads wind at `h` and precipitation at `h + 1`.
- Points are fetched in batches of 50 coordinates, up to 8 batches at a time, so a 250-point grid goes out in one round. A 5xx is retried once; a 429 fails at once (section 2.5).
- Each point's hourly score reads the forecast through the same `weather.conditions_at` the checkpoints use, so the wind-at-the-hour and precipitation-from-the-next-stamp rules live in one place.
- Weather is cached per coordinate as one series for 30 minutes, so the trip's own checkpoint weather and the heatmap share entries.

### 2.3 Scoring

`score_hours` calls `risk.level_score(wind, rain, snow, load_lb)` for every point and hour (the number behind `classify`, without the reason text). The load is the trip's `load_lb`, so the load rules apply exactly as they do for checkpoints. 250 points times 49 hours is about 12,000 calls and takes a few milliseconds.

### 2.4 Caching

| What | Key | Lifetime | Why |
|---|---|---|---|
| Heatmap | `heatmap:<trip id>:<clock hour>` | 1 h | Reopening a trip is instant; a new clock hour builds a new entry, so hour 0 never labels an hour that has passed |
| Weather series | `wx:<lat>:<lon>` | 30 min | Shared by checkpoints and heatmap |

The cache is Django's local-memory backend with `MAX_ENTRIES` raised to 20,000 in settings. The default of 300 entries was culling everything after one trip.

### 2.5 Open-Meteo rate limit

Open-Meteo's free tier allows 600 location-calls per minute, 5,000 per hour and 10,000 per day. A request with 50 coordinates counts as 50. One plan with its heatmap uses about 350 of the per-minute allowance (100 for the checkpoints, 250 for the grid), so a second trip to a different corridor inside the same minute will hit a 429. Handling:

- `weather._get` raises `WeatherRateLimited` at once on a 429, with a message the UI can show. The allowance resets per minute, so a short pause and retry could only burn more calls. The view maps it to 429 with `Retry-After: 60`; other weather failures stay 502.
- Chunks that succeed are cached even when another chunk hits the limit, so a retry only pays for what is still missing. A fetched series is merged into the cached one, never replacing a wider series with a narrower one.
- `useHeatmap` retries once after 61 s, but only on a 429. While waiting the slider says "Weather limit reached, retrying in a minute…". Any other failure shows its message at once.
- Weather is cached per coordinate for 30 minutes, so repeating a trip costs nothing. The heatmap itself is cached per trip and per clock hour, so "+0 h" always names the current hour.

## 3. Frontend

| File | Role |
|---|---|
| `api/hooks/use-heatmap.ts` `useHeatmap` | Fetches once per trip id, never refetches (`staleTime: Infinity`) |
| `components/organisms/HeatmapLayer.tsx` | Adds a MapLibre `circle` layer below the routes and keeps it in sync with the hour and the switch |
| `components/molecules/HeatmapSlider.tsx` | MUI slider 0 to 48 with time labels, plus the on/off switch and the loading, retry and error line |
| `theme/risk.ts` `riskColorExpression` | Builds the color expression for any score property |
| `store/trip-store.ts` | Zustand: `heatmapHour` and `isHeatmapVisible`, shared by the slider and the layer. `PlannerPage` calls `useHeatmap` and passes the data to both |

### 3.1 Why the slider is instant

Each grid point is one GeoJSON feature with 49 properties, `h0` to `h48`, holding its hourly scores. The layer's `circle-color` is a `match` expression on one of those properties. Moving the slider calls `setPaintProperty` with the expression for the new hour. The data is parsed once when the heatmap arrives; afterwards nothing is re-sent to the map worker and nothing is fetched.

### 3.2 Drawing

- `circle` layer, radius growing with zoom so blobs merge into a band at trip zoom and stay blob-like when zoomed in.
- `circle-blur` 0.7 and `circle-opacity` 0.32 for the soft look.
- The layer is inserted before `routes-other`, so routes, risk segments and checkpoints draw on top.
- A MapLibre `heatmap` layer type was not used because it sums density, which would make calm areas with many points look stormy.

## 4. Decisions

| Decision | Reason |
|---|---|
| 0.5° cells, 25 km spacing | Keeps the grid near 250 points so one plan plus heatmap uses about 350 of Open-Meteo's 600 location-calls per minute, with headroom. 0.4° gave 330 (about 430 per minute, no headroom); 0.2° gave 487 and 0.1° gave 585, both of which hit 429 |
| Hour 0 = now, not departure | The PRD defines the slider that way; the trip's own checkpoints already cover departure time |
| Cache for 1 hour, not forever | A heatmap built yesterday would show stale weather under a "now" label |
| Per-point properties, not per-hour setData | Keeps slider moves free of GeoJSON re-parsing |
