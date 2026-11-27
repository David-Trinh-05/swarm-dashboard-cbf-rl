"""Exercise the HTTP and WebSocket boundary without a broker or a flight stack."""

import base64
import json
import os
import unittest
from unittest.mock import patch

from dashboard_access import COOKIE, DashboardAccess


REMOTE = "https://lab.example"
AUTH = "Basic " + base64.b64encode(b"operator:test-password").decode()


class AccessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = []
        self.access = DashboardAccess(self.downstream)

    async def downstream(self, scope, receive, send):
        self.calls.append(scope["type"])
        if scope["type"] == "websocket":
            await send({"type": "websocket.accept"})
        else:
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

    async def request(self, *, kind="websocket", client="127.0.0.1",
                      host="127.0.0.1:8000", secure=False, **headers):
        events = []

        async def send(message):
            events.append(message)

        scope = {
            "type": kind,
            "scheme": ("https" if secure else "http") if kind == "http" else ("wss" if secure else "ws"),
            "client": (client, 40000),
            "headers": [(key.encode(), value.encode())
                        for key, value in {"host": host, **headers}.items()],
        }
        await self.access(scope, None, send)
        return events

    async def test_local_browser_and_native_client(self):
        for origin in ({}, {"origin": "http://127.0.0.1:8000"}):
            self.assertEqual((await self.request(**origin))[0]["type"], "websocket.accept")
        self.assertEqual(self.calls, ["websocket", "websocket"])

    async def test_cross_origin_external_ip_and_unknown_host_never_reach_handlers(self):
        for options in ({"origin": "https://other.example"},
                        {"client": "192.0.2.1"}, {"host": "other.example:8000"}):
            self.assertEqual((await self.request(**options))[0]["type"], "websocket.close")
        self.assertEqual((await self.request(kind="http", origin="null"))[0]["status"], 403)
        self.assertFalse(self.calls)

    async def test_remote_authentication_and_cookie_require_the_expected_origin(self):
        self.access = DashboardAccess(self.downstream, REMOTE, "test-password")
        host = {"host": "lab.example", "client": "192.0.2.2"}
        self.assertEqual((await self.request(kind="http", authorization=AUTH, **host))[0]["status"], 403)
        host["secure"] = True
        self.assertEqual((await self.request(kind="http", **host))[0]["status"], 401)
        self.assertEqual((await self.request(origin=REMOTE, **host))[0]["type"], "websocket.close")
        self.assertFalse(self.calls)
        response = (await self.request(kind="http", authorization=AUTH, **host))[0]
        self.assertEqual(response["status"], 200)
        cookie_header = dict(response["headers"])[b"set-cookie"].decode()
        self.assertIn("Secure", cookie_header)
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("SameSite=strict", cookie_header)
        self.assertTrue(cookie_header.startswith(COOKIE + "="))
        cookie = cookie_header.split(";", 1)[0]
        self.assertEqual((await self.request(cookie=cookie, origin=REMOTE, **host))[0]["type"],
                         "websocket.accept")
        self.assertEqual((await self.request(cookie=cookie, **host))[0]["type"], "websocket.close")
        self.assertEqual((await self.request(cookie=cookie, origin="https://other.example",
                                             **host))[0]["type"], "websocket.close")
        self.assertEqual((await self.request(origin=REMOTE, authorization="Basic ***",
                                             **host))[0]["type"], "websocket.close")
        self.assertEqual(self.calls, ["http", "websocket"])

    def test_remote_configuration_requires_both_credentials_and_https(self):
        for origin, secret in ((REMOTE, ""), ("", "secret"), ("http://lab.example", "secret"),
                               (REMOTE + "/subpath", "secret"), ("https://127.0.0.1", "secret")):
            with self.assertRaises(ValueError):
                DashboardAccess(self.downstream, origin, secret)


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_stack_readiness_requires_mqtt_and_fresh_nonretained_telemetry(self):
        import main

        fresh = {name: {"dashboard_received_monotonic_s": 99.0} for name in main.ALLOWED_DRONES}
        with patch.dict(os.environ, {"SWARM_START_ROS_TELEMETRY": "true"}), \
                patch.object(main, "latest_drones", fresh), \
                patch.object(main.time, "monotonic", return_value=100.0), \
                patch.object(main.mqtt_connected, "is_set", return_value=False) as mqtt:
            response = await main.readiness()
            self.assertEqual(response.status_code, 503)
            mqtt.return_value = True
            self.assertEqual((await main.readiness()).status_code, 200)
            fresh["UAV-02"]["dashboard_retained"] = True
            response = await main.readiness()
            self.assertEqual(response.status_code, 503)
            self.assertFalse(json.loads(response.body)["telemetry_fresh"]["UAV-02"])
            fresh["UAV-02"] = {"dashboard_received_monotonic_s": 95.0}
            self.assertEqual((await main.readiness()).status_code, 503)

            with patch.dict(os.environ, {"SWARM_START_ROS_TELEMETRY": "false"}):
                self.assertEqual((await main.readiness()).status_code, 200)


if __name__ == "__main__":
    unittest.main()
