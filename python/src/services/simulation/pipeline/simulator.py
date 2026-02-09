from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ReplayStats:
    events_total: int = 0
    events_by_type: Dict[str, int] = None

    def __post_init__(self) -> None:
        if self.events_by_type is None:
            self.events_by_type = {}

    def on_event(self, event: Dict[str, Any]) -> None:
        self.events_total += 1
        event_type = str(event.get("type", "unknown"))
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1


def replay_event_stream(stats: ReplayStats, event: Dict[str, Any]) -> None:
    """
    Phase 1a replay handler (no execution).
    Just counts/classifies events for now.
    """
    stats.on_event(event)
