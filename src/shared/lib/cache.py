"""Simple TTL file-based cache for YouTube match results."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class YouTubeCache:
    """Persists track_id -> youtube_url mappings on disk with a TTL."""

    def __init__(self, cache_dir: str, ttl: int):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_file = self.cache_dir / "youtube_cache.json"
        self._data: dict = {}
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load YouTube cache, starting fresh: {e}")
            self._data = {}

    def _save(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
        except OSError as e:
            logger.warning(f"Failed to write YouTube cache: {e}")

    def get(self, key: str) -> Optional[str]:
        entry = self._data.get(key)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) > self.ttl:
            self._data.pop(key, None)
            return None
        return entry.get("url")

    def set(self, key: str, value: str) -> None:
        self._data[key] = {"url": value, "ts": time.time()}
        self._save()
