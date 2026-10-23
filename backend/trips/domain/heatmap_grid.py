"""
Corridor heatmap grid: points around all routes, scored for every hour from
now to +48 h with the same risk and load rules as the checkpoints.

Pure functions; fetching the forecast and caching the result are application
concerns (application/build_heatmap.py).
"""
import bisect
from datetime import datetime, timedelta

from .entities import LatLon
from .forecast import Series, conditions_at, round_coord
from .geo import cumulative_m, offset_km, unit_east_north
from .risk import level_score
from .timeutil import floor_hour

# Open-Meteo's free tier counts every location in a request against a limit of
# 600 per minute. The trip's own checkpoint weather uses about 100, so the grid
# stays around 250 points to leave headroom (0.4 deg gave 330, 0.3 deg about 500).
ALONG_STEP_KM = 25  # a point about every 25 km along each route
SIDE_OFFSET_KM = 30  # plus one point this far to each side
CELL_DEG = 0.5  # grid cell (~55 km); overlapping routes and nearby samples share cells
HOURS = 49  # hour 0 (now) .. hour 48


def _cell(point: tuple[float, float]) -> tuple[float, float]:
    """Snap a point to the CELL_DEG grid, on the weather cache's coordinate precision."""
    lat, lon = point
    return round_coord(round(lat / CELL_DEG) * CELL_DEG, round(lon / CELL_DEG) * CELL_DEG)


def _sample_along(points: list[tuple[float, float]], step_m: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """
    Points every `step_m` along a polyline (plus the end), each with the unit
    direction of travel there as (east, north).
    """
    if len(points) < 2:
        return [(points[0], (0.0, 1.0))] if points else []
    along = cumulative_m(points)
    total = along[-1]
    marks = [i * step_m for i in range(int(total // step_m) + 1)]
    if total - marks[-1] > 1:
        marks.append(total)

    out = []
    for m in marks:
        i = max(1, min(bisect.bisect_left(along, m), len(points) - 1))
        (lat1, lon1), (lat2, lon2) = points[i - 1], points[i]
        span = along[i] - along[i - 1]
        t = (m - along[i - 1]) / span if span else 0.0
        point = (lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t)
        out.append((point, unit_east_north(points[i - 1], points[i])))
    return out


def corridor_points(lines: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """
    Grid around all routes: a point every ALONG_STEP_KM along each line plus one
    SIDE_OFFSET_KM to the left and right, snapped to CELL_DEG cells and
    de-duplicated, in a stable order.
    """
    seen: set[tuple[float, float]] = set()
    out: list[tuple[float, float]] = []

    def add(p: tuple[float, float]) -> None:
        cell = _cell(p)
        if cell not in seen:
            seen.add(cell)
            out.append(cell)

    for line in lines:
        for point, (east, north) in _sample_along(line, ALONG_STEP_KM * 1000):
            add(point)
            add(offset_km(point, -north * SIDE_OFFSET_KM, east * SIDE_OFFSET_KM))  # left of travel
            add(offset_km(point, north * SIDE_OFFSET_KM, -east * SIDE_OFFSET_KM))  # right of travel
    return out


def hour_range(now: datetime) -> list[datetime]:
    start = floor_hour(now)
    return [start + timedelta(hours=i) for i in range(HOURS)]


def score_hours(points: list[LatLon], hours: list[datetime], data: dict[LatLon, Series], load_lb: int) -> list[list[int]]:
    """values[hour][point] = risk score 0-4, using the same hour rules as the checkpoints."""
    values = []
    for hour in hours:
        row = []
        for point in points:
            c = conditions_at(data.get(point, {}), hour)
            row.append(level_score(c.wind_mph, c.rain_in_hr, c.snow_in_hr, load_lb))
        values.append(row)
    return values
