from api.schemas import MetricName, RiskLevel

POLLEN_METRICS: tuple[MetricName, ...] = (
    "alder_pollen",
    "birch_pollen",
    "grass_pollen",
    "mugwort_pollen",
    "olive_pollen",
    "ragweed_pollen",
)
POLLEN_REFERENCE = 100.0


def calculate_risk(metrics: dict[MetricName, float | None]) -> float | None:
    """Учебная серверная формула: пыльца относительно 100 grains/m³ и AQI"""
    candidates = [
        100 * value / POLLEN_REFERENCE
        for name in POLLEN_METRICS
        if (value := metrics.get(name)) is not None
    ]
    aqi = metrics.get("european_aqi")
    if aqi is not None:
        candidates.append(aqi)
    if not candidates:
        return None
    return round(min(100.0, max(candidates)), 2)


def risk_level(score: float | None) -> RiskLevel | None:
    if score is None:
        return None
    if score < 25:
        return "low"
    if score < 50:
        return "moderate"
    if score < 75:
        return "high"
    return "very_high"
