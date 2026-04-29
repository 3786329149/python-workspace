# common

Shared infrastructure package for workspace services.

Stable imports:

```python
from common.config import (
    BaseServiceConfig,
    DatabaseConfigMixin,
    RedisConfigMixin,
    find_service_env_file,
)
from common.database import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    create_async_engine_factory,
    create_session_factory,
)
from common.errors import AppError
from common.logger import configure_logging, get_logger
from common.redis import create_redis_client
from common.responses import register_common_handlers
```

Service-specific DB and Redis values should live in each service package,
not in `common`.
