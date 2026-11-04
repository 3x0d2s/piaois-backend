from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer

from api.schemas import HealthResponse


class HealthController(Controller[MsgspecSerializer]):
    """Проверка доступности процесса API"""

    def get(self) -> HealthResponse:
        """Возвращает состояние процесса без проверки базы данных"""
        return HealthResponse()
