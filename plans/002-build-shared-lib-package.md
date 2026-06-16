# Plan 002 — Build the missing `src.shared.lib` package

**Written against commit:** `e5867eb`
**Finding:** #1 (CRITICAL) · **Effort:** L · **Risk:** Med
**Depends on:** nothing (do alongside/after 001) · **Blocks:** the entire app, plans 003/004/006/007

## Why this matters

The codebase imports a package `src.shared.lib` with modules `utils`, `cache`,
`file_manager`, `observers`, and `exceptions`. **None of these exist** — they were
never committed (verified: `git log --all -- "src/shared/lib/"` is empty). Two are
imported at module top-level in the run path, so the app crashes with
`ModuleNotFoundError: No module named 'src.shared.lib'` when the DI container is built
— before any command (`--setup`, `--check`, downloads) can run.

This plan creates the package with implementations whose **public API exactly matches
every existing call site**. Get the signatures wrong and downstream code breaks.

## Exact API required (from call sites — do not deviate)

`src/utils.py` already exists at the repo root with the utility functions. `shared.lib.utils`
must expose the SAME functions (you will copy that file). The other four modules must
be authored to these contracts:

**`utils`** — callers and the functions they need:
- `youtube_matcher.py:10` → `clean_search_query(query: str) -> str`
- `cli.py:347`, `spotify_adapter.py:115,194` → `validate_url(url) -> bool`, `extract_playlist_id(url) -> Optional[str]`
- `progress.py` (5 sites) → `format_duration(seconds: int) -> str`, `format_speed(bytes_per_second: float) -> str`
- `file_manager` (this plan) → `sanitize_filename`, `get_file_extension`, `is_valid_audio_file`

**`cache.YouTubeCache`** — `youtube_matcher.py:11,37` and `providers.py:134-138`:
- `__init__(self, cache_dir: str, ttl: int)`  (provider passes `cache_dir`, `ttl=86400`)
- `.get(self, key: str) -> Optional[str]`     (matcher calls `self.cache.get(track.id)`)
- `.set(self, key: str, value: str) -> None`  (matcher calls `self.cache.set(track.id, url)`)

**`file_manager.FileManager`** — `download_manager.py` and `providers.py:159-162`:
- `__init__(self, base_output_dir: str)`
- `.create_playlist_directory(self, name: str) -> Path`
- `.get_output_path(self, playlist_dir: Path, track_number: int, artist: str, title: str, fmt: str, filename_template: str) -> Path`
- `.validate_file(self, path: Path) -> bool`
- `.delete_file(self, path: Path) -> None`
- `.save_resume_state(self, playlist_id: str, state: dict) -> None`
- `.load_resume_state(self, playlist_id: str) -> Optional[dict]`
- `.delete_resume_state(self, playlist_id: str) -> None`
- `.generate_m3u_playlist(self, playlist_dir: Path, name: str, track_files: list) -> None`

**`observers`** — `providers.py:82,87,93` (only referenced as DI string paths, never
called in the run path, but must import cleanly):
- `class ProgressSubject` — `__init__(self)`, `.attach(observer)`, `.detach(observer)`, `.notify(event, data=None)`
- `class ConsoleObserver` — `__init__(self, verbose: bool = False)`, `.update(event, data=None)`
- `class FileObserver` — `__init__(self, log_file)`, `.update(event, data=None)`

**`exceptions`** — names imported by `legacy/exceptions_adapter.py:6-22` (dead path,
but must import cleanly): classes `SpotifyDownloaderError`, `UserFriendlyError`,
`EncodingError`, `SpotifyAPIError`, `YouTubeMatchError`, `DownloadError`,
`MetadataError`, `FileOperationError`, `ConfigurationError`, `AuthenticationError`;
functions `create_error`, `format_warning`, `format_success`, `format_info`; dict
`ERROR_MESSAGES`.

## Steps

### Step 1 — create the package dirs and `__init__.py`

Create empty files:
- `src/shared/lib/__init__.py`  (content: `"""Shared library modules."""`)

### Step 2 — `src/shared/lib/utils.py`

