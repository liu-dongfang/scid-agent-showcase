from __future__ import annotations

import logging
import os
from typing import Any

try:  # pragma: no cover - optional dependency path
    import structlog  # type: ignore
except ImportError:  # pragma: no cover
    structlog = None


class _SimpleLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._logger.info(self._format(msg, kwargs))

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._logger.warning(self._format(msg, kwargs))

    def error(self, msg: str, **kwargs: Any) -> None:
        self._logger.error(self._format(msg, kwargs))

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._logger.debug(self._format(msg, kwargs))

    @staticmethod
    def _format(msg: str, data: dict[str, Any]) -> str:
        if not data:
            return msg
        formatted = " ".join(f"{key}={value!r}" for key, value in data.items())
        return f"{msg} | {formatted}"


def _resolve_log_level(level: int | str | None, *, debug: bool) -> int:
    """Resolve log level from CLI/env preferences."""

    candidate: int | str | None = level
    if candidate is None:
        env_level = os.getenv("SCID_LOG_LEVEL")
        if env_level:
            candidate = env_level

    if candidate is None:
        candidate = logging.DEBUG if debug else logging.INFO

    if isinstance(candidate, str):
        normalized = candidate.upper()
        resolved = logging.getLevelName(normalized)
        if isinstance(resolved, str):  # pragma: no cover - defensive guard
            raise ValueError(f"Invalid log level: {candidate}")
        candidate = resolved

    return int(candidate)


def configure_logging(*, debug: bool = False, level: int | str | None = None) -> None:
    resolved_level = _resolve_log_level(level, debug=debug)

    logging.basicConfig(
        level=resolved_level,
        format="%(message)s",
    )

    if structlog is None:
        return

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        cache_logger_on_first_use=True,
    )

    # Silence verbose AWS SDK / HTTP client logs - only show WARNING and above
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)


def get_logger(name: str = "scid") -> Any:
    if structlog is None:
        return _SimpleLogger(name)
    return structlog.get_logger(name)
