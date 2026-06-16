# Plan 011 — Make the final download summary count skipped tracks

**Written against commit:** `e5867eb` (with plans 001–008 applied in the working tree, not yet committed)
**Finding:** #12 (MEDIUM) · **Effort:** M · **Risk:** Low · **Confidence:** Medium
**Depends on:** 001 + 002 + 003 (smoke baseline) · **Blocks:** nothing

## Why this matters

The authoritative per-run tally lives in `DownloadResult`
(`download_manager.py`): `successful`, `failed`, and `skipped` counters, incremented
by `add_success()` / `add_failure()` / `add_skip()`. But the on-screen final summary
(`display_final_summary`) is computed from a *parallel* set of counters on the
progress tracker (`total_completed`, `total_failed`) that are only bumped inside
`complete_track()`.

Skipped tracks never go through `complete_track()` — both the sequential and
concurrent download loops `continue` before any download begins
(`download_manager.py:230-232` and `262-264`), calling only `result.add_skip()`.
So **skipped tracks are invisible in the final summary**: it reports
`successful + failed` and silently omits the skipped count, and there is no
"skipped" line at all. On a resumed run (where most tracks are skipped) the summary
badly understates what happened.

> Confidence is Medium: the divergence is clear from the code, but the exact wiring
> of which progress-tracker class `cli.py` uses needs runtime confirmation (see
> Escape hatch). Verify before editing.

## Current state (exact)

Skip paths bump only `DownloadResult`, never the progress tracker
(`src/features/download/infrastructure/download_manager.py`):

```python
# sequential — line 229-232
        for i, track in enumerate(tracks, 1):
            if track.id in completed_track_ids:
                result.add_skip()
                continue
```
```python
# concurrent — line 261-264
            for i, track in enumerate(tracks, 1):
                if track.id in completed_track_ids:
                    result.add_skip()
                    continue
```

`DownloadResult` knows all three totals (`download_manager.py:50-53, 70-71`):

```python
        self.total_tracks = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
...
    def add_skip(self):
        """Increment skipped tracks."""
        self.skipped += 1
```

The summary is driven by the progress tracker's own counters, not by
`DownloadResult` (`src/shared/ui/progress.py:326-347`):

```python
    def display_final_summary(self) -> None:
        """Display final summary of all downloads."""
        total_elapsed = time.time() - self.start_time
        ...
        print(f"Total playlists processed: {self.current_playlist}/{self.total_playlists}")
        print(f"{self._colorize('[OK] Successfully downloaded:', Fore.GREEN)} {self.total_completed} tracks")
        if self.total_failed > 0:
            print(f"{self._colorize('[FAIL] Failed downloads:', Fore.RED)} {self.total_failed} tracks")
        print(f"⏱ Total time: {format_duration(int(total_elapsed))}")
        ...
```

It is called once, from `src/shared/ui/cli.py:433`:

```python
            self.progress_tracker.display_final_summary()
```

There are **two** classes in `progress.py` that define `display_final_summary`
(at line 326 and line 465). You must determine which one `cli.py`'s
`self.progress_tracker` actually is before editing (see Escape hatch).

## Steps

1. Identify the live progress-tracker class. In `cli.py`, find where
   `self.progress_tracker` is assigned (grep `progress_tracker =` and check the DI
   wiring in `src/app/providers.py`). Note which `progress.py` class it instantiates
   (the one at line ~326 or the one at line ~465). All edits below target **that**
   class; if both are reachable, apply the change to both.

2. Make `display_final_summary` accept the authoritative totals instead of relying
   on its internal side-counters. Change the signature to:

   ```python
   def display_final_summary(self, successful: int = None, failed: int = None, skipped: int = 0) -> None:
   ```

   At the top of the method, fall back to the existing counters when not supplied so
   the method stays backward-compatible:

   ```python
       successful = self.total_completed if successful is None else successful
       failed = self.total_failed if failed is None else failed
   ```

   Then print from `successful` / `failed`, and add a skipped line when `skipped > 0`:

   ```python
       print(f"{self._colorize('[OK] Successfully downloaded:', Fore.GREEN)} {successful} tracks")
       if failed > 0:
           print(f"{self._colorize('[FAIL] Failed downloads:', Fore.RED)} {failed} tracks")
       if skipped > 0:
           print(f"{self._colorize('[SKIP] Skipped (already downloaded):', Fore.YELLOW)} {skipped} tracks")
   ```

   Keep the existing average-time math keyed off `successful` (guard `if successful > 0`).

