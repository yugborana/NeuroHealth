"""
BaseAgent — Common base class for all pipeline agents.
Handles timing, audit logging, and error handling automatically.
"""

import time
from db.audit_log import AuditLog


class BaseAgent:
    """All agents inherit from this. Just override _process()."""

    name: str = "BaseAgent"
    layer: str = "unknown"

    def __init__(self, conn=None, audit: AuditLog = None, **kwargs):
        self.conn = conn
        self.audit = audit
        self.extras = kwargs

    def run(self, state: dict) -> dict:
        """Execute the agent: time it, log it, catch errors."""
        start = time.perf_counter()
        error = None

        try:
            result = self._process(state)
        except Exception as e:
            error = f"{self.name}: {e}"
            result = {}

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Build trace entry
        trace_entry = {
            "agent": self.name,
            "layer": self.layer,
            "time_ms": round(elapsed_ms, 1),
            "output_keys": list(result.keys()) if result else [],
            "error": error,
        }

        # Append to agent_trace in state
        if "agent_trace" not in state:
            state["agent_trace"] = []
        state["agent_trace"].append(trace_entry)

        # Log to audit
        if self.audit:
            self.audit.log(trace_entry)

        # Track errors
        if error:
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(error)

        # Merge result into state
        state.update(result)
        return result

    def _process(self, state: dict) -> dict:
        """Override this in each agent. Return dict of state updates."""
        raise NotImplementedError(f"{self.name}._process() not implemented")
