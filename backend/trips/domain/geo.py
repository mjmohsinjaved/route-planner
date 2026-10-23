"""Small geometry helpers: distances, interpolation, offsets and polyline encoding."""
import math

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344
KM_PER_DEG_LAT = 111.32


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in meters between two (lat, lon) points."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def cumulative_m(points: list[tuple[float, float]]) -> list[float]:
    """Running distance in meters at each point, starting at 0."""
    totals = [0.0]
    for prev, cur in zip(points, points[1:]):
        totals.append(totals[-1] + haversine_m(prev, cur))
    return totals


def interpolate(x: float, xs: list[float], ys: list[float]) -> float:
    """Linear interpolation of y at x. `xs` must be sorted ascending."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:  # binary search for the bracketing pair
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    span = xs[hi] - xs[lo]
    if span == 0:
        return ys[lo]
    return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / span


def offset_km(point: tuple[float, float], east_km: float, north_km: float) -> tuple[float, float]:
    """Point moved east/north by the given kilometres (flat-earth, fine for < 100 km)."""
    lat, lon = point
    km_per_deg_lon = KM_PER_DEG_LAT * math.cos(math.radians(lat)) or 1e-9
    return (lat + north_km / KM_PER_DEG_LAT, lon + east_km / km_per_deg_lon)


def unit_east_north(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Unit direction from a to b as (east, north). (0, 1) for a zero-length step."""
    east = (b[1] - a[1]) * math.cos(math.radians(a[0]))
    north = b[0] - a[0]
    length = math.hypot(east, north)
    return (east / length, north / length) if length else (0.0, 1.0)


def thin(points: list[tuple[float, float]], max_points: int = 1500) -> list[tuple[float, float]]:
    """Keep at most `max_points`, always including the first and last point."""
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    kept = points[::step]
    if kept[-1] != points[-1]:
        kept.append(points[-1])
    return kept


def encode_polyline(points: list[tuple[float, float]], precision: int = 5) -> str:
    """Google encoded polyline (decode on the frontend with @mapbox/polyline)."""
    factor = 10**precision
    out, prev_lat, prev_lon = [], 0, 0
    for lat, lon in points:
        ilat, ilon = round(lat * factor), round(lon * factor)
        for delta in (ilat - prev_lat, ilon - prev_lon):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                out.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            out.append(chr(value + 63))
        prev_lat, prev_lon = ilat, ilon
    return "".join(out)


def decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Inverse of encode_polyline: (lat, lon) tuples."""
    factor = 10**precision
    points, index, lat, lon = [], 0, 0, 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            result = shift = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append((lat / factor, lon / factor))
    return points
