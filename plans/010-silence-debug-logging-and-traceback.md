# Plan 010 — Demote DEBUG log noise & gate the traceback dump

**Written against commit:** `e5867eb` (with plans 001–008 applied in the working tree, not yet committed)
**Finding:** #11 (LOW/DX) · **Effort:** S · **Risk:** Low · **Confidence:** High
**Depends on:** 001 + 002 (modules must import) · **Blocks:** nothing

## Why this matters

Six log statements in `download_manager.py` are written at `INFO` level with a
hand-rolled `[DEBUG]` prefix. On a normal run these spam the user's console with
internal path-plumbing detail that belongs at `DEBUG`. Separately, `main()` in
`cli.py` catches every exception and unconditionally calls
`traceback.print_exc()`, dumping a raw Python stack trace to stdout for *any*
failure — including ordinary user-facing ones (bad URL, missing credentials). That
is hostile UX and leaks internal structure.

Two other `except Exception:` blocks are **intentional** and must be left alone:
`cli.py:26` (UTF-8 console setup fallback) and
`metadata_handler.py:101` (`audio.add_tags()` "tags already exist"). Do not touch them.

## Current state (exact)

`src/features/download/infrastructure/download_manager.py` — six INFO-level lines
carrying a `[DEBUG]` prefix (lines 163, 164, 329, 340, 341, 364):

```python
            logger.info(f"[DEBUG] Playlist directory created/retrieved: {playlist_dir}")
            logger.info(f"[DEBUG] Playlist directory exists: {playlist_dir.exists()}")
...
            logger.info(f"[DEBUG] Received playlist_dir for track: {playlist_dir}")
...
            logger.info(f"[DEBUG] Generated output_path: {output_path}")
            logger.info(f"[DEBUG] Output path parent directory: {output_path.parent}")
...
            logger.info(f"[DEBUG] Final output_path before yt-dlp: {output_path}")
```

`src/shared/ui/cli.py` — unconditional stack dump in `main()` (lines 544-548):

```python
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
```

## Steps

1. In `download_manager.py`, convert all six lines from `logger.info(f"[DEBUG] ...")`
   to `logger.debug(f"...")` — i.e. change the method to `debug` **and** strip the
   now-redundant `[DEBUG] ` text from the message. Example:

   ```python
   # before
   logger.info(f"[DEBUG] Playlist directory created/retrieved: {playlist_dir}")
   # after
   logger.debug(f"Playlist directory created/retrieved: {playlist_dir}")
   ```

   Apply the same transform to all six. Do not change the interpolated values.

2. In `cli.py` `main()`, gate the full traceback behind the logger's effective
   level so it only appears when the user opted into DEBUG logging. Replace the
   except block (lines 544-548) with:

   ```python
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logging.getLogger(__name__).debug("Critical error traceback", exc_info=True)
        return 1
   ```

   This logs the full traceback through the logging system at DEBUG (so `-v`/DEBUG
   runs still capture it, routed wherever logging is configured) while a normal run
   shows only the concise one-line message. Confirm `import logging` is already at
   the top of `cli.py`; if not, add it with the other stdlib imports.

3. Do **not** modify `cli.py:26` or `metadata_handler.py:101` — both `except ...: pass`
   blocks are intentional and correct.

## Files

- **In scope:** `src/features/download/infrastructure/download_manager.py`,
  `src/shared/ui/cli.py`.
- **Out of scope:** every other `except`/`logger` site. Do not do a repo-wide
  logging refactor.

## Verification (run from repo root)

```bash
python -m py_compile src/features/download/infrastructure/download_manager.py src/shared/ui/cli.py
```
Expected: exit 0, no output.

```bash
python -c "src=open('src/features/download/infrastructure/download_manager.py',encoding='utf-8').read(); assert '[DEBUG]' not in src, 'stale [DEBUG] prefix remains'; print('OK dm')"
python -c "src=open('src/shared/ui/cli.py',encoding='utf-8').read(); assert 'traceback.print_exc()' not in src, 'traceback dump still present'; print('OK cli')"
```
Expected: `OK dm` then `OK cli`.

## Done criteria

- Zero `[DEBUG]` substrings in `download_manager.py`.
- Zero `traceback.print_exc()` in `cli.py`.
- Both files `py_compile` clean.
- `cli.py:26` and `metadata_handler.py:101` unchanged.

## Test plan

No new unit test — this is logging hygiene. The grep assertions above are the gate.
If `tests/test_import_smoke.py` already builds the container, it implicitly covers
that the edited modules still import.

## Maintenance note

Project convention going forward: use `logger.debug()` for plumbing detail, never an
`[DEBUG]` text prefix on an `INFO` line. User-facing failures print a short message;
full tracebacks go through `logger.debug(..., exc_info=True)` so they surface only
under verbose/DEBUG configuration.

## Escape hatch

If logging is **not** configured anywhere (no `logging.basicConfig`/handler) then
`logger.debug(..., exc_info=True)` could vanish silently, losing the trace entirely.
Grep for `basicConfig`/`setup_logging` in `cli.py` first. If no handler is ever
attached, STOP and report — the gate should instead key off the parsed
`args.verbose` flag (print the traceback only when `args.verbose` is set) rather
than the logging level.
