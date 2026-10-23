# Heatmap: runbook

How to run, check, tune and debug the heatmap.

## 1. Run it

```
cd backend
venv\Scripts\activate
python manage.py runserver
```

```
cd frontend
npm run dev
```

Plan a trip in the UI. The heatmap loads right after the routes appear; the slider sits at the bottom of the map.

Direct call, with a trip id from a planned trip:

```
curl http://127.0.0.1:8000/api/trips/<id>/heatmap/
```

## 2. Check it

| Check | Expect |
|---|---|
| `python manage.py test trips` | all tests pass (`test_heatmap_grid`, `test_build_heatmap`, `test_heatmap_api` and `test_openmeteo_forecast` cover this area) |
| Heatmap response for Chicago to Denver | 49 `hours`, 49 rows in `values`, about 250 `points`, about 30 KB |
| Second request for the same trip | milliseconds, no Open-Meteo call |
| Browser network tab while dragging the slider | no requests |
| Server console on a plan | one `plan_trip` line with per-step timings |

Server log lines to look for:

```
INFO trips.application.find_routes: routing: direct (3 routes, 3 distinct) 5.85s, total 5.85s
INFO trips.application.plan_trip: plan_trip Chicago, IL -> Denver, CO: routes 5.85s, checkpoints 0.04s, weather 0.95s, risk+rank 0.01s, total 6.86s
```

## 3. Tuning knobs

Grid constants are in `backend/trips/domain/heatmap_grid.py` unless noted; `CACHE_SECONDS` is in `application/build_heatmap.py`.

| Constant | Default | Effect |
|---|---|---|
| `ALONG_STEP_KM` | 25 | Spacing of points along each route |
| `SIDE_OFFSET_KM` | 30 | Distance of the side points from the route |
| `CELL_DEG` | 0.5 | Grid snap. Larger means fewer points and fewer Open-Meteo location-calls. Keep it a multiple of 0.1 |
| `HOURS` | 49 | Hours returned; the frontend slider max is `HOURS - 1` |
| `CACHE_SECONDS` | 3600 | How long a trip's heatmap is reused |
| `openmeteo_forecast.CHUNK_SIZE` | 50 | Coordinates per Open-Meteo request |
| `openmeteo_forecast.MAX_PARALLEL` | 8 | Requests in flight at once; enough for a 250-point grid in one round. Concurrency does not affect the per-minute allowance |
| `openmeteo_forecast.CACHE_SECONDS` | 1800 | Weather series lifetime |
| `settings.CACHES` `MAX_ENTRIES` | 600 × 30 + 2000 | Local-memory cache size, derived from the per-minute allowance times the 30 min series lifetime |

Frontend, in `components/organisms/HeatmapLayer.tsx`: `circle-radius` stops, `circle-opacity` 0.32, `circle-blur` 0.7.

## 4. Failure modes

| Symptom | Likely cause | What to do |
|---|---|---|
| 429 with "Weather service limit reached. Try again in a minute." and the slider says "retrying in a minute" | Open-Meteo's 600 location-calls per minute are used up: one plan plus heatmap costs about 350, so a second corridor in the same minute, or many test runs, trips it | Wait a minute; the frontend retries once by itself, and the batches that got through are already cached. If it happens with normal use, raise `CELL_DEG` or `ALONG_STEP_KM` to shrink the grid |
| 502 with "Weather service is unavailable" | Open-Meteo 5xx twice in a row | Retry. If it repeats, lower `MAX_PARALLEL` |
| 502 with "Forecast is not available for part of this trip. Try another departure time." | Open-Meteo returned no value (or fewer hours than asked) for a grid point | Retry; check the server clock, since hour 0 must be inside Open-Meteo's window |
| 504 | Open-Meteo took over 15 s per request | Retry; check network |
| 404 | Unknown trip id, or the local SQLite database was reset | Plan the trip again |
| Heatmap loads but repeat plan is slow again | Cache evictions | Confirm `MAX_ENTRIES` is set in settings; local-memory cache is per process and empties on restart |
| Slider shows "Heatmap unavailable" | The heatmap request failed | Check the server console for the error; the trip itself still works |
| Blobs hide the routes | Opacity too high for the base map | Lower `circle-opacity`, or use the switch |

## 5. Clear the caches

The local-memory cache empties when the server restarts. Without a restart:

```
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## 6. Reproduce the live timing check

A throwaway script used during development lives outside the repo. The equivalent in a Django shell:

```python
import json, time
from datetime import timedelta
from django.test import Client
from django.utils import timezone

c = Client(HTTP_HOST="localhost")
body = {"origin": {"name": "Chicago, IL", "lat": 41.8781, "lon": -87.6298},
        "destination": {"name": "Denver, CO", "lat": 39.7392, "lon": -104.9903},
        "departure": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_lb": 38000, "interval_mi": 25}
t = time.perf_counter(); r = c.post("/api/trips/", json.dumps(body), content_type="application/json")
print("plan", r.status_code, round(time.perf_counter() - t, 2))
t = time.perf_counter(); h = c.get(f"/api/trips/{r.json()['id']}/heatmap/")
print("heatmap", h.status_code, round(time.perf_counter() - t, 2), len(h.json()["points"]), "points")
```
