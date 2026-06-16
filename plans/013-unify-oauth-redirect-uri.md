# Plan 013 — Unify the OAuth redirect_uri default

**Written against commit:** `e5867eb` (with plans 001–008 applied in the working tree, not yet committed)
**Finding:** #14 (MEDIUM) · **Effort:** S · **Risk:** Low · **Confidence:** Medium
**Depends on:** nothing (but pairs naturally with 012) · **Blocks:** nothing

## Why this matters

Spotify OAuth requires the `redirect_uri` sent during auth to exactly match one
registered in the Spotify app dashboard. This codebase ships **two different
defaults**, so whichever code path runs decides whether auth works:

- **Active path** defaults to `http://localhost:8888/callback`
  (`src/app/config.py:19`, `providers.py:281`, and the setup wizard writes the same
  at `wizard.py:251`).
- The live client constructor defaults to `http://127.0.0.1:9900/`
  (`src/features/spotify/infrastructure/spotify_client.py:33`), and the dead
  top-level module repeats `127.0.0.1:9900/` (`src/spotify_client.py:92`).

Today the DI container passes `config.spotify.redirect_uri` into the client
(`providers.py:30`, `providers.py:106`), so the `8888` value usually wins and the
`9900` default is dormant. But it is a latent footgun: any code that constructs the
client without an explicit `redirect_uri` (a test, a script, a future call site)
silently gets `9900` — which won't match what the wizard registered, and OAuth
fails with an opaque error. One default, used everywhere, removes the trap.

> Confidence Medium: the active path is already consistent; this hardens a latent
> mismatch rather than fixing a guaranteed live break. Sequence after plan 012 so the
> dead `src/spotify_client.py` is already gone and you only edit the live file.

## Current state (exact)

Canonical value, used by the active path:

```python
# src/app/config.py:19
    redirect_uri: str = "http://localhost:8888/callback"
```
```python
# src/app/providers.py:281
                "redirect_uri": os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
```
```python
# src/widgets/setup_wizard/wizard.py:251
        self.config['SPOTIPY_REDIRECT_URI'] = 'http://localhost:8888/callback'
```

Divergent default in the live client:

```python
# src/features/spotify/infrastructure/spotify_client.py:33
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:9900/"):
```

Divergent default in the dead module (removed by plan 012; if 012 has not run, see
Escape hatch):

```python
# src/spotify_client.py:92
                redirect_uri="http://127.0.0.1:9900/",
```

## Steps

1. In `src/features/spotify/infrastructure/spotify_client.py:33`, change the default
   parameter value from `"http://127.0.0.1:9900/"` to the canonical
   `"http://localhost:8888/callback"`:

   ```python
       def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8888/callback"):
   ```

   Do not change the parameter name, the body, or `self.redirect_uri = redirect_uri`
   (line 44) / its use at line 64 — only the default literal.

2. If plan 012 has **not** yet removed `src/spotify_client.py`, also update its
   hardcoded `redirect_uri="http://127.0.0.1:9900/"` (line 92) to the canonical
   value for consistency. If 012 already deleted that file, skip this step.

3. Leave the active path (`config.py`, `providers.py`, `wizard.py`) untouched — it
   is already canonical.

## Files

- **In scope:** `src/features/spotify/infrastructure/spotify_client.py` (and
  `src/spotify_client.py` only if it still exists).
- **Out of scope:** `src/app/config.py`, `src/app/providers.py`,
  `src/widgets/setup_wizard/wizard.py` — already correct, do not edit.

## Verification (run from repo root)

```bash
python -m py_compile src/features/spotify/infrastructure/spotify_client.py
```
Expected: exit 0, no output.

```bash
python -c "src=open('src/features/spotify/infrastructure/spotify_client.py',encoding='utf-8').read(); assert '9900' not in src, '9900 default still present'; assert 'http://localhost:8888/callback' in src, 'canonical redirect missing'; print('OK')"
```
Expected: `OK`.

Confirm only the canonical value remains anywhere (after 012):

```bash
grep -rn "9900" src/ || echo "no 9900 remains"
```
Expected: `no 9900 remains`.

## Done criteria

- `spotify_client.py` (live) default redirect_uri is `http://localhost:8888/callback`.
- No occurrence of `9900` under `src/` (assuming plan 012 removed the dead module;
  otherwise the dead module is also updated).
- `py_compile` clean.

## Test plan

Add to `tests/test_shared_lib.py` or a new `tests/test_spotify_client_default.py`:

- Import the live `SpotifyClient` class and inspect its `__init__` default via
  `inspect.signature(SpotifyClient.__init__).parameters['redirect_uri'].default`.
- Assert it equals `"http://localhost:8888/callback"`.

`pytest.importorskip("spotipy")` at the top — the client module imports spotipy.

## Maintenance note

The single source of truth for the redirect URI is `SPOTIPY_REDIRECT_URI` (env) →
`config.spotify.redirect_uri`. Constructor defaults exist only as a last-resort
fallback and must match the canonical value so a forgotten argument cannot silently
break OAuth. If the registered URI ever changes, update `config.py:19`,
`providers.py:281`, `wizard.py:251`, and this constructor default together.

## Escape hatch

- If the Spotify app these credentials belong to is actually registered with
  `http://127.0.0.1:9900/` (not `8888`), this plan would break the working path.
  Before changing the default, confirm the registered URI — check `.env` /
  `.env.example` for `SPOTIPY_REDIRECT_URI` and any README setup note. If the
  registered value is `9900`, STOP and report: the fix is then to make `8888` the
  outlier and standardize on `9900` instead (the direction is reversed, but the goal
  — one value everywhere — is the same).
