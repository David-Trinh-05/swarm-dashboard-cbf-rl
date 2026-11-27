"""Authorize dashboard requests before entering the control application."""

import base64
import binascii
import ipaddress
import secrets
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


COOKIE = "__Host-swarm-operator"


def is_loopback(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def valid_local_host(host: str) -> bool:
    try:
        parsed = urlsplit(f"http://{host}")
        port = parsed.port
        return (parsed.netloc == host and not parsed.path and not parsed.query
                and not parsed.fragment and parsed.username is None
                and (port is None or port > 0)
                and (parsed.hostname == "localhost" or is_loopback(parsed.hostname or "")))
    except ValueError:
        return False


class DashboardAccess:
    def __init__(self, app: ASGIApp, remote_origin: str = "", password: str = "") -> None:
        self.app = app
        self.remote_origin = remote_origin
        self.remote_host = ""
        self.credentials = b""
        self.session = ""
        if not remote_origin and not password:
            return
        parsed = urlsplit(remote_origin)
        if (not password or parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or valid_local_host(parsed.netloc)
                or remote_origin != f"https://{parsed.netloc}"
                or any(char.isspace() for char in remote_origin) or parsed.port == 0):
            raise ValueError("Remote access requires SWARM_WEB_PASSWORD and an HTTPS SWARM_WEB_ORIGIN")
        self.remote_host = parsed.netloc
        self.credentials = f"operator:{password}".encode()
        self.session = secrets.token_urlsafe(32)

    def valid_basic(self, value: str) -> bool:
        scheme, _, token = value.partition(" ")
        if scheme.lower() != "basic":
            return False
        try:
            return secrets.compare_digest(base64.b64decode(token, validate=True), self.credentials)
        except (ValueError, binascii.Error):
            return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        kind = scope["type"]
        if kind not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        hosts = headers.getlist("host")
        origins = headers.getlist("origin")
        host = hosts[0] if len(hosts) == 1 else ""
        origin = origins[0] if len(origins) == 1 else None
        client = scope.get("client")
        scheme = scope["scheme"]
        local = client and scheme in {"http", "ws"} and is_loopback(client[0]) and valid_local_host(host)
        remote = self.remote_host and scheme in {"https", "wss"} and host == self.remote_host
        trusted_origin = f"http://{host}" if local else self.remote_origin
        if len(origins) <= 1 and (origin is None or origin == trusted_origin):
            if local:
                await self.app(scope, receive, send)
                return
            if remote and (kind == "http" or origin == self.remote_origin):
                cookie = HTTPConnection(scope).cookies.get(COOKIE, "")
                valid_cookie = secrets.compare_digest(cookie.encode(), self.session.encode())
                basic = self.valid_basic(headers.get("authorization", ""))
                if valid_cookie or basic:
                    if kind == "http" and basic and not valid_cookie:
                        session_header = Response()
                        session_header.set_cookie(
                            COOKIE, self.session, max_age=28_800, secure=True,
                            httponly=True, samesite="strict",
                        )

                        async def send_with_session(message):
                            if message["type"] == "http.response.start":
                                response_headers = MutableHeaders(scope=message)
                                response_headers.append("set-cookie", session_header.headers["set-cookie"])
                                response_headers["cache-control"] = "no-store"
                            await send(message)

                        await self.app(scope, receive, send_with_session)
                    else:
                        await self.app(scope, receive, send)
                    return
                if kind == "http":
                    response = PlainTextResponse(
                        "Operator authentication required", status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="Swarm Dashboard"'},
                    )
                    await response(scope, receive, send)
                    return

        if kind == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        else:
            await PlainTextResponse("Forbidden", status_code=403)(scope, receive, send)
