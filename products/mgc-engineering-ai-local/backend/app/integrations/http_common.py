from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from .base import ConnectorError, ConnectorHealth


class HttpConnectorBase:
    connector_type = "http"

    def __init__(self, config: dict[str, Any], secrets: dict[str, Any] | None = None):
        self.config = config or {}
        self.secrets = secrets or {}
        self.base_url = str(self.config.get("base_url", "")).rstrip("/")
        self.timeout = float(self.config.get("timeout_seconds", 20))
        verify: bool | str = self.config.get("ca_bundle") or self.config.get("tls_verify", True)
        cert = None
        cert_path = self.secrets.get("client_cert")
        key_path = self.secrets.get("client_key")
        if cert_path and key_path:
            cert = (str(cert_path), str(key_path))
        elif cert_path:
            cert = str(cert_path)
        self.client = httpx.Client(timeout=self.timeout, verify=verify, cert=cert)
        self._oauth_token_value: str | None = None
        self._oauth_token_expiry_monotonic: float = 0.0

    def _oauth_token(self) -> str | None:
        token_url = self.config.get("oauth_token_url")
        client_id = self.config.get("oauth_client_id")
        client_secret = self.secrets.get("oauth_client_secret")
        if not token_url or not client_id or not client_secret:
            return None
        if self._oauth_token_value and time.monotonic() < self._oauth_token_expiry_monotonic - 30:
            return self._oauth_token_value
        data = {"grant_type": "client_credentials"}
        scope = self.config.get("oauth_scope")
        if scope:
            data["scope"] = str(scope)
        auth_mode = self.config.get("oauth_client_auth", "basic")
        if auth_mode == "body":
            data["client_id"] = str(client_id)
            data["client_secret"] = str(client_secret)
            response = self.client.post(str(token_url), data=data)
        else:
            response = self.client.post(str(token_url), data=data, auth=(str(client_id), str(client_secret)))
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise ConnectorError("OAuth token endpoint returned no access_token")
        expires_in = max(int(payload.get("expires_in", 300)), 60)
        self._oauth_token_value = str(token)
        self._oauth_token_expiry_monotonic = time.monotonic() + expires_in
        return self._oauth_token_value

    def auth_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = self.secrets.get("token") or self.config.get("token") or self._oauth_token()
        api_key = self.secrets.get("api_key") or self.config.get("api_key")
        username = self.secrets.get("username")
        password = self.secrets.get("password")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif username is not None and password is not None:
            raw = f"{username}:{password}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
        if api_key:
            headers[self.config.get("api_key_header", "X-API-Key")] = str(api_key)
        return headers

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self.base_url:
            raise ConnectorError("base_url is required")
        headers = self.auth_headers()
        headers.update(kwargs.pop("headers", {}))
        url = path if str(path).startswith(("http://", "https://")) else self.base_url + str(path)
        response = self.client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def health(self) -> ConnectorHealth:
        path = self.config.get("health_path", "/health")
        started = time.perf_counter()
        try:
            r = self.request("GET", path)
            latency = (time.perf_counter() - started) * 1000
            return ConnectorHealth(True, f"HTTP {r.status_code}", latency_ms=round(latency, 2))
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000
            return ConnectorHealth(False, str(exc), latency_ms=round(latency, 2))
