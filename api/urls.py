from dmr.routing import Router, path

from api.controllers import (
    CSRFController,
    CurrentUserController,
    HealthController,
    LatestMeasurementController,
    LocationsController,
    LoginController,
    LogoutController,
    MeasurementCollectionController,
    MeasurementDetailController,
)

router = Router(
    "api/v1/",
    [
        path("health/", HealthController.as_view(), name="health"),
        path("locations/", LocationsController.as_view(), name="locations"),
        path(
            "measurements/",
            MeasurementCollectionController.as_view(),
            name="measurements",
        ),
        path(
            "measurements/latest/",
            LatestMeasurementController.as_view(),
            name="measurement-latest",
        ),
        path(
            "measurements/<str:measurement_id>/",
            MeasurementDetailController.as_view(),
            name="measurement-detail",
        ),
        path("auth/csrf/", CSRFController.as_view(), name="csrf"),
        path("auth/login/", LoginController.as_view(), name="login"),
        path("auth/logout/", LogoutController.as_view(), name="logout"),
        path("auth/me/", CurrentUserController.as_view(), name="me"),
    ],
)
