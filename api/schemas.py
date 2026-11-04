from datetime import datetime
from typing import Annotated, Literal

import msgspec

Text = Annotated[str, msgspec.Meta(min_length=1, max_length=100, pattern=r".*\S.*")]
Timestamp = Annotated[datetime, msgspec.Meta(tz=True)]
Score = Annotated[float, msgspec.Meta(ge=0, le=100)]
Latitude = Annotated[float, msgspec.Meta(ge=-90, le=90)]
Longitude = Annotated[float, msgspec.Meta(ge=-180, le=180)]
MetricName = Literal[
    "alder_pollen",
    "birch_pollen",
    "grass_pollen",
    "mugwort_pollen",
    "olive_pollen",
    "ragweed_pollen",
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "european_aqi",
    "us_aqi",
    "temperature_2m",
    "relative_humidity_2m",
]
RiskLevel = Literal["low", "moderate", "high", "very_high"]


class HealthResponse(msgspec.Struct, frozen=True):
    status: Literal["ok"] = "ok"


class MeasurementInput(msgspec.Struct, forbid_unknown_fields=True, kw_only=True):
    """Нормализованные данные эмулятора, время обязательно с UTC offset"""

    station_id: Text
    observed_at: Timestamp
    latitude: Latitude
    longitude: Longitude
    metrics: Annotated[
        dict[MetricName, float | None], msgspec.Meta(min_length=1, max_length=16)
    ]
    location_name: Annotated[str, msgspec.Meta(max_length=200)] = ""
    source: Literal["open-meteo"] = "open-meteo"


class MeasurementResponse(MeasurementInput, kw_only=True):
    id: str
    location_id: str
    risk_score: Score | None
    risk_level: RiskLevel | None
    created_at: Timestamp
    updated_at: Timestamp


class MeasurementFilters(msgspec.Struct, forbid_unknown_fields=True, kw_only=True):
    location_id: Text | None = None
    station_id: Text | None = None
    source: Literal["open-meteo"] | None = None
    time_from: Timestamp | None = None
    time_to: Timestamp | None = None
    risk_min: Score | None = None
    risk_max: Score | None = None
    risk_level: RiskLevel | None = None
    latitude_min: Latitude | None = None
    latitude_max: Latitude | None = None
    longitude_min: Longitude | None = None
    longitude_max: Longitude | None = None
    order: Literal["asc", "desc"] = "desc"
    limit: Annotated[int, msgspec.Meta(ge=1, le=500)] = 100
    offset: Annotated[int, msgspec.Meta(ge=0, le=100000)] = 0


class MeasurementPage(msgspec.Struct, kw_only=True):
    items: list[MeasurementResponse]
    limit: int
    offset: int
    has_more: bool


class MeasurementPath(msgspec.Struct, forbid_unknown_fields=True):
    measurement_id: Annotated[str, msgspec.Meta(pattern="^[0-9a-fA-F]{24}$")]


class UserResponse(msgspec.Struct):
    id: str
    username: str
    is_staff: bool


class CSRFResponse(msgspec.Struct):
    csrf_token: str


class LocationResponse(msgspec.Struct, kw_only=True):
    id: str
    name: str
    latitude: Latitude
    longitude: Longitude
    measurement_count: int
    last_observed_at: Timestamp


class LocationList(msgspec.Struct):
    items: list[LocationResponse]
