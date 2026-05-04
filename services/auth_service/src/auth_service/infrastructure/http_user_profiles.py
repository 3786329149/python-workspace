from uuid import UUID

import httpx

from common.errors import AppError
from common.responses import REQUEST_ID_HEADER


class HttpUserProfileClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str, internal_token: str) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.internal_token = internal_token

    async def create_user(
        self,
        *,
        email: str,
        username: str,
        request_id: str | None = None,
    ) -> dict[str, object]:
        response = await self.client.post(
            f"{self.base_url}/internal/v1/users/registration-profile",
            json={"email": email, "username": username},
            headers=self._headers(request_id),
        )
        return self._json_or_error(response, "failed to create user profile")

    async def delete_user(
        self,
        user_id: UUID,
        *,
        request_id: str | None = None,
    ) -> None:
        response = await self.client.delete(
            f"{self.base_url}/internal/v1/users/{user_id}",
            headers=self._headers(request_id),
        )
        if response.status_code in (204, 404):
            return
        self._raise_downstream_error(response, "failed to delete user profile")

    async def activate_user(
        self,
        user_id: UUID,
        *,
        request_id: str | None = None,
    ) -> dict[str, object]:
        response = await self.client.post(
            f"{self.base_url}/internal/v1/users/{user_id}/activate",
            headers=self._headers(request_id),
        )
        return self._json_or_error(response, "failed to activate user profile")

    def _headers(self, request_id: str | None) -> dict[str, str]:
        headers = {"X-Internal-Token": self.internal_token}
        if request_id:
            headers[REQUEST_ID_HEADER] = request_id
        return headers

    def _json_or_error(
        self,
        response: httpx.Response,
        default_message: str,
    ) -> dict[str, object]:
        if response.is_success:
            data = response.json()
            if not isinstance(data, dict):
                raise AppError(
                    "user service returned invalid response",
                    code="USER_SERVICE_INVALID_RESPONSE",
                    status_code=502,
                )
            return data

        self._raise_downstream_error(response, default_message)

    def _raise_downstream_error(
        self,
        response: httpx.Response,
        default_message: str,
    ) -> None:
        try:
            data = response.json()
        except ValueError:
            data = {}

        message = data.get("message") if isinstance(data, dict) else None
        code = data.get("code") if isinstance(data, dict) else None
        raise AppError(
            str(message or default_message),
            code=str(code or "USER_SERVICE_ERROR"),
            status_code=response.status_code,
        )
