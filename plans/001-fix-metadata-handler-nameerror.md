# Plan 001 — Fix `metadata_handler.py` NameError at import

**Written against commit:** `e5867eb`
**Finding:** #2 (CRITICAL) · **Effort:** S · **Risk:** Low
**Depends on:** nothing · **Blocks:** importing `download_manager` (and thus the whole app)

## Why this matters

`src/features/metadata/infrastructure/metadata_handler.py` annotates three method
parameters with the type `Track`, but only `SpotifyTrack` is imported. There is no
`from __future__ import annotations` at the top, so Python evaluates these
annotations when the class body executes — raising `NameError: name 'Track' is not
defined` the moment the module is imported. `download_manager.py:20` imports this
module at top level, so the error blocks the entire application from importing.

## Current state (exact)

Top of file — imports (lines 16-18):

```python
from src.features.spotify.domain.repositories import SpotifyTrack
from src.app.config import AppConfig
```

The three broken signatures:

```python
# line 86-91
def _embed_mp3_metadata(
    self,
    file_path: Path,
    track: Track,
    artwork_data: Optional[bytes]
) -> bool:
```
```python
# line 138-143
def _embed_m4a_metadata(
    self,
    file_path: Path,
    track: Track,
    artwork_data: Optional[bytes]
) -> bool:
```
```python
# line 176-181
def _embed_flac_metadata(
    self,
    file_path: Path,
    track: Track,
    artwork_data: Optional[bytes]
) -> bool:
```

The public method `embed_metadata` (line 42-47) already correctly annotates
`track: SpotifyTrack`. The three private helpers are called from it with the same
object, so the correct type is `SpotifyTrack`.

## Steps

1. Add `from __future__ import annotations` as the **first** import line of the file
   (immediately after the module docstring, before `import requests`). This makes all
   annotations lazy strings and is the project-safe fix; it also prevents this class
   of error recurring.
2. Additionally, correct the three `track: Track` annotations to `track: SpotifyTrack`
   so the annotation names a real, imported type. Replace all three occurrences.

   Use a targeted replace of the exact string `        track: Track,` (8-space indent,
   3 occurrences) → `        track: SpotifyTrack,`.

3. Do **not** change any method bodies, logic, or other annotations.

## Files

- **In scope:** `src/features/metadata/infrastructure/metadata_handler.py` only.
- **Out of scope:** everything else. Do not touch the settings-key mismatch
  (`embed_artwork` vs `download_artwork`) in this plan — that is deferred finding #10.

## Verification (run from repo root)

```bash
python -m py_compile src/features/metadata/infrastructure/metadata_handler.py
```
Expected: exit code 0, no output.

```bash
python -c "import ast,sys; src=open('src/features/metadata/infrastructure/metadata_handler.py').read(); assert 'from __future__ import annotations' in src; assert 'track: Track,' not in src; assert src.count('track: SpotifyTrack,') >= 3; print('OK')"
```
Expected: `OK`.

A full `import` smoke test (`python -c "import src.features.metadata.infrastructure.metadata_handler"`)
will still fail until plan 002 lands (it transitively needs `src.shared.lib`). That is
expected — do not try to fix it here.

## Done criteria

- `from __future__ import annotations` present as first import.
- Zero occurrences of `track: Track,` remain; ≥3 occurrences of `track: SpotifyTrack,`.
- `py_compile` passes.

## Test plan

No unit test for this trivial fix; the `py_compile` + grep assertions above are the
gate. Plan 003 adds the real import smoke test that will cover this module once 002
lands.

## Maintenance note

Keeping `from __future__ import annotations` means future annotations can reference
types defined later or behind `TYPE_CHECKING` without runtime cost. Reviewers: watch
that no code does `isinstance(x, SomeAnnotation)` relying on a runtime annotation
object.

## Escape hatch

If you discover `_embed_*` methods are actually called somewhere with the legacy
`src.legacy.spotify_adapter.Track` (not `SpotifyTrack`) and rely on attributes
`SpotifyTrack` lacks, STOP and report — the type unification may need the `__future__`
import only (leaving names as-is) rather than renaming. (Both legacy `Track` and
`SpotifyTrack` expose `.name/.album/.album_artist/.track_number/.release_date/.genres/
.get_all_artists_string()`, so renaming is expected to be safe.)
