"""
Risk rules from the assessment brief.

Levels are scored 0-4. The brief's ranges share edge values (0.25 sits in
both Moderate and High), so each edge belongs to the higher level, except
the No Travel edges for rain and snow, which are "> 1.00" and "> 3.0" as written.
See docs/PRD.md section 6.
"""
from .entities import Risk

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = range(5)
LEVEL_NAMES = ("Low", "Moderate", "High", "Severe", "No Travel")

LOAD_NO_TRAVEL_LB = 30_000  # wind 45-54 mph and load above this -> No Travel
LOAD_SEVERE_LB = 40_000  # wind 35-44 mph and load above this -> Severe


def wind_level(mph: float) -> int:
    if mph < 25:
        return LOW
    if mph < 35:
        return MODERATE
    if mph < 45:
        return HIGH
    if mph < 55:
        return SEVERE
    return NO_TRAVEL


def rain_level(in_hr: float) -> int:
    if in_hr < 0.10:
        return LOW
    if in_hr < 0.25:
        return MODERATE
    if in_hr < 0.50:
        return HIGH
    if in_hr <= 1.00:
        return SEVERE
    return NO_TRAVEL


def snow_level(in_hr: float) -> int:
    if in_hr < 0.5:
        return LOW
    if in_hr < 1.0:
        return MODERATE
    if in_hr < 2.0:
        return HIGH
    if in_hr <= 3.0:
        return SEVERE
    return NO_TRAVEL


def load_level(wind_mph: float, load_lb: float) -> int:
    """Extra risk from wind on a heavy load. Low means no load rule applies."""
    if wind_mph >= 55:
        return NO_TRAVEL
    if wind_mph >= 45 and load_lb > LOAD_NO_TRAVEL_LB:
        return NO_TRAVEL
    if wind_mph >= 35 and load_lb > LOAD_SEVERE_LB:
        return SEVERE
    return LOW


def level_score(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> int:
    """Worst of wind (with the load rule), rain and snow, 0-4. The number behind classify()."""
    return max(wind_level(wind_mph), load_level(wind_mph, load_lb), rain_level(rain_in_hr), snow_level(snow_in_hr))


def _num(x: float) -> str:
    """0.300 -> '0.3', 0.25 -> '0.25' (no rounding across a threshold)."""
    return f"{x:.3f}".rstrip("0").rstrip(".")


def classify(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> Risk:
    """
    Level for one checkpoint: the worst of wind, rain, snow and the load rule,
    plus a short reason naming what set it.
    """
    wind = (wind_level(wind_mph), f"Wind {wind_mph:.1f} mph")
    with_load = load_level(wind_mph, load_lb)
    if with_load > wind[0]:  # the load makes the wind worse than it is on its own
        wind = (with_load, f"Wind {wind_mph:.1f} mph + {load_lb:,.0f} lb load")

    causes = [
        wind,
        (rain_level(rain_in_hr), f"Rain {_num(rain_in_hr)} in/hr"),
        (snow_level(snow_in_hr), f"Snow {_num(snow_in_hr)} in/hr"),
    ]
    level = level_score(wind_mph, rain_in_hr, snow_in_hr, load_lb)
    name = LEVEL_NAMES[level]
    if level == LOW:
        return Risk(name, level, "All conditions Low")

    top = "; ".join(text for score, text in causes if score == level)
    return Risk(name, level, f"{top} → {name}")
