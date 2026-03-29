from __future__ import annotations


class RuntimeNotReadyError(RuntimeError):
    """Raised when an agent runtime has no reachable target."""
