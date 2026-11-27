"""Shared provenance for local SITL reports and the companion trace."""

import os
import time


def configured_run_id() -> str:
    return os.environ.get("SWARM_SITL_RUN_ID", "").strip()


def flight_metadata(started_monotonic_s: float) -> dict[str, str | float]:
    return {
        "run_id": configured_run_id(),
        "started_monotonic_s": started_monotonic_s,
        "finished_monotonic_s": time.monotonic(),
    }
