"""Small JSON-over-HTTP client with retries and an on-disk TTL cache (stdlib only)."""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import random
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    def __init__(self, status: int | None, url: str, message: str) -> None:
        prefix = f"HTTP {status}" if status else "Request failed"
        super().__init__(f"{prefix} for {url}: {message}")
        self.status = status
        self.url = url


def _retry_after(headers: Any) -> float | None:
    if headers is None:
        return None
    value = headers.get("Retry-After")
    if not value:
        return None
    try:
        return min(60.0, max(0.0, float(value)))
    except ValueError:
        return None


def _error_body(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read()[:300].decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - best-effort diagnostics only
        return exc.reason if isinstance(exc.reason, str) else ""
    return body.strip() or str(exc.reason)


class JsonClient:
    def __init__(
        self,
        cache_dir: Path,
        *,
        timeout: float = 20.0,
        max_retries: int = 4,
        user_agent: str = "nhl-propsbot/1.0",
        secret_params: Iterable[str] = ("apiKey",),
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.secret_params = frozenset(secret_params)

    def get(
        self,
        url: str,
        params: Mapping[str, Any] | None = None,
        *,
        ttl: float = 0,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        """GET a JSON document. Returns (data, lowercase headers).

        Responses are cached on disk for `ttl` seconds when ttl > 0. Secret query
        parameters (API keys) are never written to the cache or to error messages.
        """
        clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        full_url = url + ("?" + urllib.parse.urlencode(clean) if clean else "")
        public = {k: v for k, v in clean.items() if k not in self.secret_params}
        display_url = url + ("?" + urllib.parse.urlencode(public) if public else "")
        cache_path = self.cache_dir / (hashlib.sha256(display_url.encode("utf-8")).hexdigest()[:40] + ".json")

        if ttl > 0:
            cached = self._read_cache(cache_path, ttl)
            if cached is not None:
                return cached["data"], cached.get("headers", {})

        data, resp_headers = self._fetch(full_url, display_url, headers or {})
        if ttl > 0:
            self._write_cache(cache_path, display_url, data, resp_headers)
        return data, resp_headers

    def clear_cache(self) -> int:
        removed = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
                removed += 1
            except OSError as exc:
                log.warning("Could not delete %s: %s", path, exc)
        return removed

    # ------------------------------------------------------------------ internals
    def _fetch(self, full_url: str, display_url: str, extra_headers: Mapping[str, str]) -> tuple[Any, dict[str, str]]:
        request = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                **extra_headers,
            },
        )
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    body = resp.read()
                    if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                        body = gzip.decompress(body)
                    headers = {k.lower(): v for k, v in resp.headers.items()}
                try:
                    return json.loads(body.decode("utf-8")), headers
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise HttpError(200, display_url, f"invalid JSON response: {exc}") from None
            except urllib.error.HTTPError as exc:
                detail = _error_body(exc)
                if exc.code not in RETRY_STATUSES or attempt == self.max_retries:
                    raise HttpError(exc.code, display_url, detail) from None
                delay = _retry_after(exc.headers) or self._backoff(attempt)
                log.warning("HTTP %s from %s, retrying in %.1fs", exc.code, display_url, delay)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                reason = getattr(exc, "reason", exc)
                if attempt == self.max_retries:
                    raise HttpError(None, display_url, str(reason)) from None
                delay = self._backoff(attempt)
                log.warning("Network error for %s (%s), retrying in %.1fs", display_url, reason, delay)
            time.sleep(delay)
        raise HttpError(None, display_url, "retries exhausted")

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(30.0, 0.75 * (2 ** attempt)) + random.uniform(0, 0.5)

    @staticmethod
    def _read_cache(path: Path, ttl: float) -> dict[str, Any] | None:
        try:
            if time.time() - path.stat().st_mtime > ttl:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, path: Path, url: str, data: Any, headers: dict[str, str]) -> None:
        payload = {"url": url, "fetched_at": time.time(), "headers": headers, "data": data}
        try:
            fd, tmp = tempfile.mkstemp(dir=self.cache_dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            os.replace(tmp, path)
        except OSError as exc:
            log.warning("Could not write cache file %s: %s", path, exc)
