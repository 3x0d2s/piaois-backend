from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, SwaggerView
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import build_404_handler, build_500_handler, path
from dmr.security.csrf import build_csrf_handler

from api.urls import router

schema = build_schema(router)

urlpatterns = [
    router.to_urlpatterns(namespace="api"),
    path("api/openapi.json", OpenAPIJsonView.as_view(schema), name="openapi"),
    path("api/docs/", SwaggerView.as_view(schema), name="swagger"),
]

handler404 = build_404_handler("api/", serializer=MsgspecSerializer)
handler500 = build_500_handler("api/", serializer=MsgspecSerializer)
csrf_failure = build_csrf_handler("api/", serializer=MsgspecSerializer)
