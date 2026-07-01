from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    AMADEUS_CLIENT_ID: str = ""
    AMADEUS_CLIENT_SECRET: str = ""
    AMADEUS_ENV: str = "sandbox"
    OPEN_METEO_BASE_URL: str = "https://archive-api.open-meteo.com"
    OWM_API_KEY: str = ""
    GEONAMES_USERNAME: str = ""
    APP_ENV: str = "development"
    CACHE_TTL_FLIGHT_HOURS: int = 4
    CACHE_TTL_HOTEL_HOURS: int = 4
    CACHE_TTL_WEATHER_HOURS: int = 6
    MOCK_SEED: int = 42
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gemini-flash-latest"
    LLM_API_TYPE: str = "gemini"
    ALLOW_MOCK_FALLBACK: bool = True
    DUFFEL_ACCESS_TOKEN: str = ""
    DUFFEL_BASE_URL: str = "https://api.duffel.com"
    DUFFEL_TIMEOUT_SECONDS: int = 30
    DUFFEL_MAX_RETRIES: int = 3
    DUFFEL_ENABLED: bool = False
    FLIGHT_PROVIDER: str = "auto"
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

if not settings.DATABASE_URL:
    from pathlib import Path
    db_path = Path(__file__).parent.parent.parent.parent / "data" / "travel.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.DATABASE_URL = f"sqlite:///{db_path}"
