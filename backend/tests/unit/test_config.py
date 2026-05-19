
from backend.core.config import get_settings


def test_settings_loaded():
    settings = get_settings()
    assert settings.app_name == "EnergyInferencePlatform"
    assert settings.app_env in {"development", "staging", "production"}
    assert settings.database_pool_size > 0
    assert settings.jwt_algorithm == "HS256"


def test_settings_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_is_production_flag():
    settings = get_settings()
    if settings.app_env == "production":
        assert settings.is_production is True
    else:
        assert settings.is_production is False
