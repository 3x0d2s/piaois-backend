from django.db import models


class Measurement(models.Model):
    """Измерение с независимой от внешнего API нормализованной схемой"""

    station_id = models.CharField(max_length=100)
    observed_at = models.DateTimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_name = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=30, default="open-meteo")
    risk_score = models.FloatField(null=True, blank=True)
    metrics = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Measurement"
        ordering = ["-observed_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["station_id", "latitude", "longitude", "observed_at"],
                name="measurement_station_place_time",
            ),
        ]
        indexes = [
            models.Index(
                fields=["latitude", "longitude", "-observed_at"],
                name="measurement_location_idx",
            ),
            models.Index(fields=["-observed_at", "-id"], name="measurement_time_idx"),
            models.Index(
                fields=["station_id", "-observed_at", "-id"],
                name="measurement_station_idx",
            ),
            models.Index(
                fields=["risk_score", "-observed_at"], name="measurement_risk_idx"
            ),
        ]
