from dmr.routing import Router, path

from api.controllers import HealthController

router = Router(
    "api/v1/",
    [path("health/", HealthController.as_view(), name="health")],
)
