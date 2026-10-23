"""Route metrics and the recommendation (PRD section 7)."""
from .entities import AssessedCheckpoint, Recommendation, RouteAssessment, RouteMetrics
from .risk import HIGH, LEVEL_NAMES, NO_TRAVEL, SEVERE


def route_metrics(checkpoints: list[AssessedCheckpoint]) -> RouteMetrics:
    """
    Miles at each serious level and the distance-weighted average risk (0-4).
    Each checkpoint's level applies to the road since the previous checkpoint.
    """
    miles = {level: 0.0 for level in range(len(LEVEL_NAMES))}
    weighted, total = 0.0, 0.0
    for c in checkpoints:
        seg = c.segment_mi
        miles[c.level_score] += seg
        weighted += c.level_score * seg
        total += seg
    avg = weighted / total if total else float(checkpoints[0].level_score) if checkpoints else 0.0
    return RouteMetrics(
        no_travel_mi=round(miles[NO_TRAVEL], 1),
        severe_mi=round(miles[SEVERE], 1),
        high_mi=round(miles[HIGH], 1),
        avg_risk=round(avg, 2),
    )


# Ranking keys in priority order: (field, label used in the reason). A field is on
# RouteMetrics, except duration_min which is on the route itself.
# No Travel comes first: the brief ranks Severe first, and No Travel is worse.
RANK_KEYS = (
    ("no_travel_mi", "No Travel miles"),
    ("severe_mi", "Severe miles"),
    ("high_mi", "High miles"),
    ("avg_risk", "average risk"),
    ("duration_min", "travel time"),
)


def _get(route: RouteAssessment, field: str) -> float:
    return route.duration_min if field == "duration_min" else getattr(route.metrics, field)


def _sort_key(route: RouteAssessment) -> tuple:
    return tuple(_get(route, field) for field, _ in RANK_KEYS)


def format_duration(minutes: float) -> str:
    minutes = round(minutes)
    h, m = divmod(abs(minutes), 60)
    return f"{h} h {m} min" if h else f"{m} min"


def _value(field: str, route: RouteAssessment) -> str:
    v = _get(route, field)
    if field == "duration_min":
        return format_duration(v)
    if field == "avg_risk":
        return f"{v:.2f}"
    return f"{v:,.1f}"  # miles: one decimal, like the metrics, so 0.4 never reads as 0


def recommend(routes: list[RouteAssessment]) -> Recommendation:
    """
    Pick the best route. Returns the winner, the ranked ids, a one-sentence
    reason, and whether every route crosses No Travel weather.
    """
    ranked = sorted(routes, key=_sort_key)
    best = ranked[0]
    unsafe = all(r.metrics.no_travel_mi > 0 for r in routes)

    if len(ranked) == 1:
        reason = f"Route {best.id} is the only route found."
    else:
        runner = ranked[1]
        field, label = next(
            ((f, lbl) for f, lbl in RANK_KEYS if _get(best, f) != _get(runner, f)),
            (None, None),
        )
        if field is None:
            reason = (
                f"Route {best.id} recommended: it ties with Route {runner.id} "
                "on weather risk and travel time."
            )
        elif field == "duration_min":
            reason = (
                f"Route {best.id} recommended: weather risk is the same as Route {runner.id}, "
                f"and it is faster ({format_duration(best.duration_min)} vs "
                f"{format_duration(runner.duration_min)})."
            )
        else:
            if field == "avg_risk":
                reason = (
                    f"Route {best.id} recommended: lower average risk "
                    f"({_value(field, best)} vs {_value(field, runner)} on Route {runner.id})"
                )
            else:
                best_miles = "no" if _get(best, field) == 0 else _value(field, best)
                reason = (
                    f"Route {best.id} recommended: {best_miles} {label} "
                    f"vs {_value(field, runner)} on Route {runner.id}"
                )
            fastest = min(routes, key=lambda r: r.duration_min)
            extra = best.duration_min - fastest.duration_min
            if extra > 0:
                reason += f", {format_duration(extra)} longer than the fastest (Route {fastest.id})."
            else:
                reason += ", and it is also the fastest."

    if unsafe:
        reason += " Every route crosses No Travel weather at this departure time; consider leaving later."

    return Recommendation(
        recommended_route_id=best.id,
        ranking=[r.id for r in ranked],
        reason=reason,
        unsafe=unsafe,
    )
