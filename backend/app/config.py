"""Application configuration loaded from environment variables."""

import json
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://verdict:verdict_dev@localhost:5432/verdict",
        alias="DATABASE_URL",
    )

    # Security & Auth
    jwt_secret: str = Field(default="dev_secret_change_me_in_production", alias="JWT_SECRET")
    jwt_expires_minutes: int = Field(default=60, alias="JWT_EXPIRES_MINUTES")
    jwt_algorithm: str = "HS256"

    # LLM Providers
    gemini_api_keys: str = Field(default="", alias="GEMINI_API_KEYS")
    groq_api_keys: str = Field(default="", alias="GROQ_API_KEYS")
    openrouter_api_keys: str = Field(default="", alias="OPENROUTER_API_KEYS")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        alias="GEMINI_BASE_URL",
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        alias="GROQ_BASE_URL",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # Chains
    chain_strong: str = Field(default="", alias="CHAIN_STRONG")
    chain_mid: str = Field(default="", alias="CHAIN_MID")
    chain_small: str = Field(default="", alias="CHAIN_SMALL")

    # Embeddings & Reranking
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL")

    # Server & Logging
    cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            val = value.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in val.split(",") if origin.strip()]
        return value


settings = Settings()

