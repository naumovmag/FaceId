from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Игнорируем дополнительные поля из .env
    )

    # Application settings
    app_host: str = Field("127.0.0.1", env="APP_HOST")
    app_port: int = Field(8000, env="APP_PORT")
    debug: bool = Field(True, env="DEBUG")
    secret_key: str = Field("default_secret_key", env="SECRET_KEY")

    # Database settings
    database_url: str = Field("sqlite:///./face_recognition.db", env="DATABASE_URL")

    # Face recognition settings
    face_recognition_threshold: float = Field(0.6, env="FACE_RECOGNITION_THRESHOLD")
    max_upload_size: int = Field(10485760, env="MAX_UPLOAD_SIZE")  # 10MB
    allowed_extensions: str = Field("jpg,jpeg,png", env="ALLOWED_EXTENSIONS")

    # Paths
    upload_path: str = Field("./uploads", env="UPLOAD_PATH")
    models_cache_path: str = Field("./models_cache", env="MODELS_CACHE_PATH")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    @field_validator('allowed_extensions')
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(',')]
        return v

    def get_allowed_extensions_list(self) -> List[str]:
        """Получить список разрешенных расширений"""
        if isinstance(self.allowed_extensions, str):
            return [ext.strip().lower() for ext in self.allowed_extensions.split(',')]
        return self.allowed_extensions


# Глобальный экземпляр настроек
settings = Settings()