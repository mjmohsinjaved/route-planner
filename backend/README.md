# Route Planner backend

Django + Django REST Framework API that plans a truck trip: 3 routes from TomTom, hourly weather from Open-Meteo at every checkpoint, a risk level per checkpoint, and a recommended route. Design and API shapes are in `../docs/`.

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env     # then paste your TomTom key into TOMTOM_API_KEY
python manage.py migrate
python manage.py runserver
```

Run the tests with `python manage.py test trips` (139 tests). The use cases run against in-memory fakes and the adapters against stubbed HTTP, so no key or network is needed.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health/` | Health check |
| GET | `/api/geocode/?q=` | Up to 5 place suggestions |
| POST | `/api/trips/` | Plan a trip |
| GET | `/api/trips/{id}/` | Reopen a saved trip |
| GET | `/api/trips/{id}/heatmap/` | Corridor risk for the next 49 hours (hour 0 to 48) |

Every error has a `detail` sentence: 400 invalid input, 404 unknown trip, 422 no truck route, 429 throttled or weather limit (with `Retry-After`), 502 a provider failed or a forecast value is missing, 504 timeout. Full shapes are in [`../docs/PRD.md`](../docs/PRD.md#8-api-specification).

## Notes

- **Vehicle weight vs load weight.** The `load_lb` the user enters is the cargo. For routing, `domain/vehicle_rules.py` adds a 35,000 lb tractor-trailer tare and sends the total to TomTom as `vehicleWeight`, because road restrictions apply to the whole truck. The risk rules in `domain/risk.py` use the load alone, as the brief specifies.
- **Times.** Departure is truncated to whole seconds and stored in UTC. ETAs and arrivals are returned as ISO 8601 with a `Z` suffix.
- **Caching.** Geocode results are cached for 24 h, weather for 30 min as one hourly series per 0.1° coordinate, routes for 1 h and heatmaps for 1 h per trip and clock hour, all in Django's local-memory cache.
- **Route cache granularity.** Routes are cached for an hour, keyed by origin, destination, load and the departure *hour*. Two trips planned for 08:01 and 08:59 share one TomTom response, so the second one's durations reflect traffic as of the first request. Up to an hour of traffic drift is accepted in exchange for one TomTom call per hour bucket.

## Deploy

See [`../docs/vercel-deployment.md`](../docs/vercel-deployment.md).
