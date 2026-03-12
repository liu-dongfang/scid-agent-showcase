from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.config import get_settings


@dataclass
class PhaseConfig:
    name: str
    items_path: Path | None
    completion_requires: list[str]
    next_phase: str | None
    items_manifest: list[dict[str, Any]]


class Workflow:
    def __init__(self, payload: dict[str, Any], base_path: Path) -> None:
        self.initial_phase: str = payload["initial_phase"]
        self.events: dict[str, str] = payload.get("events", {})
        self._phases: dict[str, PhaseConfig] = {}
        self.enable_comorbidity_appendix: bool = payload.get("enable_comorbidity_appendix", False)
        config_path = payload.get("comorbidity_config_path")
        self.comorbidity_config_path: Path | None = (base_path / config_path) if config_path else None

        phases_payload: dict[str, dict[str, Any]] = payload["phases"]
        for phase_name, config in phases_payload.items():
            items_path = config.get("items_path")
            manifest = config.get("items_manifest", [])
            phase_config = PhaseConfig(
                name=phase_name,
                items_path=base_path / items_path if items_path else None,
                completion_requires=list(config.get("completion_requires", [])),
                next_phase=config.get("next_phase"),
                items_manifest=manifest,
            )
            self._phases[phase_name] = phase_config

    def phase(self, name: str) -> PhaseConfig:
        if name not in self._phases:
            raise KeyError(f"Unknown phase '{name}'")
        return self._phases[name]

    @property
    def phases(self) -> dict[str, PhaseConfig]:
        return self._phases


class WorkflowLoader:
    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self.path = path or settings.workflow_path or (settings.paths.configs / "workflow.json")

    def load(self) -> Workflow:
        payload = self._read_json(self.path)
        base_path = self.path.parent
        return Workflow(payload, base_path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
