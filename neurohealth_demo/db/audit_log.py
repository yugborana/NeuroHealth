"""DB 5 — Audit Log (JSON file writer)."""

import json
import time
from pathlib import Path
from datetime import datetime


class AuditLog:
    """Appends agent execution logs to a JSON lines file."""

    def __init__(self, log_path: str | Path = None):
        if log_path is None:
            log_path = Path(__file__).parent.parent / "audit_log.json"
        self.log_path = Path(log_path)
        self._entries = []

    def log(self, entry: dict):
        """Add a log entry with timestamp."""
        entry["timestamp"] = datetime.now().isoformat()
        self._entries.append(entry)

        # Append to file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def get_all(self) -> list[dict]:
        """Return all entries from this session."""
        return self._entries

    def get_summary(self) -> dict:
        """Return a summary of the audit log."""
        total_time = sum(e.get("time_ms", 0) for e in self._entries)
        return {
            "total_agents_run": len(self._entries),
            "total_time_ms": round(total_time, 1),
            "agents": [e.get("agent", "unknown") for e in self._entries],
            "log_file": str(self.log_path),
        }

    def clear_session(self):
        """Clear in-memory entries (file is kept)."""
        self._entries = []
