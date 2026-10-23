# Heatmap and speed: plan and outcome

Work plan from Oct 21, 2026, with what actually happened. Source: "Heatmap and Speed Plan" (Luqman Ud Din Muhammad).

## 1. Order of work

| Step | Scope | Estimate | Status |
|---|---|---|---|
| 1 | Speed: parallel TomTom fallback calls, parallel weather batches, 1 h route cache, timing logs | 1 h | Done, commit `ff2a5b3` |
| 2 | Heatmap backend: grid, 49 h weather, scoring, endpoint, cache, tests | 2 h (with step 3) | Done, commit `aa31311` |
| 3 | Heatmap frontend: layer, slider with real-time labels, on/off switch | | Done, commit `7ab2851` |
| 4 | Deliver as commits | | Done |

## 2. Targets and measurements

Chicago to Denver, 38,000 lb, 25 mile interval, measured through the Django test client against live TomTom and Open-Meteo.

| Target | Goal | Measured | Met |
|---|---|---|---|
| Repeat plan, same trip | under 1 s | 0.06 s | Yes |
| First plan | 3 to 4 s | 9.2 s | No |
| Heatmap, first request | | 2.3 s | |
| Heatmap, reopened trip | instant | 4 ms | Yes |
| Grid points | 300 to 400 | about 250 (487 before the rate-limit fix, 330 at 0.4°, then 0.5° cells for headroom) | Under, on purpose |
| Slider repaints with no loading | yes | by design, needs a browser check | |

## 3. What the first-plan measurement showed

The plan assumed the 9.5 s was extra TomTom calls made one after another. The new timing log shows otherwise:

```
tomtom direct: 3 routes (3 distinct) in 8.01s
plan_trip: routes 8.01s, checkpoints 0.04s, weather 0.95s, risk+rank 0.01s
```

The single direct request with `maxAlternatives=2` returned all 3 routes and took 8 s on its own. The fallback never ran, so running it in parallel changed nothing for this trip. Request variants were timed:

| Request | Time | Routes |
|---|---|---|
| alternatives 2, coded instructions (current) | 5.9 s | 3 |
| alternatives 2, no instructions | 5.8 s | 3 |
| alternatives 0 | 2.5 s | 1 |
| alternatives 2, `traffic=false` | 4.8 s | 3 |

The cost is TomTom computing alternatives for a 1,000 mile truck route. Options not taken, for the owner to decide:

- `traffic=false` saves about 1 s but changes ETAs.
- Replace TomTom's alternatives with via-point routes requested in parallel: about 3 s, but detours are longer and less natural than TomTom's own alternatives (Route B was 1,185 mi by via-point versus 1,015 mi for TomTom's alternative).

Shorter trips will be faster in proportion.

## 4. Bug found on the way

The repeat plan was still 6 s after adding the route cache. Django's local-memory cache keeps 300 entries by default and the weather module stored one entry per cell and hour, several thousand per trip, so every trip evicted the routes and the weather itself. Fixed by caching one series per cell and raising `MAX_ENTRIES` to 20,000. The weather cache had never been hitting before this.

## 5. Deviations from the plan

- Grid cells are 0.2° rather than the 0.1° weather grid, to keep the count near the target. See architecture.md section 4.
- The heatmap cache lives 1 hour, not indefinitely, so hour 0 stays close to "now".
- The first browser run showed "Heatmap unavailable". Open-Meteo was answering 429 "Minutely API request limit exceeded": its free tier counts every location in a request, 600 per minute, and a 487-point heatmap plus the trip's own weather used it all. The grid now snaps to 0.4° cells with 25 km spacing (about 330 points; later widened to 0.5° cells, about 250 points, for more headroom), the weather module raises a clear `WeatherRateLimited`, and the frontend retries once after a minute with a message instead of a dead state. See architecture.md section 2.5.

## 6. Follow-ups

- Browser check of the slider on a real Chicago to Denver run.
- Decide whether to trade traffic-aware ETAs for about 1 s on first plan.
- ~~Vite warns the main chunk is over 500 kB (MapLibre).~~ Done: MapLibre is lazy-loaded in its own chunk (see `docs/architecture.md` section 5.3).
- Still open, and now in [Future scope](../../PRD.md#15-future-scope): play button, moving truck marker, metric switch, one shared weather fetch for checkpoints and heatmap.
