"""State persistence — save and restore trader state across restarts.

Trading state (position, entry price, sandbox balances) is written to a JSON
file after every trade so that the engine can resume from the exact same point
if it is restarted.  The write is atomic: data is flushed to a temp file first
and then renamed, so a crash during the write never corrupts the saved state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def save_state(state: dict[str, object], path: Path) -> None:
    """Persist *state* to *path* using an atomic write.

    Args:
        state: Dictionary of serialisable values to persist.
        path: Destination file path (created if absent).
    """
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(path)
        log.debug("State saved → %s", path)
    except OSError:
        log.warning("Failed to save state to %s", path, exc_info=True)


def load_state(path: Path) -> dict[str, object]:
    """Load and return state from *path*, or ``{}`` if absent or unreadable.

    Args:
        path: JSON file previously written by :func:`save_state`.

    Returns:
        Deserialized state dict, or an empty dict on any failure.
    """
    if not path.exists():
        log.info("No saved state at %s — starting fresh", path)
        return {}
    try:
        data: dict[str, object] = json.loads(path.read_text())
        log.debug("Restored state from %s: %s", path, data)
        return data
    except (OSError, json.JSONDecodeError):
        log.warning(
            "Failed to load state from %s — starting fresh", path, exc_info=True
        )
        return {}
