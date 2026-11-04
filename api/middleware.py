import logging
import time
import uuid
from collections.abc import Callable
from http import HTTPStatus

from django.contrib.sessions.middleware import SessionMiddleware
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from dmr.errors import format_error
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.response import build_response
from pymongo.errors import PyMongoError

logger = logging.getLogger("api.requests")


class RequestLogMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started = time.monotonic()
        request_id = uuid.uuid4().hex
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["X-Request-ID"] = request_id
            logger.info(
                "request_id=%s method=%s path=%r status=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.path,
                response.status_code,
                (time.monotonic() - started) * 1000,
            )
        return response


class SafeSessionMiddleware(SessionMiddleware):
    """Возвращает JSON при сбое сохранения сессии после выполнения endpoint"""

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        try:
            return super().process_response(request, response)
        except (DatabaseError, PyMongoError) as exc:
            logger.error("Session storage failed: %s", type(exc).__name__)
            result = build_response(
                MsgspecSerializer,
                raw_data=format_error("Session storage temporarily unavailable"),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
            result["Cache-Control"] = "no-store"
            return result
