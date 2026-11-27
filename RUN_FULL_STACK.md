# Run the Swarm Dashboard stack

Use the full stack for the interactive camera, gimbal, LiDAR, mission, and companion safety features. Use the [stock X500 smoke test](docs/benchmarks/sitl/README.md) to verify the telemetry pipeline with stock simulation assets.

## Prerequisites

Use Linux with Python 3.12, ROS 2 Jazzy, Gazebo Harmonic, Mosquitto, and Micro XRCE-DDS Agent.

| External dependency | Required components |
| --- | --- |
| PX4 workspace | A `px4_sitl_default` build with `px4`, `px4-param`, `rootfs/gz_env.sh`, the `default.sdf` world, the `x500_custom` Gazebo model and the built airframe `22000_gz_x500_custom`. |
| ROS workspace | A built `swarm_telemetry` package with `two_uav_nodes.launch.py` and PX4 messages compatible with the PX4 build. |
| Gazebo Python bindings | System packages for `gz.transport13` and `gz.msgs10`. |

Record the PX4 and `px4_msgs` commits, the `swarm_telemetry` revision, and the custom model and airframe versions when handing off a working environment. The checkout includes the hybrid tracking backend. Additional tracking backends may require their own workspace or weights.

## Start the stack

From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
test -e .env || cp .env.example .env
```

Set `PX4_AUTOPILOT_ROOT` and `SWARM_ROS_SETUP` in `.env`. Set `SWARM_GZ_MODEL_ROOT` when the models are outside the PX4 tree, and `SWARM_TRACKING_PACKAGE_ROOT` when an external tracking backend requires it. The sample ENU coordinates correspond to the default PX4 world. [Sample environment](.env.example)

```bash
./run_all.sh --check
./run_all.sh
```

Open `http://127.0.0.1:8000`. Logs are written under `artifacts/run_*/`. Use Ctrl+C in the launcher terminal to stop the stack. Set `SWARM_START_GAZEBO_GUI=false` for headless simulation. The sample environment keeps Offboard, mission execution, and CBF-RL disabled. Run one stack per set of control ports. [Visual follow](VISUAL_FOLLOW_TARGET.md) · [CBF-RL roadmap](CBF_RL_ROADMAP.md)

## Dashboard access

The launcher binds to `127.0.0.1:8000` by default. Browser WebSocket requests must arrive from the configured Origin. Local loopback clients can connect with no Origin header.

For remote access, put an HTTPS proxy in front of the loopback backend. Preserve the Host header, forward WebSocket connections, and set `X-Forwarded-Proto: https`. Configure Uvicorn to trust forwarded headers from the loopback proxy. Set `SWARM_WEB_ORIGIN` to the exact public origin and set a long, randomly generated `SWARM_WEB_PASSWORD` in the local `.env`. Open the dashboard over HTTPS and sign in as `operator`. Browser sessions use Secure, HttpOnly, SameSite Strict cookies. The WebSocket validates the session and Origin before accepting commands. Restarting the dashboard clears sessions.

## Diagnose startup

```bash
curl -sS http://127.0.0.1:8000/health
curl --fail-with-body http://127.0.0.1:8000/readyz
```

`/health` provides process diagnostics. `/readyz` checks MQTT, the frontend file, and fresh telemetry from both UAVs when ROS telemetry is enabled. Check the indicated file paths if preflight fails. If readiness returns 503, read `mqtt_connected` and `telemetry_fresh`, then inspect the corresponding process logs. If a browser WebSocket is rejected, confirm the URL, expected Origin, and forwarded Host.

Once Mosquitto, Gazebo, and PX4 SITL are running, load settings in each terminal used to start a component separately:

```bash
set -a
source .env
set +a
```

| Component | Command |
| --- | --- |
| ROS telemetry | `./run_ros_telemetry_local.sh` |
| MAVLink bridge | `.venv/bin/python mavlink_manual_bridge.py` |
| Dashboard | `.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000` |
