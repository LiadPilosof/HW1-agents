"""
Inspection Log Manager.
Maintains a separate structured log (logs/inspection_log.json) to record draft attempts,
evaluator feedback (for future Part B & C), and final responses separately from visible chat history.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import INSPECTION_LOG_PATH, LOGS_DIR


class InspectionLogger:
    """Helper to log chat turns and candidate revisions into a JSON inspection log."""

    def __init__(self, log_path: Path = INSPECTION_LOG_PATH):
        self.log_path = log_path
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self) -> None:
        """Create directory and empty JSON array if log file does not exist."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def read_logs(self) -> List[Dict[str, Any]]:
        """Read all log entries from the inspection log file."""
        self._ensure_log_file_exists()
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def log_turn(
        self,
        user_message: str,
        final_response: str,
        candidate_response: Optional[str] = None,
        attempts: Optional[List[Dict[str, Any]]] = None,
        status: str = "APPROVED",
        session_id: Optional[str] = None,
        turn_index: int = 1,
        scenario_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a conversation turn in the inspection log.
        In Part A, creates attempt 1 with candidate_response.
        Parts B and C can pass multi-attempt histories with evaluator feedback.
        """
        if attempts is None:
            # Default single attempt for Part A
            attempts = [
                {
                    "attempt_number": 1,
                    "candidate_response": candidate_response or final_response,
                    "is_acceptable": True if status == "APPROVED" else None,
                    "feedback": None,  # Will be populated by Evaluator in Part B
                }
            ]

        entry = {
            "entry_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id or "default_session",
            "turn_index": turn_index,
            "scenario_id": scenario_id,
            "user_message": user_message,
            "status": status,
            "final_response": final_response,
            "attempts": attempts,
        }

        logs = self.read_logs()
        logs.append(entry)

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        return entry

    def clear(self) -> None:
        """Clear all entries in the log file."""
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)


# Default singleton instance
inspection_logger = InspectionLogger()
