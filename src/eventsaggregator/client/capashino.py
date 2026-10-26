from dataclasses import dataclass
from uuid import UUID

import httpx
from pydantic import ValidationError

from eventsaggregator.client.schemas import (
    CapashinoResponse,
)
from eventsaggregator.core.exceptions import CapashinoError


class CapashinoTransientError(CapashinoError):
    """Сетевой сбой, timeout, 408, 429 или 5xx."""


class CapashinoPermanentError(CapashinoError):
    """Постоянная ошибка запроса или контракта."""


@dataclass(frozen=True)
class NotificationCreated:
    response: CapashinoResponse


@dataclass(frozen=True)
class NotificationAlreadyExists:
    pass


NotificationResult = NotificationCreated | NotificationAlreadyExists


class CapashinoProviderClient:
    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self.client = client
        self.api_key = api_key

    async def create_notifi(
        self, message: str, reference_id: UUID, idempotency_key: str
    ) -> NotificationResult:
        try:
            response = await self.client.post(
                "/api/notifications",
                headers={"X-API-Key": self.api_key},
                json={
                    "message": message,
                    "reference_id": str(reference_id),
                    "idempotency_key": idempotency_key,
                },
            )
        except httpx.TimeoutException as exc:
            raise CapashinoTransientError("Capashino request timed out") from exc
        except httpx.TransportError as exc:
            raise CapashinoTransientError("Capashino transport error") from exc

        if response.status_code == 409:
            return NotificationAlreadyExists()

        if response.status_code in {408, 429} or response.status_code >= 500:
            raise CapashinoTransientError(
                f"Temporary Capashino error: HTTP {response.status_code}"
            )

        if response.status_code != 201:
            raise CapashinoPermanentError(
                f"Capashino rejected request: HTTP {response.status_code}"
            )

        try:
            body = response.json()
            parsed = CapashinoResponse.model_validate(body)
        except (ValueError, ValidationError) as exc:
            raise CapashinoTransientError(
                "Invalid Capashino response after HTTP 201"
            ) from exc

        return NotificationCreated(parsed)
