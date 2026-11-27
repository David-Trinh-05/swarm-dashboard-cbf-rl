from scripts.check_sitl_telemetry import DRONES, summarize


def test_stock_smoke_requires_live_disarmed_telemetry_from_both_px4_instances():
    ready = {"ok": True, "telemetry_fresh": dict.fromkeys(DRONES, True)}
    drones = {
        drone: {
            "system_id": system_id,
            "online": True,
            "status": {"armed": False},
            "local_position": {"x_north_m": 0.0, "y_east_m": 0.0, "z_down_m": 0.0},
        }
        for drone, system_id in DRONES.items()
    }

    assert summarize(ready, drones)["verdict"] == "PASS"
    assert summarize(ready, {"UAV-01": drones["UAV-01"]})["verdict"] == "FAIL"
    for mismatch in (
        {"status": {"armed": True}},
        {"system_id": 1},
        {"online": False},
        {"local_position": {"x_north_m": float("nan"), "y_east_m": 0.0, "z_down_m": 0.0}},
    ):
        wrong_instance = {**drones["UAV-02"], **mismatch}
        report = summarize(ready, {**drones, "UAV-02": wrong_instance})
        assert report["verdict"] == "FAIL"

    ready["telemetry_fresh"]["UAV-02"] = False
    assert summarize(ready, drones)["verdict"] == "FAIL"
