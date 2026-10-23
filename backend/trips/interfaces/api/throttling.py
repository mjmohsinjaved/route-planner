"""
Per-IP limits on the public endpoints, so one client cannot burn the TomTom
and Open-Meteo allowances. Rates live in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].

Each endpoint gets a burst limit (per minute) and a sustained limit (per day).
Counters live in the Django cache: per function instance on Vercel, which still
bounds what a single warm instance will forward upstream. Over the limit, DRF
answers 429 with a `detail` message and a Retry-After header.
"""
from rest_framework.throttling import AnonRateThrottle


class PlanBurstThrottle(AnonRateThrottle):
    scope = "plan_burst"


class PlanDayThrottle(AnonRateThrottle):
    scope = "plan_day"


class GeocodeBurstThrottle(AnonRateThrottle):
    scope = "geocode_burst"


class GeocodeDayThrottle(AnonRateThrottle):
    scope = "geocode_day"


class ReadBurstThrottle(AnonRateThrottle):
    scope = "read_burst"


class ReadDayThrottle(AnonRateThrottle):
    scope = "read_day"


PLAN = [PlanBurstThrottle, PlanDayThrottle]
GEOCODE = [GeocodeBurstThrottle, GeocodeDayThrottle]
READ = [ReadBurstThrottle, ReadDayThrottle]
