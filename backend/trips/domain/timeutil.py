"""Time helpers: hour rounding and the timestamp format every API response uses."""
from datetime import datetime, timezone


def floor_hour(t: datetime) -> datetime:
    """The start of the UTC hour containing t."""
    return t.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def iso_z(t: datetime) -> str:
    """ISO 8601 in UTC with a Z suffix, the format every API response uses."""
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso_z(value: str) -> datetime:
    """Inverse of iso_z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
