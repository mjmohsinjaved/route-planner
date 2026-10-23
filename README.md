# Route Planner: weather-aware truck routing

**Live app:** https://route-planner-five-gules.vercel.app/
**Walkthrough (Loom):** _link to be added_

## Overview

Enter an origin, a destination, a departure time and the load weight. The app gets three truck routes from TomTom and places a checkpoint every 10, 25 or 50 miles. For each checkpoint it works out when the truck will arrive, looks up the Open-Meteo forecast for that hour, and scores the checkpoint with the wind, rain, snow and load rules from the brief. It then recommends the safest route while keeping travel time in view. A heatmap with a 0 to 48 hour slider shows how risk along the whole corridor changes over the next two days.

![Screenshot: three routes on the map with risk-colored checkpoints, route cards and the heatmap slider](docs/screenshot.png)
_Screenshot to be added at `docs/screenshot.png`._

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite, MUI, TanStack Query, Axios, Zustand, React Select, MapLibre GL |
| Backend | Python 3.12, Django 6, Django REST Framework, httpx |
| Routing and geocoding | TomTom Routing and Search APIs (truck mode) |
| Weather | Open-Meteo forecast API (free, no key) |
| Database | Postgres in production, SQLite locally |
| Hosting | One Vercel project: static frontend plus Django as a Python serverless function |

The backend is layered (`domain`, `application`, `infrastructure`, `interfaces`); see [docs/architecture.md](docs/architecture.md).

## How it works

**Routes.** The backend makes one TomTom request in truck mode, with the vehicle weight and departure time, and asks for two alternatives. If fewer than three distinct routes come back, it adds a via-point 30 to 80 km to the side of the route midpoint and routes again, two via-points at a time in parallel. Near-duplicates (within 1% on both distance and time) are dropped.

**Checkpoints.** Each route's geometry is walked with haversine distance, scaled to TomTom's official route length. A checkpoint is placed at the origin, every N miles, and at the destination. Each checkpoint covers the stretch of road since the previous one, and the route metrics add up those stretches.

**ETA.** The arrival time at each checkpoint is the departure time plus the travel time to that point. The travel time is interpolated from TomTom's cumulative time data along the route (its instruction points), not worked out from an average speed. All times are computed in UTC and shown in the viewer's local time.

**Weather hour rule.** Open-Meteo's rain and snowfall values are totals for the preceding hour, so a checkpoint reached at 14:20 reads the value stamped 15:00. Wind is an instant value, so it uses the nearest hour. One batched request covers every checkpoint on all three routes.

**Risk rules.** Each checkpoint gets the worst of its wind, rain and snow levels:

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 to < 35 | 35 to < 45 | 45 to < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 to < 0.25 | 0.25 to < 0.50 | 0.50 to 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 to < 1.0 | 1.0 to < 2.0 | 2.0 to 3.0 | > 3.0 |

**Load rules**, applied on top of the weather levels:

| Wind | Load | Result |
|---|---|---|
| ≥ 55 mph | any | No Travel |
| 45 to 54 mph | > 30,000 lb | No Travel |
| 35 to 44 mph | > 40,000 lb | Severe |

Every checkpoint carries a reason, such as `Wind 47.0 mph + 38,000 lb load → No Travel`.

**Ranking.** Routes are sorted by:

1. Fewest No Travel miles
2. Fewest Severe miles
3. Fewest High miles
4. Lowest distance-weighted average risk
5. Shortest travel time

The first route wins, and the reason sentence names the comparison that decided it. If every route crosses No Travel weather, the best route is still shown and the trip is flagged unsafe for that departure time.

**Heatmap.** The backend builds a grid of points every 25 km along all three routes, plus points 30 km to each side, snapped to 0.5° cells. Each point is scored for each of the next 49 hours with the same rules and the trip's load. The browser loads the grid once. The slider only changes which hour colors the layer, so dragging it never calls the API.

## Assumptions and trade-offs

