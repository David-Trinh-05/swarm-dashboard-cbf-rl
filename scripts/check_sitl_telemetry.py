"""Verify that both stock SITL vehicles reach the dashboard while disarmed."""

import json
import math
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

DRONES = {"UAV-01": 1, "UAV-02": 2}
AXES = ("x_north_m", "y_east_m", "z_down_m")


def read_dashboard(endpoint):
    try:
        with urlopen(f"http://127.0.0.1:8000/{endpoint}", timeout=1) as response:
            return json.load(response)
    except HTTPError as error:
        with error:
            if endpoint == "readyz" and error.code == 503:
                return json.load(error)
            raise


def summarize(ready, drones):
    summary = {}
    for drone_id, system_id in DRONES.items():
        sample = drones.get(drone_id, {})
        status = sample.get("status", {})
        position = sample.get("local_position", {})
        observed_id = sample.get("system_id")
        summary[drone_id] = {
            "system_id": observed_id,
            "online": sample.get("online") is True,
            "armed": status.get("armed"),
            "telemetry_fresh": ready.get("telemetry_fresh", {}).get(drone_id) is True,
            "position_available": all(
                type(value) in (int, float) and math.isfinite(value)
                for value in (position.get(axis) for axis in AXES)
            ),
            "identity_matches": type(observed_id) is int and observed_id == system_id,
        }
    passed = ready.get("ok") is True and all(
        row["online"]
        and row["armed"] is False
        and row["telemetry_fresh"]
        and row["position_available"]
        and row["identity_matches"]
        for row in summary.values()
    )
    return {"verdict": "PASS" if passed else "FAIL", "drones": summary}


def main(output):
    deadline = time.monotonic() + 45
    report = {"verdict": "FAIL", "error": "dashboard did not respond"}
    while time.monotonic() < deadline:
        try:
            ready = read_dashboard("readyz")
            drones = read_dashboard("api/drones").get("drones", {})
            report = summarize(ready, drones)
            armed = any(row["armed"] is True for row in report["drones"].values())
            if report["verdict"] == "PASS" or armed:
                break
        except (OSError, ValueError) as error:
            report = {"verdict": "FAIL", "error": str(error)}
        time.sleep(0.5)

    report["profile"] = "stock_x500"
    encoded = json.dumps(report, indent=2) + "\n"
    Path(output).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
