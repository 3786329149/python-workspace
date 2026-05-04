from typing import Protocol

class LoginAttemptLimiter(Protocol):
    async def check_limits(self, username: str, ip_address: str) -> None:
        """
        Check if the username or IP is locked.
        Raises an exception (e.g. AuthInvalidCredentials) if locked.
        """
        ...

    async def record_failure(self, username: str, ip_address: str) -> None:
        """
        Record a login failure for the given username and IP.
        """
        ...

    async def clear_failures(self, username: str) -> None:
        """
        Clear login failures for the given username upon successful login.
        """
        ...
