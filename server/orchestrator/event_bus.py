from __future__ import annotations

from collections.abc import Callable
from typing import Any

from server.orchestrator.events import Event
from server.utils.logger import get_logger

logger = get_logger(__name__)


class EventBus:
    """Minimal synchronous event bus used to broadcast orchestrator events."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event, dict[str, Any]], None]] = []
        self.history: list[tuple[Event, dict[str, Any]]] = []

    def subscribe(self, handler: Callable[[Event, dict[str, Any]], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event: Event, payload: dict[str, Any]) -> None:
        logger.debug("event_bus.publish", event_name=event.value, payload=payload)
        entry = (event, payload)
        self.history.append(entry)
        for handler in list(self._subscribers):
            handler(event, payload)
