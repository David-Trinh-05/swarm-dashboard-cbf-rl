# Benchmark CBF-RL offline

Bộ đánh giá chạy năm kịch bản trên mô hình point-mass với bộ lọc CBF và kiểm tra lỗi mất covariance, trạng thái cũ, nguồn không hợp lệ và phục hồi sau gián đoạn. Baseline dùng cùng goal gain và bỏ thành phần tránh của policy. Mỗi JSON ghi SHA-256 của model, kết quả từng kịch bản của cả hai bên, khoảng cách tối thiểu, biên CBF, số frame can thiệp hoặc hold và các kiểm tra lỗi.

| Policy | Kịch bản hoàn thành | Baseline | Biên CBF thấp nhất | Kết quả |
| --- | ---: | ---: | ---: | --- |
| [v1](v1.json) | 1/5 | 1/5 | −0,940 m | FAIL |
| [v2](v2.json) | 1/5 | 1/5 | −0,801 m | FAIL |
| [mission_v1](mission-v1.json) | 5/5 | 3/5 | +0,847 m | PASS |

`mission_v1` có khoảng cách vật lý tối thiểu 7,441 m, không có frame hold và qua các kiểm tra lỗi. Kết quả này áp dụng cho mô phỏng point-mass trong benchmark. Các thử nghiệm PX4 SITL trước đây được ghi trong [roadmap](../../../CBF_RL_ROADMAP.md).

## Tái lập từ bản clone

Chạy từ thư mục gốc với Python 3.12. Hai lệnh đầu đánh giá v1 và v2 trả exit code 1 theo verdict FAIL. Lệnh mission trả 0. Workflow **Offline checks** cho phép bật tùy chọn benchmark khi chạy thủ công để tạo và tải ba JSON.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install numpy==2.4.4
mkdir -p artifacts/cbf-rl-offline
.venv/bin/python cbf_rl_evaluate.py --model cbf_rl_policy_v1.json --output artifacts/cbf-rl-offline/v1.json
.venv/bin/python cbf_rl_evaluate.py --model cbf_rl_policy_v2.json --output artifacts/cbf-rl-offline/v2.json
.venv/bin/python cbf_rl_evaluate.py --model cbf_rl_policy_mission_v1.json --output artifacts/cbf-rl-offline/mission-v1.json
```

## Kiểm tra cặp trace và báo cáo SITL

Mỗi phiên ghi cần `SWARM_SITL_RUN_ID` mới, dùng cùng giá trị ở môi trường bridge và tiến trình tạo báo cáo flight. Đặt `SWARM_COMPANION_SAFETY_LOG` thành đường dẫn trace JSONL mới. Hai tiến trình phải dùng cùng đồng hồ monotonic của hệ điều hành. Evaluator so run ID của tất cả dòng trace với báo cáo flight và chỉ dùng frame trong khoảng thời gian của báo cáo. Trace lịch sử thiếu metadata này sẽ cho FAIL.

Có thể chạy evaluator trên [fixture tổng hợp](../../../tests/fixtures/cbf_rl_sitl/) từ thư mục gốc. Fixture chỉ kiểm tra ghép dữ liệu và xử lý JSON.

```bash
python3 cbf_rl_sitl_evaluate.py \
  --trace tests/fixtures/cbf_rl_sitl/shadow_trace.jsonl \
  --flight tests/fixtures/cbf_rl_sitl/flight.json \
  --model-sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --minimum-trajectory-samples 1
```

Khi đánh giá một phiên SITL đã ghi, dùng trace và báo cáo của phiên đó cùng SHA-256 của model và mode tương ứng. Giữ ngưỡng mẫu mặc định cho các phiên SITL chuẩn. Báo cáo evaluator ghi số frame đầu vào, số frame trong cửa sổ chuyến bay và lỗi provenance nếu có.
