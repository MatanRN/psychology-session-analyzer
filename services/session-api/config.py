"""Application configuration loaded from environment variables."""

import os

from pydantic import BaseModel, computed_field


class DatabaseConfig(BaseModel, frozen=True):
    """Immutable database connection configuration."""

    host: str
    port: str
    user: str
    password: str
    database: str

    @computed_field
    @property
    def url(self) -> str:
        """Returns the full PostgreSQL connection URL."""
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class AppConfig(BaseModel, frozen=True):
    """Root application configuration."""

    database: DatabaseConfig


def load_config() -> AppConfig:
    """Loads configuration from environment variables."""
    return AppConfig(
        database=DatabaseConfig(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_USER", ""),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            database=os.getenv("POSTGRES_DB", "psychology_analyzer"),
        )
    )
