from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

try:  # pragma: no cover - dependency optional in tests
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as _BaseSettings

    class BaseSettings(_BaseSettings):  # type: ignore[misc]
        class Config:
            arbitrary_types_allowed = True

    def SettingsConfigDict(**kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
        return kwargs


class Paths(BaseModel):
    root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    configs: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "configs")
    workflows: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "configs")
    transcripts: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "examples" / "transcripts"
    )


class LLMSettings(BaseModel):
    api_key: str | None = Field(default=None, description="Optional LLM provider API key.")
    base_url: str | None = Field(default=None, description="Optional OpenAI-compatible base URL.")
    interviewer_model: str = Field(default="gpt-4o-mini")
    extractor_model: str = Field(default="gpt-4o-mini")
    evaluator_model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    timeout_seconds: float = Field(default=8.0, gt=0.0)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCID_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    workflow_path: Path | None = Field(default=None)
    paths: Paths = Field(default_factory=Paths)
    llm: LLMSettings = Field(default_factory=LLMSettings)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    settings = AppSettings()
    if settings.workflow_path is None:
        settings.workflow_path = settings.paths.workflows / "workflow.json"
    return settings


def settings_dict() -> dict[str, Any]:
    return get_settings().model_dump()
