# Smoke test PX4 SITL với X500 chuẩn

Smoke test khởi động Gazebo headless, hai PX4 SITL với X500 chuẩn (`4001_gz_x500`), Micro XRCE-DDS Agent, hai node ROS telemetry cùng các bridge MQTT và dashboard. Launcher dùng MQTT riêng trên loopback và thư mục trạng thái PX4 mới cho mỗi lần chạy. Smoke test chỉ chạy đường telemetry. [Cấu hình mô phỏng X500 của PX4](https://docs.px4.io/v1.15/en/sim_gazebo_gz/)

## Chạy từ bản clone

Chuẩn bị Ubuntu 24.04, Python 3.12, ROS 2 Jazzy, Gazebo Harmonic, Mosquitto và Micro XRCE-DDS Agent. Cần cây PX4 đã build `px4_sitl_default` với `gz_x500`, world `default.sdf` và model `x500`. Workspace ROS cung cấp `px4_msgs` tương thích với firmware và package `swarm_telemetry` đã build, có hai entry point `telemetry_node` và `mqtt_bridge`. Workspace ROS là đầu vào ngoài repo.

Từ thư mục repo, tạo môi trường Python rồi chỉ định đường dẫn hai workspace. Chế độ `--smoke` đọc cấu hình mẫu và nhận đường dẫn từ môi trường shell. Dừng stack SITL đang chạy trước khi kiểm tra. Các cổng dùng cho lượt chạy gồm TCP 8000, TCP 18883 và UDP 8888.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PX4_AUTOPILOT_ROOT=/path/to/PX4-Autopilot \
  SWARM_ROS_SETUP=/path/to/ros-workspace/install/setup.bash \
  ./run_all.sh --smoke
```

Launcher trả mã 0 khi `/readyz` xác nhận telemetry mới của cả hai UAV và `/api/drones` báo đúng system ID, có vị trí hữu hạn, online và disarmed. Sau lượt kiểm tra launcher dừng các tiến trình nó đã mở. Đường dẫn đến `smoke.json` và log nằm trong dòng `Logs:` ở terminal.

## Lượt kiểm chứng

[JSON thực nghiệm](smoke.json) ghi nhận cả hai UAV đạt kiểm tra qua pipeline thật trên Ubuntu 24.04.4, Gazebo Sim 8.15.0 và ROS 2 Jazzy. Bản PX4 ở máy thử có thay đổi cục bộ trên nền `85df8c2`. `px4_msgs` ở `a1045ec` và package telemetry từ revision workspace `1f9ef33`. Các revision mô tả môi trường đã thử. [PX4](https://github.com/PX4/PX4-Autopilot/commit/85df8c2281c2466b30a121b22b0bf33dc69bcfe4) · [px4_msgs](https://github.com/PX4/px4_msgs/commit/a1045ec4feb6d709bdecaf3895f1d5b43a5dabb8)

Phạm vi xác minh là khởi động stack và nhận telemetry khi disarmed. Camera, LiDAR và kiểm tra CBF-RL trong chuyến bay thuộc cấu hình thử nghiệm `x500_custom`. [Stack đầy đủ](../../../RUN_FULL_STACK.md) · [Benchmark CBF-RL](../cbf-rl/README.md)
