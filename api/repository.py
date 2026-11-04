import math
from datetime import UTC
from typing import Any, cast

from bson import ObjectId
from django.db import connections
from django.db.models import QuerySet
from django_mongodb_backend.base import DatabaseWrapper

from api.errors import InvalidMeasurement, MeasurementNotFound
from api.models import Measurement
from api.schemas import MeasurementFilters


def filtered_measurements(filters: MeasurementFilters) -> QuerySet[Measurement]:
    queryset = Measurement.objects.all()
    if filters.location_id is not None:
        try:
            latitude, longitude = map(float, filters.location_id.split(","))
        except ValueError:
            raise InvalidMeasurement(
                "location_id must contain latitude,longitude"
            ) from None
        if not (
            math.isfinite(latitude)
            and math.isfinite(longitude)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            raise InvalidMeasurement("Invalid location_id coordinates")
        queryset = queryset.filter(latitude=latitude, longitude=longitude)
    for field in ("latitude", "longitude", "risk"):
        low = getattr(filters, f"{field}_min")
        high = getattr(filters, f"{field}_max")
        if (
            low is not None
            and not math.isfinite(low)
            or high is not None
            and not math.isfinite(high)
        ):
            raise InvalidMeasurement("Filter values must be finite")
        if low is not None and high is not None and low > high:
            raise InvalidMeasurement(f"{field}_min must not exceed {field}_max")
        model_field = "risk_score" if field == "risk" else field
        if low is not None:
            queryset = queryset.filter(**{f"{model_field}__gte": low})
        if high is not None:
            queryset = queryset.filter(**{f"{model_field}__lte": high})
    if (
        filters.time_from is not None
        and filters.time_to is not None
        and filters.time_from > filters.time_to
    ):
        raise InvalidMeasurement("time_from must not exceed time_to")
    if filters.time_from is not None:
        queryset = queryset.filter(observed_at__gte=filters.time_from.astimezone(UTC))
    if filters.time_to is not None:
        queryset = queryset.filter(observed_at__lte=filters.time_to.astimezone(UTC))
    if filters.station_id is not None:
        queryset = queryset.filter(station_id=filters.station_id)
    if filters.source is not None:
        queryset = queryset.filter(source=filters.source)
    if filters.risk_level is not None:
        lower, upper = {
            "low": (0, 25),
            "moderate": (25, 50),
            "high": (50, 75),
            "very_high": (75, 101),
        }[filters.risk_level]
        queryset = queryset.filter(risk_score__gte=lower, risk_score__lt=upper)
    return queryset


def get_measurement(measurement_id: str) -> Measurement:
    record = Measurement.objects.filter(pk=ObjectId(measurement_id)).first()
    if record is None:
        raise MeasurementNotFound
    return record


def persist_measurement(
    values: dict[str, Any], measurement_id: str | None = None
) -> Measurement:
    if measurement_id is None:
        return Measurement.objects.create(**values)
    record = get_measurement(measurement_id)
    for name, value in values.items():
        setattr(record, name, value)
    record.save(update_fields=[*values, "updated_at"])
    return record


def remove_measurement(measurement_id: str) -> None:
    get_measurement(measurement_id).delete()


def location_summaries() -> list[dict[str, Any]]:
    connection = cast(DatabaseWrapper, connections["default"])
    collection = connection.get_collection(Measurement._meta.db_table)
    pipeline = [
        {"$sort": {"observed_at": -1, "_id": -1}},
        {
            "$group": {
                "_id": {"latitude": "$latitude", "longitude": "$longitude"},
                "name": {"$first": "$location_name"},
                "measurement_count": {"$sum": 1},
                "last_observed_at": {"$first": "$observed_at"},
            }
        },
    ]
    return list(collection.aggregate(pipeline, allowDiskUse=True, maxTimeMS=5000))