- **Boundary values.** The brief's ranges share edge values: 0.25 in/hr, for example, appears in both Moderate and High. Each edge value belongs to the higher level. The exception is the Severe to No Travel edge for rain and snow: the brief writes it as "> 1.00" and "> 3.0", so it stays exclusive. Loads of exactly 30,000 or 40,000 lb do not trigger the load rules, because the brief says "greater than".
- **Sustained wind, not gusts.** Risk is classified on Open-Meteo's sustained 10 m wind. Gusts are fetched and shown in the checkpoint tooltip for context only.
- **35,000 lb tare added for TomTom only.** The load the user enters is the cargo. For routing, the backend adds a 35,000 lb tractor-trailer tare and sends the total to TomTom as the vehicle weight, because road restrictions apply to the whole truck. The risk rules use the load alone, as the brief specifies.
- **No Travel ranked above Severe.** The brief ranks routes by Severe miles first. No Travel is worse than Severe, so it was added as the first ranking key.
- **Heatmap hour 0 is now**, not the departure time, because that is how the brief defines the slider. The trip's own checkpoints already cover the departure time.
- **The first plan takes 6 to 9 s for a long trip** (about 1,000 miles). Almost all of that is TomTom computing route alternatives: one route takes about 2.5 s, three about 6 s. Repeating a trip within the hour takes well under a second because it comes from the cache. Shorter trips are proportionally faster.
- **The in-memory cache is not shared on Vercel.** Routes (1 h), weather (30 min) and heatmaps (1 h) are kept in Django's local-memory cache, which belongs to a single function instance. The caches help only while that instance stays warm. Switching to Redis or the database cache is a settings change.
- **Open-Meteo free-tier limit.** The free tier allows 600 location-calls per minute and counts every coordinate in a request. One plan with its heatmap uses about 350. If you plan a second trip on a different corridor within the same minute, its heatmap reports the limit and retries on its own after a minute. The grid size was chosen to keep one trip well under the limit.
- **Missing forecast values are an error, not calm weather.** If Open-Meteo returns no wind, rain or snow value for a checkpoint hour, the plan fails with a 502 and a message instead of scoring that stretch as Low.
- **Public endpoints are rate-limited per IP**: 10 plans a minute and 150 a day, and 60 a minute for geocoding and trip reads. Over the limit, the API answers 429 with a `Retry-After` header.

## Local setup

You need Python 3.12, Node.js and a TomTom API key.

**Backend**

```
cd backend
python -m venv venv
venv\Scripts\activate            # source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env           # then fill in TOMTOM_API_KEY and DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver
```

**Frontend**, in a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to Django on port 8000.

- The base map is OpenFreeMap's free "positron" style, so no map key is needed.
- `VITE_MAP_STYLE` and `VITE_API_URL` are optional overrides; see [frontend/README.md](frontend/README.md).
- `DEBUG=True` in `.env` is for local use only. When `DATABASE_URL` is not set, the backend uses a local SQLite file.

## Running the tests

**Backend**: 139 tests, with no network or API key needed.

```
cd backend
python manage.py test trips
```

The tests are organised by layer. They cover:

- the threshold edges and the load limits, including exactly 30,000 and 40,000 lb
- checkpoint sampling, ETA interpolation, the forecast hour rule and missing forecast values
- the ranking order and the unsafe flag
- the heatmap grid and its scoring
- the routing fallback and cache, Open-Meteo rate-limit handling and per-IP throttling
- the trip and heatmap endpoints end to end, with fake routing and weather
- the TomTom and Open-Meteo adapters, with HTTP stubbed
- a rule that keeps framework code out of the domain layer

**Frontend**: type check, build and lint.

```
cd frontend
npm run build
npm run lint
```

## Deployment

The repository deploys as a single Vercel project:

- [vercel.json](vercel.json) builds the Vite app as static files.
- It runs Django through [api/index.py](api/index.py) as a Python function with a 60 s `maxDuration`.
- `/api`, `/admin` and `/static` go to the function, and everything else goes to the frontend.
- Production uses Postgres via `DATABASE_URL`, because the function's file system is read-only.

Environment variables, migrations and the post-deploy checks are covered step by step in [docs/vercel-deployment.md](docs/vercel-deployment.md).

## What I'd do next

- **Share one weather fetch between checkpoints and the heatmap.** Today they sample the corridor on different grids and time windows and rarely reuse each other's cache. Sharing one fetch would roughly halve Open-Meteo usage per trip and allow a finer heatmap.
- **Use a shared cache** (Redis or the database cache), so repeat trips and recent weather survive across function instances.
- **Make the first plan faster.** Either ask TomTom for alternatives with `traffic=false` (about 1 s faster, but the ETAs lose traffic awareness), or show the direct route first and stream in the alternatives.
- **Add heatmap extras:** a play button, a truck marker that moves along the recommended route with the slider, and a switch between risk, wind, rain and snow.
- **Add shareable trip links.** Trips are already saved by ID and served by `GET /api/trips/{id}/`. The UI only needs a `/trips/{id}` page.
- **Add rest breaks to the ETAs and a time trade-off to the ranking.** ETAs are pure driving time today, and the ranking puts weather strictly first.
- **Add frontend tests and CI** that run the backend tests, type check and lint on every push.

More detail is in [PRD section 15](docs/PRD.md#15-future-scope). The PRD, architecture, plan and task list are in [docs/](docs/).
