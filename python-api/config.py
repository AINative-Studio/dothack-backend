"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables with validation
and type checking.
"""


from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic for validation and type coercion.
    Reads from .env file if present.
    """

    # Application settings
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    API_VERSION: str = Field(default="v1", description="API version prefix")

    # CORS settings
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins",
    )

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # ZeroDB Settings
    ZERODB_API_KEY: str = Field(default="", description="ZeroDB API key")
    ZERODB_PROJECT_ID: str = Field(default="", description="ZeroDB project ID")
    ZERODB_BASE_URL: str = Field(
        default="https://api.ainative.studio", description="ZeroDB API base URL"
    )
    ZERODB_TIMEOUT: float = Field(default=30.0, description="ZeroDB request timeout")

    # External service URLs (to be configured later)
    HUBSPOT_API_URL: str = Field(
        default="https://api.hubapi.com", description="HubSpot API base URL"
    )
    HUBSPOT_API_KEY: str = Field(default="", description="HubSpot API key")

    CLEARBIT_API_URL: str = Field(
        default="https://person.clearbit.com", description="Clearbit API base URL"
    )
    CLEARBIT_API_KEY: str = Field(default="", description="Clearbit API key")

    APOLLO_API_URL: str = Field(default="https://api.apollo.io", description="Apollo API base URL")
    APOLLO_API_KEY: str = Field(default="", description="Apollo API key")

    RESEND_API_URL: str = Field(default="https://api.resend.com", description="Resend API base URL")
    RESEND_API_KEY: str = Field(default="", description="Resend API key")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields in .env
    )

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v: str) -> list[str]:
        """
        Parse comma-separated CORS origins into a list.

        Args:
            v: Comma-separated string of origins

        Returns:
            List of origin strings
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """
        Validate log level is one of the standard Python logging levels.

        Args:
            v: Log level string

        Returns:
            Uppercase log level string

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper


# Singleton instance
settings = Settings()
