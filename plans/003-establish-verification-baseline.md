# Plan 003 — Establish a verification baseline (pytest + fix .gitignore)

**Written against commit:** `e5867eb`
**Finding:** #3 (HIGH) · **Effort:** M · **Risk:** Low
**Depends on:** 001 and 002 (need the app importable for the smoke test)
**Blocks:** safe execution/review of 004, 006

## Why this matters

There are zero tests (`tests/` contains only `__init__.py`), `pytest` is commented out
in `requirements.txt`, and — critically — `.gitignore:95` contains `test_*.py`, which
**git-ignores every standard pytest test file at any path**. Any test the executor of a
later plan writes as `test_*.py` will be silently untracked. There is no command that
proves the app even imports. This plan creates a real, runnable safety net.

## Current state (exact)

`.gitignore` lines 93-96:
```
count_tracks.py
cleanup_*.py
test_*.py
test_*.txt
```

`requirements.txt` lines 40-45:
```
# Development Dependencies (optional, install with: pip install -r requirements-dev.txt)
# pytest>=7.4.0
# pytest-cov>=4.1.0
# black>=23.0.0
# flake8>=6.0.0
# mypy>=1.5.0
```

`tests/__init__.py` exists; no other test files.

## Steps

### Step 1 — stop git-ignoring test files

Edit `.gitignore`: change line `test_*.py` to scope it to the repo root only, so it
keeps ignoring stray root-level scratch scripts but allows `tests/test_*.py`:

Replace:
```
test_*.py
test_*.txt
```
with:
```
/test_*.py
/test_*.txt
```
(The leading `/` anchors the pattern to the repo root. `tests/test_foo.py` is no longer
ignored.)

### Step 2 — create `requirements-dev.txt`

The comment references a file that does not exist. Create `requirements-dev.txt` at repo
root:
```
-r requirements.txt
pytest>=7.4.0
pytest-cov>=4.1.0
```

### Step 3 — pytest config

Create `pytest.ini` at repo root:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

### Step 4 — unit tests for pure utilities (no third-party deps)

Create `tests/test_shared_lib.py`. These exercise plan 002's modules and need no
network or external packages:
```python
"""Unit tests for src.shared.lib pure-Python utilities."""

import tempfile
from pathlib import Path

from src.shared.lib import utils
from src.shared.lib.file_manager import FileManager
from src.shared.lib.cache import YouTubeCache


def test_validate_url_accepts_spotify_playlist():
    assert utils.validate_url("https://open.spotify.com/playlist/abc123")


def test_validate_url_rejects_garbage():
    assert not utils.validate_url("not a url")


def test_extract_playlist_id():
    url = "https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS?si=x"
    assert utils.extract_playlist_id(url) == "7ooZ1OdYCD6wibrLAfrgXS"


def test_sanitize_filename_strips_invalid_chars():
    assert ":" not in utils.sanitize_filename("a:b/c?")


def test_format_duration():
    assert utils.format_duration(65) == "1m 5s"


def test_file_manager_roundtrip():
    d = tempfile.mkdtemp()
    fm = FileManager(d)
    pd = fm.create_playlist_directory("My: Playlist?")
    assert pd.exists()
    op = fm.get_output_path(pd, 3, "Artist", "Title", "mp3",
                            "{track_number:02d} - {artist} - {title}")
    assert op.suffix == ".mp3"
    assert op.name.startswith("03 -")


def test_resume_state_roundtrip():
    fm = FileManager(tempfile.mkdtemp())
    fm.save_resume_state("pl", {"completed_tracks": ["a", "b"]})
    assert fm.load_resume_state("pl")["completed_tracks"] == ["a", "b"]
    fm.delete_resume_state("pl")
    assert fm.load_resume_state("pl") is None


def test_youtube_cache_set_get():
    c = YouTubeCache(tempfile.mkdtemp(), 86400)
    c.set("track-id", "https://youtube.com/watch?v=x")
    assert c.get("track-id") == "https://youtube.com/watch?v=x"


def test_youtube_cache_missing_key_returns_none():
    c = YouTubeCache(tempfile.mkdtemp(), 86400)
    assert c.get("nope") is None
```

### Step 5 — import smoke test (guarded on optional deps)

Create `tests/test_import_smoke.py`. This proves the container builds once
third-party deps are installed, and **skips cleanly** when they are not, so the suite
stays green in a bare environment:
```python
"""Smoke test: the DI container builds and the CLI object is constructible."""

import pytest


def test_container_builds():
    pytest.importorskip("dependency_injector")
    pytest.importorskip("dotenv")
    pytest.importorskip("spotipy")
    pytest.importorskip("yt_dlp")
    pytest.importorskip("tenacity")
    from src.app.providers import create_container
    container = create_container()
    cli = container.cli()  # builds download_manager -> imports shared.lib + metadata
    assert cli is not None
```

## Files

- **In scope:** `.gitignore` (1 edit), `requirements-dev.txt` (new), `pytest.ini` (new),
  `tests/test_shared_lib.py` (new), `tests/test_import_smoke.py` (new).
- **Out of scope:** do not modify `src/` or `requirements.txt`.

## Verification (from repo root)

```bash
python -m pytest tests/test_shared_lib.py -q
```
Expected: all tests pass (8 passed). Requires only the standard library + plan 002.

```bash
python -c "import pathlib,re; gi=open('.gitignore').read(); assert '/test_*.py' in gi and '\ntest_*.py' not in gi; print('gitignore OK')"
```
Expected: `gitignore OK`.

```bash
python -m pytest tests/test_import_smoke.py -q
```
Expected: `1 passed` if deps installed, else `1 skipped`. Either is acceptable — a
failure (not skip/pass) means the container is still broken; investigate plans 001/002.

If you can install deps in this worktree (allowed — disposable), run
`python -m pip install -r requirements-dev.txt` then re-run the smoke test; a green
import smoke is the strongest signal the app is revived.

## Done criteria

- `tests/test_shared_lib.py` passes (8 passed).
- `.gitignore` anchors `/test_*.py` (no longer ignores `tests/test_*.py`).
- `requirements-dev.txt` and `pytest.ini` exist.
- import smoke either passes or skips (never fails).

## Test plan

This plan *is* the test plan. Later plans extend `tests/` following these as the
pattern (AAA structure, `pytest.importorskip` for optional deps).

## Maintenance note

CI (if added later) should run `pip install -r requirements-dev.txt && pytest`. Watch
that nobody re-adds an unanchored `test_*.py` to `.gitignore`.

## Escape hatch

If `tests/test_shared_lib.py` fails on import of `src.shared.lib`, plan 002 is
incomplete or wrong — STOP and report rather than weakening the tests to pass.
