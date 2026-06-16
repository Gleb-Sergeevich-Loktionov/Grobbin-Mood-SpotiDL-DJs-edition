# Plan 007 — Remove duplicate DI provider definitions

**Written against commit:** `e5867eb`
**Finding:** #9 (MED) · **Effort:** S · **Risk:** Low
**Depends on:** 002 (so the container can be smoke-tested afterward)

## Why this matters

`src/app/providers.py` defines `youtube_matcher` twice and `metadata_handler` twice.
In a `dependency_injector` `DeclarativeContainer`, the later class attribute silently
shadows the earlier one, so the first definitions are dead code that misleads readers
(and the two `youtube_matcher` definitions differ: `Factory` vs `Singleton`). Removing
the dead duplicates makes the container honest about what it actually builds.

## Current state (exact)

`src/app/providers.py`:
- First `youtube_matcher` (lines 140-144), a `Factory`:
  ```python
    # YouTube Matcher (обновленный путь)
    youtube_matcher = providers.Factory(
        "src.features.download.infrastructure.youtube_matcher.YouTubeMatcher",
        config=app_config
    )
  ```
- First `metadata_handler` (lines 151-155), a `Factory`:
  ```python
    # Metadata Handler (обновленный путь)
    metadata_handler = providers.Factory(
        "src.features.metadata.infrastructure.metadata_handler.MetadataHandler",
        config=app_config
    )
  ```
- Second `youtube_matcher` (lines 173-178), a `Singleton` — **this one wins**:
  ```python
    # YouTube Matcher
    # Конструктор принимает: config (AppConfig)
    youtube_matcher = providers.Singleton(
        "src.features.download.infrastructure.youtube_matcher.YouTubeMatcher",
        config=app_config
    )
  ```
- Second `metadata_handler` (lines 180-185), a `Singleton` — **this one wins**:
  ```python
    # Metadata Handler
    # Конструктор принимает: config (AppConfig)
    metadata_handler = providers.Singleton(
        "src.features.metadata.infrastructure.metadata_handler.MetadataHandler",
        config=app_config
    )
  ```

The second (Singleton) definitions are the effective ones. The first (Factory) ones are
dead.

## Decision

Keep the **Singleton** definitions (the effective current behavior — do not change
runtime behavior in this cleanup plan). Delete the earlier **Factory** duplicates and
their comment lines.

## Steps

1. In `src/app/providers.py`, delete the first `youtube_matcher` block (the `Factory`
   at lines ~140-144) including its `# YouTube Matcher (обновленный путь)` comment.
2. Delete the first `metadata_handler` block (the `Factory` at lines ~151-155) including
   its `# Metadata Handler (обновленный путь)` comment.
3. Leave the second (Singleton) `youtube_matcher` and `metadata_handler` definitions
   intact.
4. Do not touch any other provider (`youtube_cache`, `file_manager`, `progress_tracker`,
   etc.) or the `download_manager`/`cli` wiring.

## Files

- **In scope:** `src/app/providers.py` only.
- **Out of scope:** everything else.

## Verification (from repo root)

```bash
python -m py_compile src/app/providers.py
```
Expected: exit 0.

Exactly one definition of each remains:
```bash
python -c "
s = open('src/app/providers.py').read()
assert s.count('youtube_matcher = providers.') == 1, s.count('youtube_matcher = providers.')
assert s.count('metadata_handler = providers.') == 1, s.count('metadata_handler = providers.')
assert 'youtube_matcher = providers.Singleton' in s
assert 'metadata_handler = providers.Singleton' in s
print('dedupe OK')
"
```
Expected: `dedupe OK`.

Container still builds (if deps installed):
```bash
python -c "from src.app.providers import create_container; create_container().cli(); print('container OK')" 2>/dev/null || echo "SKIP (deps not installed)"
```
Expected: `container OK` or `SKIP`.

## Done criteria

- Exactly one `youtube_matcher = providers.` and one `metadata_handler = providers.`,
  both `Singleton`.
- `py_compile` passes; dedupe gate prints `dedupe OK`.

## Test plan

Covered by 003's `tests/test_import_smoke.py` (container builds). No new test required.

## Maintenance note

Watch for re-introduction of duplicates when editing this declarative container —
`dependency_injector` does not warn on shadowed attributes.

## Escape hatch

If the two definitions are NOT identical except for `Factory`/`Singleton` (e.g. they
pass different args), STOP and report — deleting one could change behavior beyond the
provider lifetime.
