# Plan: Route Planner

Build and submit in **1.5 days**, with a half-day buffer (2 days maximum). Detailed tasks are in [task.md](task.md).

---

## Goal

A hosted React + Django app that recommends the safest of 3 truck routes using weather at each checkpoint's ETA, load weight and travel time, with a 0–48 hour weather heatmap.

**Grading weights:** 40% logic · 40% UI and map smoothness · 15% code quality · 5% docs and Loom.
**Rule from the brief:** correctness and clarity before extra features.

---

## Schedule

| Block | Focus | Done when |
|---|---|---|
| **Day 1 morning** (4 h) | Setup, geocoding, 3-route routing | 3 routes come back for Chicago → Denver |
| **Day 1 afternoon** (4 h) | Checkpoints, ETA, weather, risk, recommendation, tests | Tests pass and the API names the best route |
| **Day 1 evening** (3 h) | Trip form, route cards, map | A sample trip shows everything on one screen |
| **Day 2 morning** (4 h) | Heatmap + slider, caching | The slider moves smoothly with no loading |
| **Day 2 afternoon** (4 h) | Deploy, README, Loom | Repo, app and Loom links are sent |
| **Day 2 evening** | Buffer only | Used only if something slips |

---

## Day 1 target

A working local app: enter a trip, get 3 routes, see checkpoints colored by risk, and see the recommended route with its reason, all on a map.

## Day 2 target

Heatmap with slider, caching, the app online, README written, Loom recorded, links submitted.

---

## Critical path

Routing → checkpoints and ETA → weather → risk → recommendation.

Everything else (map, heatmap, polish) depends on this chain. If it is not working by the end of Day 1 afternoon, stop and fix it before starting UI work.

---

## If time runs short, cut in this order

1. Play button and moving truck marker on the heatmap
2. Extra charts (risk-along-route strip)
3. Shareable trip links (`GET /api/trips/{id}/`)
4. Visual polish beyond clean spacing and a legend

**Never cut:** exactly 3 routes, correct risk rules, tests for the rules, the recommendation reason, the heatmap slider, the hosted link.

---

## Not doing (to save time)

- Docker
- Postgres (SQLite is enough) *(changed: production uses Postgres, see "Where it ended up")*
- Redis (Django's built-in cache is enough)
- User accounts

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Routing API returns fewer than 3 routes | Fails a core requirement | Via-point fallback |
| Weather on a demo day is calm everywhere | Map looks all green in the Loom | Pick a windy corridor on recording day (for example I-80 in Wyoming) |
| Free hosting sleeps | Slow first load for the reviewer | Use a host that stays warm, or open the link just before sharing |
| API free-tier limits | Errors during testing | Cache every external call |
| Time overrun on UI polish | Logic left unfinished | Logic first; polish only after tests pass |

---

## Where it ended up

All build blocks are done and the app is live on Vercel. Differences from this plan:

- **Hosting.** One Vercel project serves the static frontend and Django as a Python function, instead of a separate Railway or Render backend. That forced **Postgres** in production, because the function's file system is read-only. SQLite is still the local default.
- **First-plan speed.** The 3 s target was not met: a 1,000 mile trip takes 6 to 9 s, almost all of it TomTom computing alternatives. A repeat trip takes about 0.06 s from cache.
- **Extras added.** Rate limiting, error `detail` on every response, Open-Meteo limit handling, tablet layout, map error states and code splitting. See "Done beyond the plan" in [task.md](task.md).
- **Cut and still open.** Play button, moving truck marker, metric switch, risk chart and the shareable-link UI. They are in [PRD section 15, Future scope](PRD.md#15-future-scope).
- **Still to do by hand.** Incognito test of the live app, the Loom, the README screenshot, the checklist below, the `v1.0` tag.

---

## Submission checklist

- [ ] Hosted app loads quickly from an incognito window
- [ ] Every trip returns exactly 3 routes
- [ ] Units correct: miles, mph, in/hr, lb
- [ ] Boundary values classified as documented, with tests
- [ ] Changing load from 25,000 to 45,000 lb visibly changes risk on a windy route
- [ ] Recommendation reason matches the numbers on the cards
- [ ] Heatmap slider smooth across all 49 hours
- [ ] No API keys in the repo or frontend bundle
- [ ] README has the app link, Loom link, setup steps and assumptions
- [ ] Loom is 5–10 minutes
