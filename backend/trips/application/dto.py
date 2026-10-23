"""
Commands going in, and the JSON shape of a trip going out and into storage.

`trip_to_payload` is the one definition of a trip's wire format (PRD section 8).
The API returns it and the repository stores it, so the two cannot drift.
"""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..domain.entities import (
    AssessedCheckpoint,
    Checkpoint,
    Conditions,
    Heatmap,
    Place,
    Recommendation,
    Risk,
    RouteAssessment,
    RouteMetrics,
    Trip,
)
from ..domain.geo import decode_polyline, encode_polyline
from ..domain.timeutil import iso_z, parse_iso_z


@dataclass(frozen=True)
class PlanTripCommand:
    origin: Place
    destination: Place
    departure: datetime  # UTC, whole seconds
    load_lb: int
    interval_mi: int


def _place(p: Place) -> dict:
    return {"name": p.name, "lat": p.lat, "lon": p.lon}


def _checkpoint(c: AssessedCheckpoint) -> dict:
    cp, w, r = c.checkpoint, c.conditions, c.risk
    return {
        "index": cp.index,
        "mile": cp.mile,
        "segment_mi": cp.segment_mi,
        "lat": cp.lat,
        "lon": cp.lon,
        "eta": iso_z(cp.eta),
        "wind_mph": w.wind_mph,
        "gust_mph": w.gust_mph,
        "rain_in_hr": w.rain_in_hr,
        "snow_in_hr": w.snow_in_hr,
        "level": r.level,
        "level_score": r.level_score,
        "reason": r.reason,
    }


def _route(r: RouteAssessment) -> dict:
    m = r.metrics
    return {
        "id": r.id,
        "distance_mi": r.distance_mi,
        "duration_min": r.duration_min,
        "arrival": iso_z(r.arrival),
        "no_travel_mi": m.no_travel_mi,
        "severe_mi": m.severe_mi,
        "high_mi": m.high_mi,
        "avg_risk": m.avg_risk,
        "geometry": encode_polyline(r.geometry),
        "checkpoints": [_checkpoint(c) for c in r.checkpoints],
    }


def trip_to_payload(trip: Trip) -> dict:
    rec = trip.recommendation
    return {
        "id": str(trip.id),
        "origin": _place(trip.origin),
        "destination": _place(trip.destination),
        "departure": iso_z(trip.departure),
        "load_lb": trip.load_lb,
        "interval_mi": trip.interval_mi,
        "recommended_route_id": rec.recommended_route_id,
        "ranking": rec.ranking,
        "recommendation_reason": rec.reason,
        "unsafe": rec.unsafe,
        "routes": [_route(r) for r in trip.routes],
    }


def _assessed(d: dict) -> AssessedCheckpoint:
    return AssessedCheckpoint(
        checkpoint=Checkpoint(
            index=d["index"], mile=d["mile"], segment_mi=d["segment_mi"], lat=d["lat"], lon=d["lon"], eta=parse_iso_z(d["eta"])
        ),
        conditions=Conditions(
            wind_mph=d["wind_mph"], gust_mph=d["gust_mph"], rain_in_hr=d["rain_in_hr"], snow_in_hr=d["snow_in_hr"]
        ),
        risk=Risk(level=d["level"], level_score=d["level_score"], reason=d["reason"]),
    )


def _route_assessment(d: dict) -> RouteAssessment:
    return RouteAssessment(
        id=d["id"],
        distance_mi=d["distance_mi"],
        duration_min=d["duration_min"],
        arrival=parse_iso_z(d["arrival"]),
        metrics=RouteMetrics(
            no_travel_mi=d["no_travel_mi"], severe_mi=d["severe_mi"], high_mi=d["high_mi"], avg_risk=d["avg_risk"]
        ),
        geometry=decode_polyline(d["geometry"]),
        checkpoints=[_assessed(c) for c in d["checkpoints"]],
    )


def trip_from_payload(d: dict) -> Trip:
    return Trip(
        id=UUID(d["id"]),
        origin=Place(**d["origin"]),
        destination=Place(**d["destination"]),
        departure=parse_iso_z(d["departure"]),
        load_lb=d["load_lb"],
        interval_mi=d["interval_mi"],
        routes=[_route_assessment(r) for r in d["routes"]],
        recommendation=Recommendation(
            recommended_route_id=d["recommended_route_id"],
            ranking=d["ranking"],
            reason=d["recommendation_reason"],
            unsafe=d["unsafe"],
        ),
    )


def heatmap_to_payload(h: Heatmap) -> dict:
    return {
        "points": [[lat, lon] for lat, lon in h.points],
        "hours": [iso_z(hour) for hour in h.hours],
        "values": h.values,
    }
