from fastapi import FastAPI
from common.responses import register_common_handlers
from common.logger import configure_logging
from gateway.config import settings
from gateway.api.v1.auth import router as auth_router

def create_app() -> FastAPI:
    configure_logging(settings.LOG_LEVEL)
    app = FastAPI(title=settings.PROJECT_NAME)
    register_common_handlers(app)
    
    app.include_router(auth_router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "gateway"}

    return app

app = create_app()
