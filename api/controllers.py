import logging
from http import HTTPStatus
from typing import cast

from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.views.decorators.debug import sensitive_variables
from dmr import Controller, CookieSpec, Path, Query, ResponseSpec, modify
from dmr.errors import ErrorModel
from dmr.plugins.msgspec import BodyMsgspec, MsgspecSerializer
from dmr.security import NO_STORE_HEADERS, AuthenticatedHttpRequest
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.security.django_session.views import (
    DjangoSessionPayload,
    DjangoSessionSyncController,
)
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr

from api import services
from api.auth import IngestKeyAuth, StaffSessionAuth
from api.schemas import (
    CSRFResponse,
    HealthResponse,
    LocationList,
    MeasurementFilters,
    MeasurementInput,
    MeasurementPage,
    MeasurementPath,
    MeasurementResponse,
    UserResponse,
)

logger = logging.getLogger("api")
SERVICE_RESPONSES = (
    ResponseSpec(ErrorModel, status_code=HTTPStatus.SERVICE_UNAVAILABLE),
    ResponseSpec(ErrorModel, status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE),
)


class APIController(Controller[MsgspecSerializer]):
    responses = SERVICE_RESPONSES


class HealthController(APIController):
    """Проверка доступности процесса API"""

    def get(self) -> HealthResponse:
        """Состояние процесса без проверки MongoDB"""
        return HealthResponse()


class MeasurementCollectionController(APIController):
    """Публичный просмотр истории и защищённый приём данных"""

    responses = (
        *SERVICE_RESPONSES,
        ResponseSpec(ErrorModel, status_code=HTTPStatus.CONFLICT),
    )

    def get(self, parsed_query: Query[MeasurementFilters]) -> MeasurementPage:
        """История измерений с фильтрами и ограниченной пагинацией"""
        return services.list_measurements(parsed_query)

    @modify(
        auth=[IngestKeyAuth()],
        throttling=[SyncThrottle(120, Rate.minute, cache_key=RemoteAddr())],
    )
    def post(self, parsed_body: BodyMsgspec[MeasurementInput]) -> MeasurementResponse:
        """Сохраняет измерение; повтор станции, координат и времени возвращает 409"""
        return services.save_measurement(parsed_body)


class LatestMeasurementController(APIController):
    """Последнее измерение по времени наблюдения"""

    responses = (
        *SERVICE_RESPONSES,
        ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
    )

    def get(self, parsed_query: Query[MeasurementFilters]) -> MeasurementResponse:
        """Последнее измерение среди данных, соответствующих фильтрам"""
        return services.latest_measurement(parsed_query)


class MeasurementDetailController(APIController):
    """Публичное чтение и административное изменение одного измерения"""

    responses = (
        *SERVICE_RESPONSES,
        ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
        ResponseSpec(ErrorModel, status_code=HTTPStatus.CONFLICT),
        ResponseSpec(ErrorModel, status_code=HTTPStatus.FORBIDDEN),
    )

    def get(self, parsed_path: Path[MeasurementPath]) -> MeasurementResponse:
        """Возвращает измерение по MongoDB ObjectId"""
        return services.retrieve_measurement(parsed_path.measurement_id)

    @modify(auth=[StaffSessionAuth()])
    def put(
        self,
        parsed_path: Path[MeasurementPath],
        parsed_body: BodyMsgspec[MeasurementInput],
    ) -> MeasurementResponse:
        """Полностью заменяет данные измерения, сохраняя его id"""
        result = services.save_measurement(parsed_body, parsed_path.measurement_id)
        logger.info("Measurement edit actor=%s id=%s", self.request.user.pk, result.id)
        return result

    @modify(auth=[StaffSessionAuth()], status_code=HTTPStatus.NO_CONTENT)
    def delete(self, parsed_path: Path[MeasurementPath]) -> None:
        """Удаляет измерение; доступно только сотрудникам"""
        services.delete_measurement(parsed_path.measurement_id)
        logger.info(
            "Measurement delete actor=%s id=%s",
            self.request.user.pk,
            parsed_path.measurement_id,
        )


class CSRFController(APIController):
    """Начало сессионной аутентификации браузерного клиента"""

    @modify(
        headers=NO_STORE_HEADERS,
        cookies={"csrftoken": CookieSpec(skip_validation=True)},
    )
    def get(self) -> CSRFResponse:
        """Выдаёт CSRF cookie и токен для X-CSRFToken"""
        return CSRFResponse(csrf_token=get_token(self.request))


class LoginController(
    DjangoSessionSyncController[MsgspecSerializer, DjangoSessionPayload, UserResponse]
):
    """Вход существующего пользователя по username и password"""

    auth = None
    csrf_exempt = False
    throttling = (SyncThrottle(5, Rate.minute, cache_key=RemoteAddr()),)
    responses = SERVICE_RESPONSES

    @sensitive_variables()
    @modify(
        status_code=HTTPStatus.OK,
        headers=NO_STORE_HEADERS,
        cookies={
            "sessionid": CookieSpec(skip_validation=True),
            "csrftoken": CookieSpec(skip_validation=True),
        },
        extra_responses=[
            *SERVICE_RESPONSES,
            ResponseSpec(ErrorModel, status_code=HTTPStatus.UNAUTHORIZED),
        ],
    )
    def post(self, parsed_body: BodyMsgspec[DjangoSessionPayload]) -> UserResponse:
        """Проверяет пароль и создаёт сессию; публичной регистрации нет"""
        return self.login(parsed_body)

    def convert_auth_payload(
        self, payload: DjangoSessionPayload
    ) -> DjangoSessionPayload:
        return payload

    def make_api_response(self) -> UserResponse:
        user = cast(AuthenticatedHttpRequest[User], self.request).user
        logger.info("User login id=%s", user.pk)
        return UserResponse(
            id=str(user.pk), username=user.get_username(), is_staff=user.is_staff
        )


class CurrentUserController(APIController):
    """Информация об активной сессии"""

    auth = (DjangoSessionSyncAuth(),)

    @modify(headers=NO_STORE_HEADERS)
    def get(self) -> UserResponse:
        """Возвращает пользователя текущей сессии"""
        user = cast(AuthenticatedHttpRequest[User], self.request).user
        return UserResponse(
            id=str(user.pk), username=user.get_username(), is_staff=user.is_staff
        )


class LogoutController(APIController):
    """Завершение текущей серверной сессии"""

    auth = (DjangoSessionSyncAuth(),)
    csrf_exempt = False

    @modify(status_code=HTTPStatus.NO_CONTENT, headers=NO_STORE_HEADERS)
    def post(self) -> None:
        """Удаляет текущую сессию и сбрасывает session cookie"""
        user_id = str(self.request.user.pk)
        logout(self.request)
        logger.info("User logout id=%s", user_id)


class LocationsController(APIController):
    """Локации, для которых в базе есть измерения"""

    def get(self) -> LocationList:
        """Уникальные координаты с названием и временем последнего наблюдения"""
        return services.list_locations()
