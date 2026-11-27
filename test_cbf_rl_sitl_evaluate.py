import copy
import json
import subprocess
import sys
import time
from pathlib import Path

from cbf_rl_sitl_evaluate import DRONES, evaluate


SHA = "a" * 64
RUN_ID = "synthetic-sitl-001"


def _active_row(drone_id: str) -> dict:
    cbf = {"active": True, "reason": "cbf_filtered", "minimum_margin_m": 0.5}
    shielded = [0.1, 0.2, 0.0]
    return {
        "drone_id": drone_id,
        "run_id": RUN_ID,
        "evaluated_monotonic_s": 15.0,
        "station_keeping": True,
        "nominal_reason": "tracking_slot",
        "authority": "shadow_companion_only",
        "nominal_source": "cbf_rl_active",
        "output_velocity_enu_m_s": shielded,
        "cbf": cbf,
        "emergency": {"stage": "normal"},
        "active_offboard_conditions": [],
        "active_offboard_sender": {"latched_abort": None},
        "active_offboard_frame": {"decision": "transmit", "transmitted": True},
        "cbf_rl_shadow": {
            "mode": "active",
            "valid": True,
            "model_sha256": SHA,
            "applied": True,
            "transmit_authority": True,
            "normalized_action": [0.1, 0.2, 0.0],
            "nominal_delta_norm_m_s": 0.1,
            "shielded_delta_norm_m_s": 0.2,
            "shielded_velocity_enu_m_s": shielded,
            "cbf": cbf,
        },
    }


def _shadow_row(drone_id: str) -> dict:
    row = _active_row(drone_id)
    row["nominal_reason"] = "tracking_trajectory"
    row["cbf_rl_shadow"].update(
        {"mode": "shadow", "applied": False, "transmit_authority": False}
    )
    return row


FLIGHT = {
    "run_id": RUN_ID,
    "started_monotonic_s": 10.0,
    "finished_monotonic_s": 20.0,
    "verdict": "FLIGHT_PASS",
    "final_state": {drone: {"armed": False} for drone in DRONES},
}


def test_valid_shadow_flight_passes() -> None:
    report = evaluate(
        [_shadow_row(drone) for drone in DRONES],
        FLIGHT,
        SHA,
        minimum_trajectory_samples=1,
    )

    assert report["verdict"] == "PASS"
    assert report["per_drone"]["UAV-01"]["minimum_shadow_cbf_margin_m"] == 0.5


def test_circle_driver_final_safe_record_is_accepted() -> None:
    flight = {
        **FLIGHT,
        "verdict": "FLIGHT_PASS",
        "circle": {"radius_m": 5.0},
        "records": [
            {
                "event": "FINAL_SAFE_STATE",
                "armed": {drone: False for drone in DRONES},
            }
        ],
    }

    report = evaluate(
        [_shadow_row(drone) for drone in DRONES],
        flight,
        SHA,
        minimum_trajectory_samples=1,
    )

    assert report["verdict"] == "PASS"
    assert report["checks"]["landed_and_disarmed"]


def test_applied_shadow_output_fails() -> None:
    rows = [_shadow_row(drone) for drone in DRONES]
    rows[0]["cbf_rl_shadow"]["applied"] = True

    report = evaluate(rows, FLIGHT, SHA, minimum_trajectory_samples=1)

    assert report["verdict"] == "FAIL"
    assert not report["checks"]["UAV-01:never_applied_or_authorized"]


def test_active_evaluation_requires_real_transmission() -> None:
    rows = [_active_row(drone) for drone in DRONES]
    flight = {
        **FLIGHT,
        "verdict": "FLIGHT_PASS",
        "final_state": {drone: {"armed": False} for drone in DRONES},
    }

    report = evaluate(
        rows, flight, SHA, minimum_trajectory_samples=1, expected_mode="active"
    )
    assert report["verdict"] == "PASS"

    withheld = copy.deepcopy(rows)
    withheld[0]["active_offboard_frame"]["transmitted"] = False
    report = evaluate(
        withheld, flight, SHA, minimum_trajectory_samples=1, expected_mode="active"
    )
    assert report["verdict"] == "FAIL"
    assert not report["per_drone"]["UAV-01"]["checks"][
        "every_frame_transmitted"
    ]


