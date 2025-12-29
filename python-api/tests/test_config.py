"""
Tests for configuration module.

Tests for:
- Environment variable loading
- Configuration validation with Pydantic
- Default values
"""



def test_config_loads_environment_variables(mock_env):
    """
    Test that configuration loads from environment variables.
    """
    from config import Settings

    settings = Settings()

    assert settings.ENVIRONMENT == "test"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.API_VERSION == "v1"


def test_config_has_default_values(monkeypatch):
    """
    Test that configuration has sensible default values.
    """
    # Clear relevant env vars to test defaults
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    from config import Settings

    settings = Settings()

    # Should have defaults
    assert hasattr(settings, "ENVIRONMENT")
    assert hasattr(settings, "LOG_LEVEL")
    assert hasattr(settings, "API_VERSION")


def test_config_allowed_origins_is_list(mock_env):
    """
    Test that ALLOWED_ORIGINS is parsed as a list.
    """
    from config import Settings

    settings = Settings()

    assert isinstance(settings.ALLOWED_ORIGINS, list)
    assert len(settings.ALLOWED_ORIGINS) > 0
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS


def test_config_validation_enforces_types(monkeypatch):
    """
    Test that Pydantic validates configuration types.
    """
    from config import Settings

    # Should not raise validation errors with valid data
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()
    assert settings.ENVIRONMENT == "production"
    assert settings.LOG_LEVEL == "DEBUG"
