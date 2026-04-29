import uvicorn

from auth_service.config import settings


def main() -> None:
    uvicorn.run(
        "auth_service.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=bool(settings.SERVICE_RELOAD),
    )


if __name__ == "__main__":
    main()
