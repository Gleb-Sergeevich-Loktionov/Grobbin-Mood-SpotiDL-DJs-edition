# Plan 012 — Remove dead top-level modules `src/config.py` & `src/spotify_client.py`

**Written against commit:** `e5867eb` (with plans 001–008 applied in the working tree, not yet committed)
**Finding:** #13 (LOW/tech-debt) · **Effort:** S · **Risk:** Medium (deletion) · **Confidence:** High
**Depends on:** nothing · **Blocks:** nothing

## Why this matters

The repo carries a parallel "old" stack at the top of `src/` that predates the
current feature-sliced architecture: `src/config.py` and `src/spotify_client.py`.
The live app loads configuration via `src/app/config.py` and talks to Spotify via
`src/features/spotify/infrastructure/spotify_client.py` + the wired
`src/legacy/spotify_adapter.py`. The two top-level modules are dead weight: they
confuse navigation (two `config.py`, two `spotify_client.py`), and
`src/spotify_client.py:92` hardcodes the wrong OAuth redirect (`127.0.0.1:9900/`),
making it a trap for anyone who edits the wrong file (see finding #14 / plan 013).

**Import-graph evidence (commit `e5867eb`):** a repo-wide grep for
`from src.config`, `import src.config`, `from src import config`,
`src.spotify_client`, and `from src.spotify_client` returns **zero matches**.
Nothing imports either module.

> **Correction to the prior session's deferred note:** that note grouped
> `src/legacy/*` in with this dead stack. That is wrong — `src/legacy/` is **alive**.
> `src/app/providers.py:122-123` wires
> `legacy_spotify_client = Singleton("src.legacy.spotify_adapter.SpotifyClient")`,
> the download manager uses it (`providers.py:179`), and `cli.py:398-402`
> authenticates it. **Do not delete anything under `src/legacy/` in this plan.**

## Current state (exact)

Two unreferenced top-level modules:

- `src/config.py` — old config loader. Has its own `get_spotify_redirect_uri()`
  (line 251) and `embed_artwork` default (line 112); none of it is imported.
- `src/spotify_client.py` — old Spotify client. `except Exception:` at line 421,
  hardcoded `redirect_uri="http://127.0.0.1:9900/"` at line 92.

Active equivalents that stay:

- `src/app/config.py` (live config + `AppConfig`)
- `src/features/spotify/infrastructure/spotify_client.py` (live client)
- `src/legacy/spotify_adapter.py` (live adapter, DI-wired)

## Steps

1. **Re-confirm dead before deleting** (do not skip — the import grep is necessary
   but not sufficient). From repo root run each and confirm empty output:

   ```bash
   grep -rn --include='*.py' -E "from src\.config|import src\.config|from src import config" . || echo "clean: src.config"
   grep -rn --include='*.py' -E "src\.spotify_client|from src\.spotify_client|import spotify_client" . || echo "clean: src.spotify_client"
   ```

2. Check for **non-import** references that a grep on import statements would miss:
   - direct-run / entry points: `grep -rn "spotify_client\|config.py" *.md setup.py setup.cfg pyproject.toml 2>/dev/null` and skim the README for `python src/config.py`-style invocations.
   - dynamic imports: `grep -rn "importlib\|__import__" src/` and confirm none name these modules.
   - test references: `grep -rn "spotify_client\|src.config" tests/`.

   If **any** real reference is found, STOP (see Escape hatch).

3. If steps 1–2 are clean, delete exactly two files:
   - `src/config.py`
   - `src/spotify_client.py`

   Also remove their compiled artifacts if present (`src/__pycache__/config.*.pyc`,
   `src/__pycache__/spotify_client.*.pyc`).

4. Do **not** touch `src/legacy/`, `src/app/`, or `src/features/`.

## Files

- **In scope (delete):** `src/config.py`, `src/spotify_client.py`.
- **Out of scope (keep):** `src/app/config.py`,
  `src/features/spotify/infrastructure/spotify_client.py`, all of `src/legacy/`,
  everything else.

## Verification (run from repo root)

```bash
test ! -f src/config.py && test ! -f src/spotify_client.py && echo "deleted OK"
```
Expected: `deleted OK`.

The app must still import and the smoke test must still pass (proves nothing
depended on the deleted modules):

```bash
python -m pytest -q
```
Expected: same pass/skip result as before deletion — no new failures, no
`ModuleNotFoundError`.

```bash
python -c "from src.app.providers import create_container; print('container import OK')"
```
Expected: `container import OK` (or a clean skip if optional deps are missing —
but **not** a `ModuleNotFoundError: src.config`/`src.spotify_client`).

## Done criteria

- `src/config.py` and `src/spotify_client.py` no longer exist.
- `pytest` result unchanged from pre-deletion baseline.
- No `ModuleNotFoundError` referencing the deleted modules.

## Test plan

No new test. The existing import smoke test (`tests/test_import_smoke.py`, plan 003)
is the regression guard: if anything secretly depended on the deleted modules, the
container build will fail. Run it before and after to compare.

## Maintenance note

After this, there is exactly one `config` module (`src/app/config.py`) and the
Spotify client lives only under `src/features/...` + `src/legacy/`. If you later
find more orphaned top-level modules, confirm with the same import-graph grep before
removing — `src/legacy/` is intentionally retained for the adapter layer.

## Escape hatch

- If step 1 or 2 surfaces **any** importer, entry-point, doc invocation, or test
  that names `src/config.py` or `src/spotify_client.py`, STOP and report it. Deletion
  is only safe because the import graph is empty; a single live reference invalidates
  this plan.
- If `git log --oneline -- src/config.py src/spotify_client.py` shows these files
  were added very recently / deliberately (not legacy scaffold), STOP and report —
  they may be work-in-progress rather than dead code.
