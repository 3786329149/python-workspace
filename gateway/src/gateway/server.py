import uvicorn
from gateway.config import settings

def main() -> None:
    uvicorn.run(
        "gateway.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=bool(settings.SERVICE_RELOAD),
    )

if __name__ == "__main__":
    main()
