from typing import Literal

import msgspec


class HealthResponse(msgspec.Struct, frozen=True):
    """Состояние процесса API"""

    status: Literal["ok"] = "ok"
