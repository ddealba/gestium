"""Application configuration."""


class BaseConfig:
    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_config(config_name: str) -> type[BaseConfig]:
    """Return configuration class by name."""
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return config_map.get(config_name, DevelopmentConfig)
