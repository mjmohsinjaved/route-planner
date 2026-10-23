# Route Planner frontend

React 19 + TypeScript + Vite single-page app. It collects a trip, calls the Django API, and draws the three routes, their risk-colored checkpoints, the route cards and the 48-hour weather heatmap on a MapLibre map. Requirements are in [`../docs/PRD.md`](../docs/PRD.md); the structure and decisions are in [`../docs/architecture.md`](../docs/architecture.md#5-frontend).

## Setup

```
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/api` to Django on `http://127.0.0.1:8000`, so start the backend first (see [`../backend/README.md`](../backend/README.md)).

| Script | Does |
|---|---|
| `npm run dev` | Vite dev server with the `/api` proxy |
| `npm run build` | Type check (`tsc -b`) and production build into `dist/` |
| `npm run lint` | ESLint |
| `npm run preview` | Serve the production build locally |

There are no frontend unit tests yet (see Future scope in the PRD). The type check and lint are the automated checks.

## Environment variables

Both are optional.

| Variable | Default | Use |
|---|---|---|
| `VITE_API_URL` | `/api` | Backend base URL when it is not on the same origin. On Vercel the app and API share one origin, so it stays unset |
| `VITE_MAP_STYLE` | `https://tiles.openfreemap.org/styles/positron` | MapLibre style URL for the base map (OpenFreeMap needs no key) |

## Structure

Atomic design: atoms → molecules → organisms → templates → pages.

```
src/
├── api/               # axios client, query keys, hooks: useGeocode, usePlanTrip, useHeatmap
├── components/
│   ├── atoms/         # FieldLabel, Stat, Swatch
│   ├── molecules/     # PlaceField, PresetChips, IntervalToggle, RouteCard, RiskBar, Legend,
│   │                  # HeatmapSlider, EmptyState, MapBanner
│   ├── organisms/     # TripForm, RouteList, MapView (lazy-loaded), HeatmapLayer
│   ├── templates/     # PlannerLayout: sidebar beside the map from 768 px, stacked below
│   └── pages/         # PlannerPage wires form, list, map and slider
├── hooks/             # use-planner-map (MapLibre setup), use-debounced
├── store/             # Zustand: selected route, heatmap hour, heatmap on/off
├── theme/             # tokens, MUI theme, one risk color scale used everywhere
├── utils/             # polyline and risk segments, formatting, checkpoint popup
├── constants/         # example trips
└── types.ts           # API shapes
```

How it behaves:

- **State.** Server data (trip, heatmap, suggestions) is in TanStack Query; UI state shared by the list, map and slider is in the Zustand store. The selected route falls back to the recommended one for any trip the user has not chosen on.
- **Heatmap.** The 49 hours load once per trip. Each grid point carries all 49 scores as properties, and the slider only changes which property colors the layer, so dragging it makes no requests. If the API answers 429 (Open-Meteo's limit), the slider says so and the query retries once after 61 s.
- **Map.** One GeoJSON source per layer, updated in place. MapLibre and its stylesheet load in a separate chunk, so the form paints first. Without WebGL, or if the style fails to load, a banner replaces the map and the cards still work.
- **Form.** Autocomplete is debounced by 300 ms and searches after 2 characters. The form checks the same rules as the API (departure window, load 1 to 100,000 lb, distinct places) before it sends.
- **Errors.** Every API error carries a `detail` sentence, which is shown as is.
