import uuid

from django.db import models


class TripPlan(models.Model):
    """One planned trip: the inputs and the full result, stored whole as JSON."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    origin = models.JSONField()  # {name, lat, lon}
    destination = models.JSONField()
    departure = models.DateTimeField()  # stored in UTC
    load_lb = models.PositiveIntegerField()
    interval_mi = models.PositiveSmallIntegerField()
    result = models.JSONField()  # routes, checkpoints, recommendation

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.origin.get('name')} → {self.destination.get('name')} ({self.departure:%Y-%m-%d %H:%M})"
