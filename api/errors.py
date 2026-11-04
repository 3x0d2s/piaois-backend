import logging
from http import HTTPStatus

from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError, IntegrityError
from django.http import HttpResponse
from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.errors import ErrorType, global_error_handler
from dmr.serializer import BaseSerializer
from pymongo.errors import DuplicateKeyError, PyMongoError

logger = logging.getLogger("api")


class InvalidMeasurement(ValueError):
    pass


class MeasurementNotFound(LookupError):
    pass


def api_error_handler(
    endpoint: Endpoint, controller: Controller[BaseSerializer], exc: Exception
) -> HttpResponse:
    if isinstance(exc, RequestDataTooBig):
        status, message = (
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "Request body exceeds 64 KiB",
        )
    elif isinstance(exc, InvalidMeasurement):
        status, message = HTTPStatus.BAD_REQUEST, str(exc)
    elif isinstance(exc, MeasurementNotFound):
        status, message = HTTPStatus.NOT_FOUND, "Measurement not found"
    elif isinstance(exc, (IntegrityError, DuplicateKeyError)):
        status, message = (
            HTTPStatus.CONFLICT,
            "Measurement for this station, coordinates and timestamp already exists",
        )
    elif isinstance(exc, (DatabaseError, PyMongoError)):
        logger.error("Database operation failed: %s", type(exc).__name__)
        status, message = (
            HTTPStatus.SERVICE_UNAVAILABLE,
            "Database temporarily unavailable",
        )
    else:
        return global_error_handler(endpoint, controller, exc)
    return controller.to_error(
        controller.format_error(message, error_type=ErrorType.user_msg),
        status_code=status,
    )
