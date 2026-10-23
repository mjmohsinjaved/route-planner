# Heatmap: spec

Weather risk along the whole trip corridor for the next 48 hours, shown on the map with a slider. Implements PRD FR-10.

## 1. What the user sees

- After a trip is planned, soft colored blobs appear around all 3 routes. Colors are the same five risk colors as the legend: Low, Moderate, High, Severe, No Travel.
- A slider under the map goes from 0 to 48 hours. Its label shows the real time and the offset, for example `Wed 14:00 · +6 h`. Hour 0 is the current hour.
- Moving the slider repaints the map at once. There is no loading state and no network call.
- A switch turns the heatmap off so the route colors stay readable.
- Each point shows its own level. Points do not add up, so a calm area never looks stormy because it has many points.

## 2. Requirements

| Id | Requirement |
|---|---|
| H1 | Grid: a point about every 25 km along each of the 3 routes, plus one point about 30 km to each side. Duplicates removed. |
| H2 | Weather for all grid points for 49 hours (hour 0 to hour 48) in one batched job. |
| H3 | Each point is scored for each hour with the same wind, rain, snow and load rules as the checkpoints (PRD section 6). Score 0 Low to 4 No Travel. |
| H4 | Response shape is compact: `points`, `hours`, `values[hour][point]`. |
| H5 | The result is cached per trip so reopening a trip shows the heatmap at once. |
| H6 | The frontend loads the heatmap once per trip and keeps all 49 hours in memory. |
| H7 | Slider labels show absolute local time plus the offset. |
| H8 | Heatmap can be switched off. |

## 3. API

`GET /api/trips/{id}/heatmap/`

```json
{
  "points": [[41.8, -87.6], [41.8, -87.4]],
  "hours": ["2026-10-21T08:00:00Z", "2026-10-21T09:00:00Z"],
  "values": [[0, 1], [0, 2]]
}
```

- `points[i]` is `[lat, lon]`, snapped to a 0.5° grid.
- `hours` has 49 entries, UTC, on the hour. `hours[0]` is the hour the heatmap was built.
- `values[h][i]` is the risk score for point `i` at hour `h`.

| Status | When |
|---|---|
| 200 | Heatmap built or served from cache |
| 404 | No trip with that id |
| 429 | Open-Meteo's per-minute allowance is used up. `Retry-After: 60`; body has `detail`. |
| 502 | Open-Meteo failed or returned an incomplete forecast. Body has `detail`. |
| 504 | Open-Meteo timed out |

## 4. Acceptance

- Chicago to Denver returns about 250 points, 49 hours and 49 rows.
- A second request for the same trip returns within milliseconds.
- Dragging the slider repaints without any request in the browser's network tab.
- Tests cover grid building, hour scoring and the endpoint with weather mocked.

## 5. Out of scope

- Heatmap for an arbitrary area without a trip.
- Hours beyond +48 h.
- Interpolated surfaces between points. Blobs are drawn per point.

## 6. Future scope

Not built: a play button that steps through the hours, a truck marker moving along the recommended route with the slider, a switch between risk, wind, rain and snow, hour 0 anchored to the departure, and a finer grid once checkpoints and heatmap share one weather fetch. See [PRD section 15](../../PRD.md#15-future-scope).
