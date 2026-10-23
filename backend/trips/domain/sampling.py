"""Checkpoints every N miles along a route, each with its ETA."""
from datetime import datetime, timedelta

from .entities import Checkpoint, Route
from .geo import METERS_PER_MILE, cumulative_m, interpolate

ALLOWED_INTERVALS_MI = (10, 25, 50)


def sample_checkpoints(route: Route, interval_mi: int, departure: datetime) -> list[Checkpoint]:
    """
    Return checkpoints at the origin, every `interval_mi` miles, and the destination.

    Each checkpoint owns the stretch of road since the previous checkpoint
    (`segment_mi`), which is what route metrics add up later.

    Distances along the polyline are scaled to the route's official length so
    mile markers match the distance shown to the user. ETA comes from the
    route's own (meters, seconds) anchors, not from an average speed.
    """
    if interval_mi not in ALLOWED_INTERVALS_MI:
        raise ValueError(f"interval_mi must be one of {ALLOWED_INTERVALS_MI}")

    points = route.points
    total_m = route.distance_m
    along = cumulative_m(points)
    scale = total_m / along[-1] if along[-1] else 1.0
    along = [d * scale for d in along]

    anchor_m = [m for m, _ in route.time_anchors]
    anchor_s = [s for _, s in route.time_anchors]
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]

    step_m = interval_mi * METERS_PER_MILE
    marks = [0.0]
    next_mark = step_m
    while next_mark < total_m - 1:  # skip a mark sitting on the destination
        marks.append(next_mark)
        next_mark += step_m
    marks.append(float(total_m))

    checkpoints = []
    for i, m in enumerate(marks):
        seconds = interpolate(m, anchor_m, anchor_s)
        checkpoints.append(
            Checkpoint(
                index=i,
                mile=round(m / METERS_PER_MILE, 1),
                segment_mi=round((m - marks[i - 1]) / METERS_PER_MILE, 3) if i else 0.0,
                lat=round(interpolate(m, along, lats), 5),
                lon=round(interpolate(m, along, lons), 5),
                eta=departure + timedelta(seconds=round(seconds)),
            )
        )
    return checkpoints
