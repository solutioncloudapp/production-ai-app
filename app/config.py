"""Centralized application configuration."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field("gpt-4o", description="Primary LLM model")
    openai_embedding_model: str = Field(
        "text-embedding-3-small", description="Embedding model"
    )

    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379", description="Redis URL")

    # Database Configuration
    database_url: str = Field(
        "postgresql://postgres:postgres@localhost:5432/ai_app",
        description="PostgreSQL URL",
    )

    # ChromaDB Configuration
    chroma_host: str = Field("localhost", description="ChromaDB host")
    chroma_port: int = Field(8001, description="ChromaDB port")

    # Application Configuration
    app_host: str = Field("0.0.0.0", description="App host")
    app_port: int = Field(8000, description="App port")
    log_level: str = Field("info", description="Log level")
    environment: str = Field("development", description="Environment")

    # Security Configuration
    max_input_length: int = Field(4000, description="Max input length")
    rate_limit_per_minute: int = Field(60, description="Rate limit per minute")
    allowed_origins: List[str] = Field(
        ["http://localhost:3000"], description="Allowed CORS origins"
    )

    # Cache Configuration
    cache_ttl_seconds: int = Field(3600, description="Cache TTL")
    cache_similarity_threshold: float = Field(
        0.95, description="Cache similarity threshold"
    )

    # Evaluation Configuration
    eval_model: str = Field("gpt-4o-mini", description="Evaluation model")
    eval_dataset_path: str = Field(
        "evaluation/golden_dataset.json", description="Eval dataset path"
    )

    # Observability Configuration
    otel_exporter_otlp_endpoint: str = Field(
        "http://localhost:4317", description="OTLP endpoint"
    )
    enable_cost_tracking: bool = Field(True, description="Enable cost tracking")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
