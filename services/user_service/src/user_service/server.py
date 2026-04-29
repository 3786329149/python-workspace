import uvicorn

from user_service.config import settings


def main() -> None:
    uvicorn.run(
        "user_service.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=bool(settings.SERVICE_RELOAD),
    )


if __name__ == "__main__":
    main()
