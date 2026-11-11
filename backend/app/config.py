from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # O caminho precisa ser absoluto: o atalho, o terminal e o Docker podem
    # iniciar o Uvicorn em diretórios diferentes.
    database_url: str = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'studyflow.db').as_posix()}"
    jwt_secret: str = "change-this-in-development"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore", case_sensitive=False)

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.database_url.startswith("sqlite:///"):
        raise ValueError("Conexões SQL externas devem usar a API de queries do projeto, não uma conexão direta.")
    if settings.environment.lower() == "production" and (
        settings.jwt_secret == "change-this-in-development" or len(settings.jwt_secret) < 32
    ):
        raise ValueError("Configure um JWT_SECRET com pelo menos 32 caracteres antes de iniciar em produção.")
    if settings.database_url.startswith("sqlite:///./"):
        relative_path = settings.database_url.removeprefix("sqlite:///./")
        database_path = (Path(__file__).resolve().parents[1] / relative_path).resolve()
        settings.database_url = f"sqlite:///{database_path.as_posix()}"
    return settings
