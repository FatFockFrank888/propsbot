"""Gemensam HTTP-hämtning för de öppna källorna: cache, artig takt, omförsök."""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


class SourceError(RuntimeError):
    pass


class JsonClient:
    def __init__(self, cache_dir: str | Path = ".cache_odds", ttl_s: float = 120.0,
                 min_interval_s: float = 0.35, headers: dict | None = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_s = ttl_s
        self.min_interval_s = min_interval_s
        self.headers = {"User-Agent": UA, "Accept": "application/json", **(headers or {})}
        self._last = 0.0
        self.calls = 0
        self.errors: list[str] = []

    def get(self, url: str, params: dict | None = None, ttl: float | None = None):
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        f = self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".json")
        ttl = self.ttl_s if ttl is None else ttl
        if f.exists() and time.time() - f.stat().st_mtime < ttl:
            return json.loads(f.read_text(encoding="utf-8"))
        for attempt in range(3):
            wait = self.min_interval_s - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=20) as r:
                    body = r.read().decode("utf-8")
                self.calls += 1
                data = json.loads(body)
                f.write_text(body, encoding="utf-8")
                return data
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                if e.code == 404:
                    return None
                msg = f"HTTP {e.code} för {url.split('?')[0]}"
                self.errors.append(msg)
                raise SourceError(msg) from e
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                msg = f"{type(e).__name__} för {url.split('?')[0]}: {e}"
                self.errors.append(msg)
                raise SourceError(msg) from e
        raise SourceError(f"gav upp: {url}")
