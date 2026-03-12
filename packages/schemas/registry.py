"""Runtime registry for schema lookups used by agents and orchestrator."""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class SchemaRegistry:
    """Lightweight registry that maps schema keys to Pydantic models and JSON payloads."""

    def __init__(self) -> None:
        self._models: dict[str, Callable[[], Any]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def register(self, name: str, model_factory: Callable[[], Any]) -> None:
        self._models[name] = model_factory

    def get_model(self, name: str) -> Any:
        if name not in self._models:
            raise KeyError(f"Schema model '{name}' is not registered.")
        return self._models[name]()

    def register_schema_payload(self, name: str, schema: dict[str, Any]) -> None:
        self._schemas[name] = schema

    def get_schema(self, name: str) -> dict[str, Any]:
        if name not in self._schemas:
            raise KeyError(f"Schema payload '{name}' is not registered.")
        return self._schemas[name]

    def load_from_directory(self, directory: Path) -> None:
        """Load JSON schema files from configs/schemas."""
        for path in directory.glob("*.json"):
            name = path.stem
            self._schemas[name] = self._load_json(path)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        import json

        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    @property
    def model_names(self) -> Mapping[str, Callable[[], Any]]:
        return dict(self._models)

    @property
    def schema_names(self) -> Mapping[str, dict[str, Any]]:
        return dict(self._schemas)
