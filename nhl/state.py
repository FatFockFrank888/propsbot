"""Tiny persistent key/value state (last recap date, failure counter)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BotState:
    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            self.data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if self.data.get(key) == value:
            return
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
