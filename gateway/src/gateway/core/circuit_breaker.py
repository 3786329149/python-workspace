import asyncio
import time
from dataclasses import dataclass
from enum import StrEnum


class CircuitOpen(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("circuit is open")


class CircuitStateName(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class CircuitState:
    state: CircuitStateName = CircuitStateName.CLOSED
    failure_count: int = 0
    opened_at: float = 0.0


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int,
        recovery_seconds: int,
        enabled: bool = True,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.enabled = enabled
        self._states: dict[str, CircuitState] = {}
        self._lock = asyncio.Lock()

    async def before_call(self, service: str) -> None:
        if not self.enabled:
            return

        now = time.monotonic()
        async with self._lock:
            state = self._states.setdefault(service, CircuitState())
            if state.state != CircuitStateName.OPEN:
                return

            elapsed = now - state.opened_at
            if elapsed >= self.recovery_seconds:
                state.state = CircuitStateName.HALF_OPEN
                return

            retry_after = max(1, int(self.recovery_seconds - elapsed))
            raise CircuitOpen(retry_after)

    async def record_success(self, service: str) -> None:
        if not self.enabled:
            return

        async with self._lock:
            self._states[service] = CircuitState()

    async def record_failure(self, service: str) -> None:
        if not self.enabled:
            return

        now = time.monotonic()
        async with self._lock:
            state = self._states.setdefault(service, CircuitState())
            state.failure_count += 1

            if (
                state.state == CircuitStateName.HALF_OPEN
                or state.failure_count >= self.failure_threshold
            ):
                state.state = CircuitStateName.OPEN
                state.opened_at = now
