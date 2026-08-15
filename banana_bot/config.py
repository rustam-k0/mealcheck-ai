from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ModelSpec:
    name: str
    capabilities: frozenset[str] = frozenset({"text", "image"})

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


def _catalog(raw: str) -> tuple[ModelSpec, ...]:
    """Parse `model` or `model|text+image` entries separated by commas.

    Plain model names default to text+image because most gateways do not expose a
    model-capability endpoint. Operators should annotate text-only models.
    """
    result: list[ModelSpec] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        name, separator, capability_text = entry.partition("|")
        capabilities = frozenset(x.strip().lower() for x in capability_text.split("+") if x.strip()) if separator else frozenset({"text", "image"})
        if not name.strip() or not capabilities or not capabilities <= {"text", "image", "audio"}:
            raise ConfigError(f"Invalid AI_MODEL_CATALOG entry: {entry!r}")
        result.append(ModelSpec(name.strip(), capabilities))
    if not result:
        raise ConfigError("AI_MODEL_CATALOG must contain at least one model")
    if len({x.name for x in result}) != len(result):
        raise ConfigError("AI_MODEL_CATALOG contains duplicate model names")
    return tuple(result)


def _ids(raw: str) -> frozenset[int]:
    return frozenset(int(value.strip()) for value in raw.split(",") if value.strip().isdigit())


@dataclass(frozen=True)
class AppConfig:
    telegram_bot_token: str | None
    ai_api_key: str | None
    ai_base_url: str
    ai_provider: str
    ai_vision_model: str
    ai_text_model: str
    ai_transcription_model: str | None
    transcription_api_key: str | None
    transcription_base_url: str | None
    model_catalog: tuple[ModelSpec, ...]
    allowed_users_env: str
    webhook_url: str | None
    port: int
    redis_url: str | None
    diary_db_path: str
    admin_users: frozenset[int]
    allowed_users: frozenset[int]
    request_timeout_seconds: float
    connect_timeout_seconds: float
    http_retries: int
    rate_limit_per_minute: int
    max_output_tokens: int
    memory_messages: int
    log_level: str

    @property
    def allowed_model_names(self) -> frozenset[str]:
        return frozenset(x.name for x in self.model_catalog)

    def model(self, name: str) -> ModelSpec | None:
        return next((x for x in self.model_catalog if x.name == name), None)

    def validate_model(self, name: str, capability: str = "text") -> ModelSpec:
        model = self.model(name)
        if model is None:
            raise ConfigError("The selected model is not in AI_MODEL_CATALOG")
        if not model.supports(capability):
            raise ConfigError(f"The selected model does not support {capability} input")
        return model

    def validate(self) -> None:
        if not self.telegram_bot_token:
            raise ConfigError("TELEGRAM_BOT_TOKEN is required")
        if not self.ai_api_key:
            raise ConfigError("AI_API_KEY is required")
        if not self.ai_base_url.startswith(("http://", "https://")):
            raise ConfigError("AI_BASE_URL must be an http(s) URL")
        self.validate_model(self.ai_text_model, "text")
        self.validate_model(self.ai_vision_model, "image")
        if self.ai_transcription_model and not (self.transcription_api_key or self.ai_api_key):
            raise ConfigError("Audio transcription has no API key")
        if self.memory_messages != 8:
            raise ConfigError("MEMORY_MESSAGES must be 8")
        if self.http_retries < 0 or self.rate_limit_per_minute < 1:
            raise ConfigError("Invalid retry or rate-limit setting")


def load_config(env: Mapping[str, str] | None = None, *, validate: bool = False) -> AppConfig:
    values = os.environ if env is None else env
    allowed_raw = values.get("ALLOWED_USERS", "")
    vision = values.get("AI_VISION_MODEL", "mimo-v2.5")
    text = values.get("AI_TEXT_MODEL", vision)
    catalog = _catalog(values.get("AI_MODEL_CATALOG", f"{vision}|text+image" + (f",{text}|text" if text != vision else "")))
    config = AppConfig(
        telegram_bot_token=values.get("TELEGRAM_BOT_TOKEN"), ai_api_key=values.get("AI_API_KEY"),
        ai_base_url=values.get("AI_BASE_URL", "https://opencode.ai/zen/go/v1").rstrip("/"),
        ai_provider=values.get("AI_PROVIDER", "opencode-go"), ai_vision_model=vision, ai_text_model=text,
        ai_transcription_model=values.get("AI_TRANSCRIPTION_MODEL") or None,
        transcription_api_key=values.get("TRANSCRIPTION_API_KEY") or None,
        transcription_base_url=(values.get("TRANSCRIPTION_BASE_URL") or values.get("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
        model_catalog=catalog, allowed_users_env=allowed_raw, webhook_url=values.get("WEBHOOK_URL"),
        port=int(values.get("PORT", "8080")), redis_url=values.get("REDIS_URL"),
        diary_db_path=values.get("DIARY_DB_PATH", "banana_mate_diary.sqlite3"),
        admin_users=_ids(values.get("ADMIN_USERS", allowed_raw)), allowed_users=_ids(allowed_raw),
        request_timeout_seconds=float(values.get("REQUEST_TIMEOUT_SECONDS", "180")),
        connect_timeout_seconds=float(values.get("CONNECT_TIMEOUT_SECONDS", "10")),
        http_retries=int(values.get("HTTP_RETRIES", "2")), rate_limit_per_minute=int(values.get("RATE_LIMIT_PER_MINUTE", "20")),
        max_output_tokens=int(values.get("MAX_OUTPUT_TOKENS", "1800")), memory_messages=int(values.get("MEMORY_MESSAGES", "8")),
        log_level=values.get("LOG_LEVEL", "INFO").upper(),
    )
    if validate:
        config.validate()
    return config
