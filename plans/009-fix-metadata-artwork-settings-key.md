# Plan 009 — Fix dead artwork toggle (settings-key mismatch)

**Written against commit:** `e5867eb` (with plans 001–008 applied in the working tree, not yet committed)
**Finding:** #10 (HIGH) · **Effort:** S · **Risk:** Low · **Confidence:** High
**Depends on:** 001 + 002 (module must import) · **Blocks:** nothing

## Why this matters

`MetadataHandler.__init__` builds a `self.settings` dict keyed by the real config
field name `download_artwork`, but the only place that *reads* the artwork toggle
looks up a key named `embed_artwork`, which is never written. `dict.get('embed_artwork', True)`
therefore always returns its default `True`. Net effect: the user's
`download_artwork=False` setting is silently ignored — album artwork is always
downloaded and embedded regardless of configuration. The `__repr__` has the same
typo and always prints `None`.

The canonical config field is `download_artwork` (`src/app/config.py:54`,
`download_artwork: bool = True`), wired through `providers.py:57`
(`download_artwork=config.metadata.download_artwork`) and the inline default at
`providers.py:299` (`"download_artwork": True`). There is no `embed_artwork` field
anywhere in config — so `download_artwork` is the single source of truth and the
read sites are simply using the wrong key.

## Current state (exact)

`src/features/metadata/infrastructure/metadata_handler.py`

Settings dict is built with key `download_artwork` (lines 36-40):

```python
self.settings = {
    'download_artwork': config.metadata.download_artwork,
    'embed_lyrics': config.metadata.embed_lyrics,
    'preserve_original': config.metadata.preserve_original
}
```

But the toggle is read under the wrong key (line 68):

```python
            if self.settings.get('embed_artwork', True) and artwork_url:
                artwork_data = self.download_artwork(artwork_url)
```

And the repr repeats the typo (line 416):

```python
        return f"MetadataHandler(embed_artwork={self.settings.get('embed_artwork')})"
```

## Steps

1. Line 68 — change the lookup key from `embed_artwork` to `download_artwork`:

   Replace `self.settings.get('embed_artwork', True)` → `self.settings.get('download_artwork', True)`.

2. Line 416 — fix the repr to read the real key. Replace the whole return line with:

   ```python
        return f"MetadataHandler(download_artwork={self.settings.get('download_artwork')})"
   ```

3. Do **not** rename the config field, do **not** add an `embed_artwork` key, do
   **not** touch `embed_lyrics`/`preserve_original`, and do **not** change any
   method bodies beyond these two string lookups.

## Files

- **In scope:** `src/features/metadata/infrastructure/metadata_handler.py` only.
- **Out of scope:** `src/app/config.py`, `src/app/providers.py`,
  `src/features/download/infrastructure/download_manager.py` (its own
  `download_artwork`/`embed_lyrics` settings dict at lines 118-119 is correct —
  leave it).

## Verification (run from repo root)

```bash
python -m py_compile src/features/metadata/infrastructure/metadata_handler.py
```
Expected: exit code 0, no output.

```bash
python -c "src=open('src/features/metadata/infrastructure/metadata_handler.py',encoding='utf-8').read(); assert \"get('embed_artwork'\" not in src, 'stale embed_artwork key still present'; assert src.count(\"get('download_artwork'\") >= 2, 'download_artwork not read twice'; print('OK')"
```
Expected: `OK`.

## Done criteria

- Zero occurrences of the string `get('embed_artwork'` in the file.
- At least 2 occurrences of `get('download_artwork'` (line 68 read + line 416 repr).
- `py_compile` passes.

## Test plan

Add a focused unit test in `tests/test_metadata_settings.py` (follow the AAA style
of `tests/test_shared_lib.py`):

- Build a fake config object with `metadata.download_artwork = False`,
  `metadata.embed_lyrics = False`, `metadata.preserve_original = False`
  (a `types.SimpleNamespace` is enough; `MetadataHandler.__init__` only reads those
  three attributes plus `config` itself).
- Construct `MetadataHandler(fake_config)` and assert
  `handler.settings['download_artwork'] is False`.
- Assert the toggle is now honored: with `download_artwork=False`, the value the
  guard at line 68 reads is `handler.settings.get('download_artwork', True) is False`.
  (Before this fix the guard read the missing `embed_artwork` key and got `True`.)

`pytest.importorskip("mutagen")` and `importorskip("PIL")` at the top so the test
skips cleanly if those optional deps are absent.

## Maintenance note

If a future change really does need to separate "download artwork" from "embed
artwork" (two stages), add an explicit `embed_artwork` field to
`MetadataConfig` in `src/app/config.py` and wire it through `providers.py` and the
`self.settings` dict — do not reintroduce a bare-string key that no field backs.

## Escape hatch

If you find that `config.metadata` exposes a real `embed_artwork` attribute
(grep `embed_artwork` across `src/app/config.py`) that this code was meant to read,
STOP and report — the correct fix would then be to add `'embed_artwork'` to the
`self.settings` dict, not to repoint the lookup. As of commit `e5867eb` no such
field exists, so repointing to `download_artwork` is correct.
