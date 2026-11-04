import secrets
from http import HTTPStatus
from typing import Self, cast

from django.conf import settings
from django.contrib.auth.models import User
from dmr import APIError, Controller
from dmr.endpoint import Endpoint
from dmr.errors import format_error
from dmr.metadata import EndpointMetadata
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security import SyncAuth
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.serializer import BaseSerializer


class IngestKeyAuth(SyncAuth):
    """Ключ эмулятора даёт право только добавлять измерения"""

    @property
    def www_authenticate_challenge(self) -> None:
        return None

    def __call__(
        self, endpoint: Endpoint, controller: Controller[BaseSerializer]
    ) -> Self | None:
        expected = settings.INGEST_API_KEY
        if not 32 <= len(expected) <= 256:
            raise APIError(
                format_error("Measurement ingestion is not configured"),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        supplied = controller.request.headers.get("X-Ingest-Key", "")
        if len(supplied) > 256 or not secrets.compare_digest(
            supplied.encode(), expected.encode()
        ):
            return None
        return self

    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> dict[str, SecurityScheme | Reference]:
        return {
            "ingest_key": SecurityScheme(
                type="apiKey",
                name="X-Ingest-Key",
                security_scheme_in="header",
                description="Emulator key; grants create-only access",
            )
        }

    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> list[SecurityRequirement]:
        return [{"ingest_key": []}]


class StaffSessionAuth(DjangoSessionSyncAuth):
    """Изменять историю может только активный сотрудник"""

    def authenticate(
        self, endpoint: Endpoint, controller: Controller[BaseSerializer]
    ) -> Self | None:
        result = super().authenticate(endpoint, controller)
        if result is not None and not cast(User, controller.request.user).is_staff:
            raise APIError(
                format_error("Staff access required"), status_code=HTTPStatus.FORBIDDEN
            )
        return result
