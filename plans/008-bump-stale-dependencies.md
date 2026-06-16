# Plan 008 — Bump stale, breakage-prone dependencies

**Written against commit:** `e5867eb`
**Finding:** #8 (MED) · **Effort:** S · **Risk:** Med (API drift)
**Depends on:** nothing (independent)

## Why this matters

- `yt-dlp==2023.10.13` is pinned to a >2-year-old release. YouTube changes its
  extraction surface constantly; this version fails on current YouTube. The README
  itself instructs users to run `--update` to work around it. The download path is
  dead without a current `yt-dlp`.
- `requests==2.31.0` predates the fix for CVE-2024-35195 (released in `requests` 2.32.0,
  where a `Session` could skip certificate verification on the first request after a
  `verify=False` request). Low severity here but free to fix.

## Current state (exact)

`requirements.txt`:
```
# YouTube Download
yt-dlp==2023.10.13
```
```
# HTTP Requests
requests==2.31.0
```

## Decision

`yt-dlp` should not be hard-pinned to a single old release — its whole value is tracking
YouTube. Use a recent floor with no upper cap so `--update`/reinstall pulls fixes.
`requests` gets a safe minor floor.

## Steps

1. In `requirements.txt`, change:
   ```
   yt-dlp==2023.10.13
   ```
   to:
   ```
   yt-dlp>=2024.8.0
   ```

2. Change:
   ```
   requests==2.31.0
   ```
   to:
   ```
   requests>=2.32.2,<3
   ```

3. Change nothing else in `requirements.txt` (leave the other pins as-is — they are not
   part of this finding).

## Files

- **In scope:** `requirements.txt` (two lines).
- **Out of scope:** `setup.py`, `requirements-dev.txt`, source code.

## Verification (from repo root)

```bash
python -c "
reqs = open('requirements.txt').read()
assert 'yt-dlp==2023.10.13' not in reqs
assert 'yt-dlp>=2024.8.0' in reqs
assert 'requests==2.31.0' not in reqs
assert 'requests>=2.32.2,<3' in reqs
print('requirements OK')
"
```
Expected: `requirements OK`.

Resolvability check (allowed in the disposable worktree; needs network). Use a dry run
so nothing is actually installed into the environment:
```bash
python -m pip install --dry-run -r requirements.txt 2>&1 | tail -5 || echo "SKIP (no network or pip --dry-run unsupported)"
```
Expected: pip resolves both packages, or a clean SKIP if offline. A resolution
**conflict** (not a network error) means a version floor is wrong — see escape hatch.

## Done criteria

- `requirements.txt` shows `yt-dlp>=2024.8.0` and `requests>=2.32.2,<3`.
- Requirements gate prints `requirements OK`.
- pip dry-run resolves (or SKIPs on no network) — no dependency conflict.

## Test plan

No unit test (dependency manifest change). The pip dry-run is the gate. After this
lands, a manual end-to-end download is the real proof yt-dlp works against current
YouTube — note this in the PR for the maintainer to run.

## Maintenance note

`yt-dlp` will need periodic bumps; the unbounded floor lets users `pip install -U yt-dlp`
without editing the manifest. Consider a CI job or scheduled reminder to refresh the
floor a few times a year. If a future `yt-dlp` ever breaks the `ydl_opts` used in
`download_manager._download_with_ytdlp` / `youtube_matcher._search_with_ytdlp`
(e.g. `extractor_args` schema changes), those call sites need updating — out of scope here.

## Escape hatch

If `pip install --dry-run` reports a version-resolution conflict (e.g. `yt-dlp>=2024.8.0`
does not exist for the target Python, or `requests>=2.32.2` conflicts with another pin),
STOP and report the exact pip error rather than loosening floors blindly. Do not remove
the version constraints entirely.
