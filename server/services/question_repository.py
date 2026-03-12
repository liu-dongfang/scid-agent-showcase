from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.config import get_settings
from server.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QuestionItem:
    item_id: str
    module: str
    description: str
    requires: list[str]
    schema: str
    anchors: list[str]
    followups: dict[str, str]
    maps_to_module: str | None = None
    constraints: dict[str, Any] | None = None


class QuestionRepository:
    """Load question manifests for phases and modules from configs/questions."""

    def __init__(self, base_path: Path | None = None) -> None:
        settings = get_settings()
        self.base_path = base_path or settings.paths.configs / "questions"
        self._cache: dict[str, list[QuestionItem]] = {}
        self._module_cache: dict[str, list[QuestionItem]] = {}
        self._load_phase_questions()
        self._load_module_questions()

    def _load_phase_questions(self) -> None:
        for path in self.base_path.glob("*.json"):
            try:
                payload = self._read_json(path)
            except Exception as exc:  # pragma: no cover - logged for visibility
                logger.error("question.load.error", path=str(path), error=str(exc))
                continue

            phase = payload.get("phase")
            module = payload.get("module")

            items_payload = payload.get("items", [])
            items = [self._item_from_dict(item, module or phase) for item in items_payload]

            if phase:
                self._cache[phase] = items
            elif module:
                self._module_cache[module] = items

    def _load_module_questions(self) -> None:
        # Already handled in _load_phase_questions by checking 'module' key, keep for clarity.
        pass

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def _item_from_dict(payload: dict[str, Any], module_name: str) -> QuestionItem:
        return QuestionItem(
            item_id=payload["item_id"],
            module=module_name,
            description=payload.get("description", ""),
            requires=list(payload.get("requires", [])),
            schema=payload["schema"],
            anchors=list(payload.get("anchors", [])),
            followups=dict(payload.get("followups", {})),
            maps_to_module=payload.get("maps_to_module"),
            constraints=payload.get("constraints"),
        )

    def questions_for_phase(self, phase: str) -> list[QuestionItem]:
        return self._cache.get(phase, [])

    def questions_for_module(self, module: str) -> list[QuestionItem]:
        return self._module_cache.get(module, [])

    def activation_targets_from_screening(self) -> dict[str, str]:
        """Map screening item_id to activation module if defined."""
        mapping: dict[str, str] = {}
        screening_items = self._cache.get("Screening", [])
        for item in screening_items:
            if item.maps_to_module:
                mapping[item.item_id] = item.maps_to_module
        return mapping
