from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "api-gateway"
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    
    SERVICE_HOST: str = "127.0.0.1"
    SERVICE_PORT: int = 8000
    SERVICE_RELOAD: bool = True

    # Internal Service URLs
    USER_SERVICE_URL: str = "http://127.0.0.1:5600"
    AUTH_SERVICE_URL: str = "http://127.0.0.1:5601"

settings = Settings()
