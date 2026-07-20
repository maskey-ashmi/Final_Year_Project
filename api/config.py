import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed; skip loading .env file
    pass


class BaseConfig:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    # Store uploads in the top-level uploads folder for persistent application use
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")

    # Optional DATABASE_URL (no SQLAlchemy enforcement)
    DATABASE_URL = os.environ.get("DATABASE_URL", "")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