def test_active_trajectory_requires_both_drones_to_reach_end() -> None:
    rows = [_active_row(drone) for drone in DRONES]
    for row in rows:
        row["nominal_reason"] = "tracking_trajectory"
    flight = {
        **FLIGHT,
        "expected_trajectory_env": {"SWARM_TRAJECTORY_UAV_01_KIND": "linear"},
        "records": [
            {
                "step": "TRAJECTORY_HOLD_COMPLETE",
                "drone_id": drone,
                "reached_trajectory_end": drone == "UAV-01",
            }
            for drone in DRONES
        ],
    }

    report = evaluate(
        rows, flight, SHA, minimum_trajectory_samples=1, expected_mode="active"
    )

    assert report["milestone"] == "CBF_RL_ACTIVE_TRAJECTORY"
    assert report["verdict"] == "FAIL"
    assert report["checks"]["UAV-01:trajectory_completed"]
    assert not report["checks"]["UAV-02:trajectory_completed"]


def test_trace_from_another_run_or_legacy_trace_cannot_pass() -> None:
    rows = [_shadow_row(drone) for drone in DRONES]
    for run_id, problem in (
        ("another-run", "trace_run_id_mismatch"),
        (None, "flight_run_id_missing"),
    ):
        report = evaluate(
            rows, {**FLIGHT, "run_id": run_id}, SHA, minimum_trajectory_samples=1
        )
        assert report["verdict"] == "FAIL"
        assert report["provenance"]["error"] == problem
    report = evaluate([*rows, {**rows[0], "run_id": "another-run"}], FLIGHT, SHA)
    assert report["verdict"] == "FAIL"
    assert report["provenance"]["error"] == "trace_run_id_mismatch"


def test_excludes_frames_before_and_after_the_flight() -> None:
    rows = [_shadow_row(drone) for drone in DRONES]
    previous = {**rows[0], "evaluated_monotonic_s": 5.0, "cbf_rl_shadow": {}}
    later = {**rows[1], "evaluated_monotonic_s": 25.0, "cbf_rl_shadow": {}}
    report = evaluate([previous, *rows, later], FLIGHT, SHA, minimum_trajectory_samples=1)
    assert report["verdict"] == "PASS"
    assert report["provenance"]["in_flight_window"] == 2
    report = evaluate([previous, later], FLIGHT, SHA, minimum_trajectory_samples=1)
    assert report["verdict"] == "FAIL"
    assert report["provenance"]["error"] == "no_trace_frames_in_flight_window"


def test_synthetic_sitl_fixture_through_cli(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent
    fixtures = root / "tests/fixtures/cbf_rl_sitl"
    output = tmp_path / "evaluation.json"
    command = [
        sys.executable,
        str(root / "cbf_rl_sitl_evaluate.py"),
        "--trace", str(fixtures / "shadow_trace.jsonl"),
        "--flight", str(fixtures / "flight.json"),
        "--model-sha256", SHA,
        "--minimum-trajectory-samples", "1",
        "--output", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    report = json.loads(output.read_text())
    assert json.loads(result.stdout) == report
    assert report["verdict"] == "PASS"
    assert report["provenance"] == {
        "run_id": RUN_ID,
        "trace_rows": 2,
        "in_flight_window": 2,
        "error": None,
    }


def test_invalid_flight_or_trace_timestamp_fails() -> None:
    rows = [_shadow_row(drone) for drone in DRONES]
    flight = {**FLIGHT, "finished_monotonic_s": FLIGHT["started_monotonic_s"]}
    report = evaluate(rows, flight, SHA, minimum_trajectory_samples=1)
    assert report["verdict"] == "FAIL"
    assert report["provenance"]["error"] == "invalid_flight_window"
    rows[0].pop("evaluated_monotonic_s")
    report = evaluate(rows, FLIGHT, SHA, minimum_trajectory_samples=1)
    assert report["verdict"] == "FAIL"
    assert report["provenance"]["error"] == "invalid_trace_timestamp"


def test_bridge_trace_and_flight_metadata_share_run_id(tmp_path: Path, monkeypatch) -> None:
    import mavlink_manual_bridge as bridge
    from sitl_run import configured_run_id, flight_metadata

    log = tmp_path / "trace.jsonl"
    monkeypatch.setenv("SWARM_SITL_RUN_ID", RUN_ID)
    monkeypatch.setattr(bridge, "COMPANION_SAFETY_LOG_PATH", str(log))
    monkeypatch.setattr(bridge, "COMPANION_SAFETY_RUN_ID", configured_run_id())
    worker = object.__new__(bridge.MavlinkWorker)

    started = time.monotonic()
    for drone in DRONES:
        worker.append_companion_safety_trace({
            **_shadow_row(drone),
            "evaluated_monotonic_s": time.monotonic(),
            "run_id": "wrong",
        })
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    flight = {**FLIGHT, **flight_metadata(started)}
    report = evaluate(rows, flight, SHA, minimum_trajectory_samples=1)

    assert report["verdict"] == "PASS"
    assert report["provenance"]["run_id"] == RUN_ID
    assert report["provenance"]["in_flight_window"] == 2
