import logging
import math
from datetime import UTC

import msgspec

from api import repository
from api.errors import InvalidMeasurement, MeasurementNotFound
from api.models import Measurement
from api.risk import calculate_risk, risk_level
from api.schemas import (
    LocationList,
    LocationResponse,
    MeasurementFilters,
    MeasurementInput,
    MeasurementPage,
    MeasurementResponse,
)

logger = logging.getLogger("api")


def validate_measurement(payload: MeasurementInput) -> None:
    for value in (payload.latitude, payload.longitude):
        if not math.isfinite(value):
            raise InvalidMeasurement("Coordinates must be finite")
    if not any(value is not None for value in payload.metrics.values()):
        raise InvalidMeasurement("At least one metric must have a value")
    for name, value in payload.metrics.items():
        if value is None:
            continue
        if not math.isfinite(value):
            raise InvalidMeasurement(f"{name} must be finite")
        if name != "temperature_2m" and value < 0:
            raise InvalidMeasurement(f"{name} must be non-negative")
        if name == "relative_humidity_2m" and value > 100:
            raise InvalidMeasurement("relative_humidity_2m must be at most 100")


def serialize(measurement: Measurement) -> MeasurementResponse:
    return msgspec.convert(
        {
            "id": str(measurement.pk),
            "location_id": f"{float(measurement.latitude)},{float(measurement.longitude)}",
            "station_id": measurement.station_id,
            "observed_at": measurement.observed_at,
            "latitude": measurement.latitude,
            "longitude": measurement.longitude,
            "location_name": measurement.location_name,
            "source": measurement.source,
            "risk_score": measurement.risk_score,
            "risk_level": risk_level(measurement.risk_score),
            "metrics": measurement.metrics,
            "created_at": measurement.created_at,
            "updated_at": measurement.updated_at,
        },
        type=MeasurementResponse,
    )


def list_measurements(filters: MeasurementFilters) -> MeasurementPage:
    ordering = (
        ("observed_at", "id") if filters.order == "asc" else ("-observed_at", "-id")
    )
    records = list(
        repository.filtered_measurements(filters).order_by(*ordering)[
            filters.offset : filters.offset + filters.limit + 1
        ]
    )
    return MeasurementPage(
        items=[serialize(record) for record in records[: filters.limit]],
        limit=filters.limit,
        offset=filters.offset,
        has_more=len(records) > filters.limit,
    )


def latest_measurement(filters: MeasurementFilters) -> MeasurementResponse:
    record = (
        repository.filtered_measurements(filters)
        .order_by("-observed_at", "-id")
        .first()
    )
    if record is None:
        raise MeasurementNotFound
    return serialize(record)


def save_measurement(
    payload: MeasurementInput, measurement_id: str | None = None
) -> MeasurementResponse:
    validate_measurement(payload)
    values = msgspec.structs.asdict(payload)
    values["risk_score"] = calculate_risk(payload.metrics)
    observed_at = payload.observed_at.astimezone(UTC)
    values["observed_at"] = observed_at.replace(
        microsecond=observed_at.microsecond // 1000 * 1000
    )
    record = repository.persist_measurement(values, measurement_id)
    action = "created" if measurement_id is None else "updated"
    logger.info("Measurement %s id=%s station=%r", action, record.pk, record.station_id)
    return serialize(record)


def delete_measurement(measurement_id: str) -> None:
    repository.remove_measurement(measurement_id)
    logger.info("Measurement deleted id=%s", measurement_id)


def retrieve_measurement(measurement_id: str) -> MeasurementResponse:
    return serialize(repository.get_measurement(measurement_id))


def list_locations() -> LocationList:
    items = []
    for item in repository.location_summaries():
        latitude, longitude = (
            float(item["_id"]["latitude"]),
            float(item["_id"]["longitude"]),
        )
        location_id = f"{latitude},{longitude}"
        items.append(
            LocationResponse(
                id=location_id,
                name=item.get("name") or location_id,
                latitude=latitude,
                longitude=longitude,
                measurement_count=item["measurement_count"],
                last_observed_at=item["last_observed_at"].replace(tzinfo=UTC),
            )
        )
    return LocationList(
        items=sorted(items, key=lambda item: (item.name.casefold(), item.id))
    )
