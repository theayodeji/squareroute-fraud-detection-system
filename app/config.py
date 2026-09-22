from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Delivery Fraud Risk Engine"
    ENVIRONMENT: str = "development"
    
    # Defaults to SQLite in-memory for zero-friction local dev if not provided
    DATABASE_URL: str = "sqlite+aiosqlite:///./risk_engine.db"
    
    # If None, the system uses the AsyncMemoryBroker (for testing/local dev without Redis)
    REDIS_URL: str | None = None
    
    QUEUE_NAME: str = "risk-events"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