Copy the **entire current contents** of `src/utils.py` (repo root) verbatim into
`src/shared/lib/utils.py`. Do not edit `src/utils.py`. Both files coexist for now
(dedup is deferred finding #13). Confirm the copy includes at minimum:
`sanitize_filename`, `validate_url`, `extract_playlist_id`, `clean_search_query`,
`format_duration`, `format_speed`, `get_file_extension`, `is_valid_audio_file`,
`get_duplicate_filename`.

### Step 3 — `src/shared/lib/cache.py`

```python
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
```

### Step 4 — `src/shared/lib/file_manager.py`

```python
"""Filesystem operations: playlist dirs, output paths, resume state, M3U."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from src.shared.lib.utils import (
    sanitize_filename,
    get_file_extension,
    is_valid_audio_file,
)

logger = logging.getLogger(__name__)


class FileManager:
    """Manages output directories, file paths, and resume state on disk."""

    def __init__(self, base_output_dir: str):
        self.base_output_dir = Path(base_output_dir)
        self.resume_dir = self.base_output_dir / ".resume_state"
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

    def create_playlist_directory(self, name: str) -> Path:
        safe_name = sanitize_filename(name)
        playlist_dir = self.base_output_dir / safe_name
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return playlist_dir

    def get_output_path(
        self,
        playlist_dir: Path,
        track_number: int,
        artist: str,
        title: str,
        fmt: str,
        filename_template: str,
    ) -> Path:
        safe_artist = sanitize_filename(artist)
        safe_title = sanitize_filename(title)
        try:
            stem = filename_template.format(
                track_number=track_number, artist=safe_artist, title=safe_title
            )
        except (KeyError, ValueError):
            stem = f"{track_number:02d} - {safe_artist} - {safe_title}"
        stem = sanitize_filename(stem)
        ext = get_file_extension(fmt)
        return playlist_dir / f"{stem}{ext}"

    def validate_file(self, path: Path) -> bool:
        return is_valid_audio_file(path)

    def delete_file(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"Failed to delete file {path}: {e}")

    def _resume_path(self, playlist_id: str) -> Path:
        return self.resume_dir / f"{playlist_id}.json"

    def save_resume_state(self, playlist_id: str, state: dict) -> None:
        try:
            self.resume_dir.mkdir(parents=True, exist_ok=True)
            with open(self._resume_path(playlist_id), "w", encoding="utf-8") as f:
                json.dump(state, f)
        except OSError as e:
            logger.warning(f"Failed to save resume state: {e}")

    def load_resume_state(self, playlist_id: str) -> Optional[dict]:
        path = self._resume_path(playlist_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load resume state: {e}")
            return None

    def delete_resume_state(self, playlist_id: str) -> None:
        path = self._resume_path(playlist_id)
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"Failed to delete resume state: {e}")

    def generate_m3u_playlist(
        self, playlist_dir: Path, name: str, track_files: List[Path]
    ) -> None:
        try:
            m3u_path = playlist_dir / f"{sanitize_filename(name)}.m3u"
            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for track_file in track_files:
                    f.write(f"{track_file.name}\n")
        except OSError as e:
            logger.warning(f"Failed to generate M3U playlist: {e}")
```

### Step 5 — `src/shared/lib/observers.py`

```python
"""Minimal observer pattern for progress events."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class ProgressSubject:
    """Subject that notifies attached observers of progress events."""

    def __init__(self):
        self._observers: List[Any] = []

    def attach(self, observer: Any) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Any) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: str, data: Optional[Any] = None) -> None:
        for observer in self._observers:
            observer.update(event, data)


class ConsoleObserver:
    """Prints progress events to the console."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def update(self, event: str, data: Optional[Any] = None) -> None:
        if self.verbose:
            print(f"[{event}] {data}" if data is not None else f"[{event}]")


class FileObserver:
    """Logs progress events to a file via the logging module."""

    def __init__(self, log_file):
        self.log_file = log_file
        self._logger = logging.getLogger("spotify_downloader.progress")

    def update(self, event: str, data: Optional[Any] = None) -> None:
        self._logger.info("%s %s", event, data if data is not None else "")
```

### Step 6 — `src/shared/lib/exceptions.py`

```python
"""Application exception hierarchy and user-facing message helpers."""

from __future__ import annotations

from typing import Optional


class SpotifyDownloaderError(Exception):
    """Base class for all application errors."""


class UserFriendlyError(SpotifyDownloaderError):
    """Error carrying a message safe to show the end user."""


class EncodingError(SpotifyDownloaderError):
    """Raised on text encoding/decoding problems."""


class SpotifyAPIError(SpotifyDownloaderError):
    """Raised on Spotify API failures."""


class YouTubeMatchError(SpotifyDownloaderError):
    """Raised when no acceptable YouTube match is found."""


class DownloadError(SpotifyDownloaderError):
    """Raised on download failures."""


class MetadataError(SpotifyDownloaderError):
    """Raised on metadata embedding failures."""


class FileOperationError(SpotifyDownloaderError):
    """Raised on filesystem operation failures."""


class ConfigurationError(SpotifyDownloaderError):
    """Raised on invalid or missing configuration."""


class AuthenticationError(SpotifyDownloaderError):
    """Raised on authentication failures."""


ERROR_MESSAGES = {
    "spotify_auth": "Spotify authentication failed. Check your credentials in .env.",
    "no_match": "No acceptable YouTube match was found for this track.",
    "download_failed": "Download failed. See the log for details.",
    "config_missing": "Configuration is missing or invalid.",
}


def create_error(key: str, default: str = "An error occurred.") -> UserFriendlyError:
    return UserFriendlyError(ERROR_MESSAGES.get(key, default))


def format_warning(message: str) -> str:
    return f"WARNING: {message}"


def format_success(message: str) -> str:
    return f"OK: {message}"


def format_info(message: str) -> str:
    return f"INFO: {message}"
```

## Files

- **In scope (create only):** `src/shared/lib/__init__.py`, `src/shared/lib/utils.py`,
  `src/shared/lib/cache.py`, `src/shared/lib/file_manager.py`,
  `src/shared/lib/observers.py`, `src/shared/lib/exceptions.py`.
- **Out of scope:** do NOT edit `src/utils.py`, any `src/features/*`, `src/legacy/*`,
  `providers.py`, or `cli.py`. This plan only adds the missing package; it changes no
  existing behavior beyond making imports resolve.

## Verification (from repo root)

1. Syntax:
```bash
python -m py_compile src/shared/lib/__init__.py src/shared/lib/utils.py src/shared/lib/cache.py src/shared/lib/file_manager.py src/shared/lib/observers.py src/shared/lib/exceptions.py
```
Expected: exit 0.

2. Pure-Python imports (no third-party deps needed):
```bash
python -c "from src.shared.lib import utils, cache, file_manager, observers, exceptions; print('lib OK')"
```
Expected: `lib OK`.

3. exceptions API surface matches the legacy adapter:
```bash
python -c "import src.legacy.exceptions_adapter as e; print('exceptions OK')"
```
Expected: `exceptions OK`.

4. Smoke-test FileManager + YouTubeCache behavior in a temp dir:
```bash
python -c "
import tempfile, pathlib
from src.shared.lib.file_manager import FileManager
from src.shared.lib.cache import YouTubeCache
d = tempfile.mkdtemp()
fm = FileManager(d)
pd = fm.create_playlist_directory('My: Playlist?')
assert pd.exists()
op = fm.get_output_path(pd, 3, 'Artist/Name', 'Title*', 'mp3', '{track_number:02d} - {artist} - {title}')
assert op.suffix == '.mp3' and '03 -' in op.name
fm.save_resume_state('pl1', {'completed_tracks': ['a']})
assert fm.load_resume_state('pl1')['completed_tracks'] == ['a']
fm.delete_resume_state('pl1'); assert fm.load_resume_state('pl1') is None
c = YouTubeCache(d, 86400)
c.set('tid', 'http://x'); assert c.get('tid') == 'http://x'
print('fm+cache OK')
"
```
Expected: `fm+cache OK`.

The full app import smoke (`python -c "import src.app.providers"`) needs third-party
deps (`dependency-injector`, `python-dotenv`) installed; that is exercised in plan 003,
not here.

## Done criteria

- All six files exist and `py_compile` passes.
- Verification commands 2, 3, 4 print their `OK` lines.
- No existing file was modified.

## Test plan

Plan 003 adds `tests/test_shared_lib.py` with real pytest cases for `utils`,
`FileManager`, and `YouTubeCache` (the inline smoke above is the seed for those tests).

## Maintenance note

These modules are now the canonical location. The root `src/utils.py` is a duplicate
(deferred #13) — when that cleanup happens, delete `src/utils.py` and repoint its
importers to `src.shared.lib.utils`. The `observers`/`exceptions` modules are currently
only referenced by dead/lazy paths; keep them minimal until something actually consumes
them.

## Escape hatch

If any call site expects a method **not** listed in the API contract above (e.g. a
`FileManager` method name this plan didn't define), STOP and report the exact
`file:line` rather than guessing the signature — a wrong guess silently breaks the
download path.
