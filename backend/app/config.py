"""Application configuration loaded from environment variables."""

import json
from typing import List, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://verdict:verdict_dev@localhost:5434/verdict",
        alias="DATABASE_URL",
    )

    # Security & Auth
    jwt_secret: str = Field(default="dev_secret_change_me_in_production", alias="JWT_SECRET")
    jwt_expires_minutes: int = Field(default=60, alias="JWT_EXPIRES_MINUTES")
    jwt_algorithm: str = "HS256"
    admin_emails: str = Field(default="admin@verdict.internal", alias="ADMIN_EMAILS")

    # LLM Providers (comma-separated or individual slots)
    gemini_api_keys: str = Field(default="", alias="GEMINI_API_KEYS")
    gemini_api_key_1: str = Field(default="", alias="GEMINI_API_KEY_1")
    gemini_api_key_2: str = Field(default="", alias="GEMINI_API_KEY_2")
    gemini_api_key_3: str = Field(default="", alias="GEMINI_API_KEY_3")

    groq_api_keys: str = Field(default="", alias="GROQ_API_KEYS")
    groq_api_key_1: str = Field(default="", alias="GROQ_API_KEY_1")
    groq_api_key_2: str = Field(default="", alias="GROQ_API_KEY_2")
    groq_api_key_3: str = Field(default="", alias="GROQ_API_KEY_3")

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

    # Simulation & Quota Guards
    dev_mode: bool = Field(default=True, alias="DEV_MODE")
    max_trial_tokens: int = Field(default=300000, alias="MAX_TRIAL_TOKENS")
    casegen_daily_user_cap: int = Field(default=10, alias="CASEGEN_DAILY_USER_CAP")
    default_juror_count: int = Field(default=3, alias="DEFAULT_JUROR_COUNT")
    default_deliberation_rounds: int = Field(default=1, alias="DEFAULT_DELIBERATION_ROUNDS")
    ack_timeout_seconds: float = Field(default=10.0, alias="ACK_TIMEOUT_SECONDS")

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

    @model_validator(mode="after")
    def consolidate_keys(self) -> "Settings":
        # Consolidate Gemini keys
        g_keys = [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]
        for slot in (self.gemini_api_key_1, self.gemini_api_key_2, self.gemini_api_key_3):
            if slot and slot.strip() and slot.strip() not in g_keys:
                g_keys.append(slot.strip())
        self.gemini_api_keys = ",".join(g_keys)

        # Consolidate Groq keys
        gr_keys = [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]
        for slot in (self.groq_api_key_1, self.groq_api_key_2, self.groq_api_key_3):
            if slot and slot.strip() and slot.strip() not in gr_keys:
                gr_keys.append(slot.strip())
        self.groq_api_keys = ",".join(gr_keys)

        return self

    @property
    def admin_emails_list(self) -> List[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]


settings = Settings()
