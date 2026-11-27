# Chạy và kiểm tra Swarm Dashboard

Cài môi trường Python, cấu hình PX4 và ROS theo [quickstart](README.md#chạy-từ-bản-clone). Chạy các lệnh từ repo.

```bash
./run_all.sh --check
./run_all.sh
```

Launcher mở Gazebo, hai PX4 SITL, bridge và dashboard theo `.env`. Nếu muốn dùng Gazebo headless, đặt `SWARM_START_GAZEBO_GUI=false`. Không mở stack thứ hai song song trên cùng các cổng điều khiển.

Để kiểm tra nhanh đầu vào telemetry với model X500 chuẩn, dùng `./run_all.sh --smoke`. [Điều kiện và báo cáo smoke test](docs/benchmarks/sitl/README.md)

## Tách tiến trình để chẩn đoán

Sau khi Mosquitto, Gazebo và PX4 SITL đã chạy, nạp cấu hình trong mỗi terminal chạy thành phần riêng.

```bash
set -a
source .env
set +a
```

| Thành phần | Lệnh |
| --- | --- |
| ROS telemetry | `./run_ros_telemetry_local.sh` |
| MAVLink bridge | `.venv/bin/python mavlink_manual_bridge.py` |
| Dashboard | `.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000` |

Quyền truy cập từ máy khác dùng [HTTPS proxy và xác thực](README.md#truy-cập-dashboard).

## Dấu hiệu cần kiểm tra

- Preflight chỉ ra đường dẫn PX4, model hoặc airframe bị thiếu. Kiểm tra `PX4_AUTOPILOT_ROOT` và profile airframe đã build.
- `/health` trả lời mà `/readyz` trả 503. Đọc `mqtt_connected` và `telemetry_fresh`, sau đó kiểm tra log tương ứng trong `artifacts/run_*/`.
- Trình duyệt mở trang nhưng WebSocket bị từ chối. Dùng chính địa chỉ đã mở dashboard. Với truy cập qua proxy, Origin phải trùng `SWARM_WEB_ORIGIN` và Host phải được giữ nguyên.
- Tùy chọn CBF-RL, mission và RGB Follow dùng các interlock riêng. [RGB Follow](VISUAL_FOLLOW_TARGET.md) · [CBF-RL](CBF_RL_ROADMAP.md)
