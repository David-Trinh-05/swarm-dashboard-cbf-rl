#!/usr/bin/env bash
# The offline suite runs without ROS, PX4, Gazebo, MQTT or research artifacts.
set -euo pipefail
cd "$(dirname "$0")/.."
"${PYTHON:-python3}" -m pytest -q \
  test_dashboard_access.py test_dashboard_boot.py test_cbf*.py \
  test_active_offboard_setpoint_sender.py test_offboard_authority.py \
  test_offboard_abort_conditions.py test_emergency_supervisor.py \
  test_worker_liveness_watchdog.py test_mission_ui_contract.py \
  test_mavlink_attitude_bridge.py test_sitl_smoke.py \
  test_two_uav_trajectory_flight.py test_two_uav_mission_circle_flight.py
