from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration management using pydantic-settings.

    Reads environment variables from `.env` and exposes parsed/validated settings.
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    
    PROJECT_NAME: str = "Scalable RAG API"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    @property
    def is_production(self) -> bool:
        """Helper indicating whether the environment is running in production.

        Returns:
            True if APP_ENV is 'production', False otherwise.
        """
        return self.APP_ENV.lower() == "production"

    @property
    def allowed_cors_origins(self) -> list[str]:
        """Splits and validates the allowed origins list from configuration settings.

        Returns:
            List of allowed CORS host origin strings.
        """
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.is_production and "*" in origins:
            raise ValueError("CORS_ORIGINS cannot include '*' when APP_ENV=production")
        return origins
    DATABASE_URL: str | None = None
    
    # Local Postgres configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "rag_db"
    
    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Assembles the SQLAlchemy async database connection URI.

        Returns:
            Connection string matching standard asyncpg schemas.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            
            # Clean up asyncpg incompatible parameters like sslmode and channel_binding
            if "?" in url:
                base_url, query_params = url.split("?", 1)
                # Keep standard ssl=require parameter for cloud databases
                url = f"{base_url}?ssl=require"
            return url
        password_part = f":{self.POSTGRES_PASSWORD}" if self.POSTGRES_PASSWORD else ""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}{password_part}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Qdrant configuration
    QDRANT_URL: str | None = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None
    
    # Redis configuration
    REDIS_URL: str | None = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    QUERY_CACHE_TTL_SECONDS: int = 3600

    # Groq configuration
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"


settings = Settings()