3. Thread the real totals from the caller. The download flow returns / holds a
   `DownloadResult` per playlist. At the `cli.py:433` call site, aggregate the
   `successful`/`failed`/`skipped` from the `DownloadResult`(s) produced during the
   run and pass them in:

   ```python
       self.progress_tracker.display_final_summary(
           successful=total.successful,
           failed=total.failed,
           skipped=total.skipped,
       )
   ```

   Where `total` is the run's aggregate `DownloadResult`. If the run processes
   multiple playlists, sum the per-playlist results into one accumulator first. Trace
   how `cli.py` currently obtains the `DownloadResult` (grep `DownloadResult` and the
   download-manager call in `cli.py`) and reuse that object — do not re-run anything.

4. Do **not** change `DownloadResult`'s counters or the download loops — they are
   already correct. This plan only fixes the *display* path.

## Files

- **In scope:** `src/shared/ui/progress.py`, `src/shared/ui/cli.py`.
- **Out of scope:** `src/features/download/infrastructure/download_manager.py`
  (counters are correct), `progress.py`'s per-playlist summary
  (`_print_playlist_summary`) unless both classes need the same fix.

## Verification (run from repo root)

```bash
python -m py_compile src/shared/ui/progress.py src/shared/ui/cli.py
```
Expected: exit 0, no output.

```bash
python -c "import inspect,sys; sys.path.insert(0,'.'); import src.shared.ui.progress as p; import re; src=open('src/shared/ui/progress.py',encoding='utf-8').read(); assert 'skipped' in src, 'no skipped handling added'; print('OK')"
```
Expected: `OK`.

Run the test suite (003 baseline must stay green):

```bash
python -m pytest -q
```
Expected: all tests pass / skip (no failures).

## Done criteria

- `display_final_summary` accepts `successful`/`failed`/`skipped` params with safe
  fallbacks and prints a skipped line when `skipped > 0`.
- `cli.py:433` call site passes the real `DownloadResult` totals.
- `py_compile` clean; `pytest` shows no new failures.

## Test plan

Add `tests/test_summary_totals.py` (AAA style, mirror `tests/test_shared_lib.py`):

- Instantiate the live progress-tracker class (the one identified in step 1).
- Capture stdout (`capsys` fixture) while calling
  `tracker.display_final_summary(successful=8, failed=1, skipped=3)`.
- Assert the captured output contains `8`, `1`, and a skipped line mentioning `3`.
- A second case: `display_final_summary()` with no args still runs (falls back to
  internal counters) and does not raise.

`pytest.importorskip("colorama")` and `importorskip("tqdm")` at the top if the
tracker imports them at construction.

## Maintenance note

The progress tracker should be treated as a *view* over `DownloadResult`, never a
second source of truth. If new outcome categories appear (e.g. "retried"), add them
to `DownloadResult` first and pass them into `display_final_summary` — do not grow a
parallel counter on the tracker.

## Escape hatch

- If step 1 shows `self.progress_tracker` is a class whose `total_completed` /
  `total_failed` are **already** fed from `DownloadResult` (i.e. no divergence
  exists in the live path), STOP and report — the finding may only apply to the
  unused second class, in which case the correct action is a one-line note, not a
  refactor.
- If `cli.py` does not retain a `DownloadResult` at the `display_final_summary` call
  site (e.g. the download manager prints its own summary and discards the result),
  STOP and report the call graph — threading the totals may require returning the
  result up through an intermediate method, which is a larger change than this plan
  scopes.
