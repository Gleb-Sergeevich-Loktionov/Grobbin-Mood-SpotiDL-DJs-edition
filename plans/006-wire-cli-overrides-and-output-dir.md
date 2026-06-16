# Plan 006 — Wire CLI overrides and respect the configured output directory

**Written against commit:** `e5867eb`
**Findings:** #4 + #7 (HIGH) · **Effort:** M · **Risk:** Low
**Depends on:** 002 (app must import). Validate after 003's smoke test passes.

## Why this matters

Two related bugs:
- **#7:** the download directory is hardcoded. `providers.create_container` builds the
  config dict with `output_dir: "downloads"` and never reads `DEFAULT_OUTPUT_DIR` from
  the environment, so the folder a user picks in the setup wizard (saved to `.env`) is
  ignored.
- **#4:** `CLI.apply_cli_overrides()` is an empty `pass`. The flags `--output`,
  `--format`, `--quality`, `--concurrent`, `--resume`, `--skip-existing` are declared in
  `--help` but do nothing.

## Current state (exact)

`src/app/providers.py:289-301` (`create_container`, the `from_dict` defaults):
```python
        container.config.from_dict({
            "spotify": {
                "client_id": os.getenv("SPOTIPY_CLIENT_ID", ""),
                "client_secret": os.getenv("SPOTIPY_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
            },
            "download": {
                "output_dir": "downloads",
                "format": "mp3",
                "quality": "320",
                "max_retries": 3,
                "max_concurrent": 3
            },
```

`src/shared/ui/cli.py:285-289`:
```python
    def apply_cli_overrides(self, args: argparse.Namespace) -> None:
        """Apply command-line argument overrides to config."""
        # This would update the config object based on CLI args
        # Implementation depends on config structure
        pass
```

`DownloadManager.__init__` (`download_manager.py:107-127`) **snapshots** config into
`self.download_settings` (a dict) and holds `self.file_manager`. The container builds
`download_manager` before `CLI.run()` parses args, so overrides must update both the
config object *and* the already-constructed `download_manager`'s live state.

`FileManager.base_output_dir` (built in plan 002) is what
`create_playlist_directory` uses for the output location.

## Steps

### Step 1 — read output dir + audio settings from env at container build (#7)

In `src/app/providers.py`, inside `create_container`'s `from_dict` call, change the
`download` block to read environment variables (which `load_dotenv()` at module top
has already loaded from `.env`):

```python
            "download": {
                "output_dir": os.getenv("DEFAULT_OUTPUT_DIR", "downloads"),
                "format": os.getenv("DEFAULT_AUDIO_FORMAT", "mp3"),
                "quality": os.getenv("DEFAULT_AUDIO_QUALITY", "320"),
                "max_retries": int(os.getenv("RETRY_ATTEMPTS", "3")),
                "max_concurrent": int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
            },
```
(Env var names match exactly what the setup wizard writes — see `wizard.py:348-352`
and `.env.example`.)

### Step 2 — implement `apply_cli_overrides` (#4)

Replace the empty body in `src/shared/ui/cli.py` with:

```python
    def apply_cli_overrides(self, args: argparse.Namespace) -> None:
        """Apply command-line argument overrides to config and live components.

        The DI container builds config and the download manager before args are
        parsed, so overrides must update both the config object and the already-
        constructed download_manager's snapshotted settings.
        """
        cfg = self.config

        if args.output:
            cfg.download.output_dir = Path(args.output)
            if self.download_manager and getattr(self.download_manager, "file_manager", None):
                self.download_manager.file_manager.base_output_dir = Path(args.output)

        if args.format:
            cfg.download.format = args.format
            if self.download_manager:
                self.download_manager.download_settings['format'] = args.format

        if args.quality:
            cfg.download.quality = args.quality
            if self.download_manager:
                self.download_manager.download_settings['quality'] = args.quality

        if args.concurrent:
            cfg.download.max_concurrent = args.concurrent
            if self.download_manager:
                self.download_manager.download_settings['concurrent_downloads'] = args.concurrent
                self.download_manager.download_settings['max_concurrent'] = args.concurrent

        if args.skip_existing or args.resume:
            cfg.download.skip_existing = True
            if self.download_manager:
                self.download_manager.download_settings['skip_existing'] = True
```

`Path` is already imported at the top of `cli.py` (line 11). Do not add a duplicate import.

### Step 3 — leave call site as-is

`CLI.run()` already calls `self.apply_cli_overrides(args)` at line 115 before download.
No change needed there.

## Files

- **In scope:** `src/app/providers.py` (download config block), `src/shared/ui/cli.py`
  (`apply_cli_overrides` body).
- **Out of scope:** `download_manager.py` (do not refactor it to read config live —
  that is the larger maintenance item noted below), `app/config.py`, the wizard.

## Verification (from repo root)

```bash
python -m py_compile src/app/providers.py src/shared/ui/cli.py
```
Expected: exit 0.

Env-driven output dir is read:
```bash
DEFAULT_OUTPUT_DIR=/tmp/custommusic python -c "
import os
from src.app.providers import create_container  # needs deps installed
c = create_container()
ac = c.app_config()
assert str(ac.download.output_dir) == '/tmp/custommusic', ac.download.output_dir
print('outputdir OK')
" 2>/dev/null || echo "SKIP (third-party deps not installed)"
```
Expected: `outputdir OK` if deps installed, else `SKIP`.

`apply_cli_overrides` is no longer a stub:
```bash
python -c "s=open('src/shared/ui/cli.py').read(); body=s.split('def apply_cli_overrides')[1].split('def ')[0]; assert 'args.output' in body and 'download_settings' in body; print('overrides OK')"
```
Expected: `overrides OK`.

## Done criteria

- `providers.py` reads `DEFAULT_OUTPUT_DIR`/`DEFAULT_AUDIO_FORMAT`/`DEFAULT_AUDIO_QUALITY`/
  `MAX_CONCURRENT_DOWNLOADS`/`RETRY_ATTEMPTS` from env with the current values as defaults.
- `apply_cli_overrides` updates config + `download_manager` for output/format/quality/
  concurrent/skip_existing/resume.
- Both gates print their `OK` lines (or env one SKIPs without deps).

## Test plan

Add `tests/test_cli_overrides.py` (guard third-party deps with `importorskip`):
build a container, construct the CLI, call `apply_cli_overrides` with a fake
`argparse.Namespace`, assert `download_manager.download_settings['format']` changed and
`file_manager.base_output_dir` updated. Follow the AAA pattern from
`tests/test_shared_lib.py`.

## Maintenance note

The clean long-term fix is to parse CLI args **before** building the container and pass
overrides into `create_container`, so `download_manager` is constructed with final
values and `apply_cli_overrides` need not reach into its internals. That is a larger
refactor (touches `main.py` ordering) — deliberately out of scope here. Until then,
any new setting added to `DownloadManager.download_settings` must also be handled in
`apply_cli_overrides` if it has a CLI flag.

## Escape hatch

If `DownloadManager` no longer exposes `download_settings` (dict) or `file_manager`
(e.g. it was refactored to read config live), STOP and report — the override wiring
must target whatever the manager actually reads, and a stale reach-in would silently
no-op.
