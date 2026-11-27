# Swarm UAV Dashboard

Dashboard thử nghiệm cho hai PX4 SITL trong Gazebo. FastAPI nhận telemetry qua MQTT và hiển thị trạng thái UAV, camera, gimbal, LiDAR và kết quả CBF. Bridge MAVLink xử lý lệnh dành cho mô phỏng.

- [Chạy stack và xử lý lỗi](RUN_FULL_STACK.md)
- [RGB Follow Target](VISUAL_FOLLOW_TARGET.md)
- [Benchmark CBF-RL tái lập](docs/benchmarks/cbf-rl/README.md)
- [Roadmap và kết quả CBF-RL trước đây](CBF_RL_ROADMAP.md)
- [Tài liệu bàn giao cũ và các thử nghiệm UniDepth](docs/archive/README.md)

## Chạy từ bản clone

Dùng Linux với Python 3.12, ROS 2 Jazzy, Gazebo Harmonic, Mosquitto và Micro XRCE-DDS Agent. Cần hai workspace ngoài repo.

| Workspace | Thành phần cần có |
| --- | --- |
| PX4 SITL | Bản build `px4_sitl_default` có binary `px4`, `px4-param`, `rootfs/gz_env.sh`, world `default.sdf`, model `x500_custom` và airframe build `22000_gz_x500_custom`. |
| ROS 2 | Workspace đã build `swarm_telemetry` với launch `two_uav_nodes.launch.py` và message PX4 tương thích với bản SITL. Gazebo Python bindings `gz.transport13` và `gz.msgs10` đến từ gói hệ điều hành. |

Model, airframe và ROS workspace là phụ thuộc ngoài checkout. Khi bàn giao môi trường, ghi lại commit PX4, commit `px4_msgs` và revision của `swarm_telemetry` cùng các thay đổi riêng dành cho `x500_custom`. Checkout này dùng hợp đồng asset ở bảng trên. Backend tracking hybrid có sẵn trong repo. Những backend bổ sung có thể cần workspace tracking hoặc model riêng. [Cấu hình mẫu](.env.example)

```bash
git clone https://github.com/David-Trinh-05/swarm-dashboard-cbf-rl.git
cd swarm-dashboard-cbf-rl
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Trong `.env`, đặt `PX4_AUTOPILOT_ROOT` và `SWARM_ROS_SETUP` theo workspace của máy. Nếu dùng backend tracking ngoài repo, đặt thêm `SWARM_TRACKING_PACKAGE_ROOT`. Chỉ đặt `SWARM_GZ_MODEL_ROOT` khi models nằm ngoài cây PX4. Launcher lấy đường dẫn model mặc định từ PX4 root sau khi đọc cấu hình. Các giá trị ENU trong `.env.example` dành cho world PX4 mặc định.

```bash
./run_all.sh --check
./run_all.sh
```

Mở `http://127.0.0.1:8000`. Nhật ký tiến trình nằm trong `artifacts/run_*/`. Mỗi stack nên có một bridge MAVLink. Dùng Ctrl+C ở terminal launcher để dừng stack đang chạy. Cấu hình mẫu giữ OFFBOARD, mission execution và CBF-RL ở trạng thái tắt.

## Truy cập dashboard

Launcher mặc định bind `127.0.0.1:8000`. Trình duyệt phải gửi Origin khớp với địa chỉ mở dashboard. Công cụ local chạy trên loopback có thể kết nối WebSocket mà không cần Origin.

Để truy cập từ máy khác, đặt proxy HTTPS trước backend loopback. Proxy cần giữ nguyên header Host, chuyển tiếp WebSocket và đặt `X-Forwarded-Proto: https`. Uvicorn chỉ nên tin các forwarded header từ địa chỉ proxy loopback. Đặt `SWARM_WEB_ORIGIN` thành đúng public origin, chẳng hạn `https://dashboard.example.net`, và `SWARM_WEB_PASSWORD` thành một mật khẩu ngẫu nhiên dài trong file `.env` của máy chạy stack. Mở dashboard qua HTTPS và đăng nhập với username `operator`. Sau khi xác thực, phiên trình duyệt dùng cookie Secure, HttpOnly và SameSite Strict. WebSocket kiểm tra Origin và phiên trước khi nhận lệnh. Khởi động lại dashboard sẽ xóa phiên cũ.

## Kiểm tra runtime

```bash
curl -sS http://127.0.0.1:8000/health
curl --fail-with-body http://127.0.0.1:8000/readyz
```

`/health` cho biết backend đang trả lời và cung cấp chẩn đoán. Launcher chờ `/readyz` trả HTTP 200. Endpoint này kiểm tra MQTT, trang web và telemetry mới của cả hai UAV khi ROS telemetry được bật. Đây là readiness của dashboard. Trạng thái PX4 và các interlock điều khiển vẫn được kiểm tra ở nơi thực thi lệnh.

## Test offline

Bộ test lõi chạy từ bản clone với Python 3.12, không cần `.env`, PX4, Gazebo, ROS 2, MQTT broker hay dataset nghiên cứu. Trên Ubuntu 24.04, OpenCV cần các gói hệ thống `libgl1` và `libglib2.0-0t64`.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
PYTHON=.venv/bin/python bash scripts/test-core.sh
```

GitHub Actions chạy cùng lệnh khi mở hoặc cập nhật pull request và khi push lên `master`. [Workflow Offline checks](.github/workflows/offline.yml)

Các bài test replay, SITL và ML sử dụng môi trường và dữ liệu tương ứng. Với ML, cài thêm `requirements-ml.txt` và chuẩn bị fixture hoặc dataset theo tài liệu từng thử nghiệm. [Tài liệu nghiên cứu](docs/)
