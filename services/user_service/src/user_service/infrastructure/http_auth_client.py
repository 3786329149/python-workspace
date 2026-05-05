import httpx
from uuid import UUID
from common.errors import AppError
from common.responses import REQUEST_ID_HEADER

class HttpAuthClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str, internal_token: str) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.internal_token = internal_token

    async def bind_password(
        self,
        *,
        user_id: UUID,
        username: str,
        password: str,
        request_id: str | None = None,
    ) -> None:
        headers = {"X-Internal-Token": self.internal_token}
        if request_id:
            headers[REQUEST_ID_HEADER] = request_id
            
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/bind-password",
            json={
                "user_id": str(user_id),
                "username": username,
                "password": password,
            },
            headers=headers,
        )
        if not response.is_success:
            try:
                data = response.json()
                message = data.get("message", "failed to bind password in auth-service")
            except Exception:
                message = "failed to bind password in auth-service"
            raise AppError(message, status_code=response.status_code)
