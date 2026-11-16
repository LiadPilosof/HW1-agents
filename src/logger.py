"""
Inspection log: a JSON file kept separately from the visible chat (Part A §4).

Each handled question becomes one entry holding the Actor's draft, the Critic's
decision and feedback, or the technical error that stopped the handling.
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import INSPECTION_LOG_PATH


class InspectionLogger:
    """Append-only JSON log; thread-safe because Gradio runs handlers concurrently."""

    def __init__(self, log_path: Path = INSPECTION_LOG_PATH):
        self.log_path = log_path
        self._lock = threading.Lock()

    def read_logs(self) -> list[dict[str, Any]]:
        """Return all entries ([] if the file is missing or unreadable)."""
        try:
            data = json.loads(self.log_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        """Stamp the record with an id and timestamp, append it and return it."""
        entry = {
            "entry_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **record,
        }
        with self._lock:
            logs = self.read_logs()
            logs.append(entry)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.write_text(
                json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return entry
