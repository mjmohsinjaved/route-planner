from datetime import timedelta
from datetime import timezone as dt_timezone

from django.utils import timezone
from rest_framework import serializers

from ...domain.geo import haversine_m

MAX_DAYS_AHEAD = 14  # leaves room for the trip itself inside Open-Meteo's 16-day forecast
PAST_GRACE = timedelta(minutes=15)  # allow "leave now" even if the form sat open a while


class PlaceSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class TripRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=1, max_value=100_000)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_departure(self, value):
        now = timezone.now()
        if value < now - PAST_GRACE:
            raise serializers.ValidationError("Departure can't be in the past.")
        if value > now + timedelta(days=MAX_DAYS_AHEAD):
            raise serializers.ValidationError(f"Forecast is available up to {MAX_DAYS_AHEAD} days ahead.")
        return max(value, now).replace(microsecond=0).astimezone(dt_timezone.utc)  # a few minutes ago counts as "now"

    def validate(self, data):
        o, d = data["origin"], data["destination"]
        if haversine_m((o["lat"], o["lon"]), (d["lat"], d["lon"])) < 1000:
            raise serializers.ValidationError({"destination": "Destination must be different from the origin."})
        return data
