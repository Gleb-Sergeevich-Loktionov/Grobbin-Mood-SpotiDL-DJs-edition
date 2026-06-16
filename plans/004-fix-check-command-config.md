# Plan 004 — Fix the `--check` command's config loading

**Written against commit:** `e5867eb`
**Finding:** #5 (HIGH) · **Effort:** S · **Risk:** Low
**Depends on:** 002 (app must import). Validate with the 003 harness.

## Why this matters

`python main.py --check` is the diagnostic command, yet it reliably errors with
`SpotifyConfig.__init__() missing 2 required positional arguments: 'client_id' and
'client_secret'` even when `.env` is correct. Root cause: `--check` calls
`src.app.config.load_config()`, which tries `config/default_config.yaml` **first**.
That YAML has no `spotify:` section, so `SpotifyConfig(**{})` is constructed with no
arguments — and `SpotifyConfig` requires `client_id`/`client_secret`. The `.env`
credentials are never consulted on that path.

## Current state (exact)

`src/shared/ui/cli.py:446-457` (`check_configuration`):
```python
            try:
                from src.app.config import load_config
                config = load_config()

                if config.spotify.client_id and config.spotify.client_secret:
                    print(f"{Fore.GREEN}✓ Spotify credentials настроены{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}✗ Spotify credentials не найдены{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Запустите: python main.py --setup{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")
```

`src/app/config.py:206-231` (`load_config`) prefers `config/default_config.yaml`
(which lacks `spotify:`) over `.env`. `AppConfig.from_yaml` (line 99-107) does
`SpotifyConfig(**data.get('spotify', {}))` → empty dict → TypeError.

`SpotifyConfig` (config.py:14-19) has required `client_id`, `client_secret`.

The container's own happy path (`providers.py:289-294`) reads creds from env vars
`SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` — that is the source of truth the
setup wizard writes to `.env`.

## Fix approach

`--check` should validate the **same** credential source the real run uses: the
environment (loaded from `.env` by `load_dotenv()`), not the YAML. Make
`check_configuration` read credentials from env directly instead of via
`load_config()`.

## Steps

1. In `src/shared/ui/cli.py`, inside `check_configuration`, replace the
   `from src.app.config import load_config` / `config = load_config()` block with a
   direct env read that mirrors `providers.create_container`'s defaults:

   ```python
            try:
                import os
                from dotenv import load_dotenv
                load_dotenv()
                client_id = os.getenv("SPOTIPY_CLIENT_ID", "")
                client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")

                if client_id and client_secret:
                    print(f"{Fore.GREEN}✓ Spotify credentials настроены{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}✗ Spotify credentials не найдены{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Запустите: python main.py --setup{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")
   ```

   Keep the surrounding `if wizard.env_file.exists():` structure and all other lines
   unchanged.

2. Do not change `load_config` or `SpotifyConfig` — other code may rely on them; this
   is a targeted fix to the `--check` path only.

## Files

- **In scope:** `src/shared/ui/cli.py` (`check_configuration` only).
- **Out of scope:** `src/app/config.py`, `providers.py`, the wizard.

## Verification (from repo root)

```bash
python -m py_compile src/shared/ui/cli.py
```
Expected: exit 0.

Behavioral check (no real creds needed — proves no TypeError):
```bash
SPOTIPY_CLIENT_ID=00000000000000000000000000000000 SPOTIPY_CLIENT_SECRET=11111111111111111111111111111111 python - <<'PY'
import os
# Simulate the new check logic in isolation to prove it does not raise.
from dotenv import load_dotenv
load_dotenv()
cid = os.getenv("SPOTIPY_CLIENT_ID",""); cs = os.getenv("SPOTIPY_CLIENT_SECRET","")
assert cid and cs, "env creds should be visible"
print("check-logic OK")
PY
```
Expected: `check-logic OK`. (Requires `python-dotenv`; if not installed, install it in
the worktree or skip — the `py_compile` gate still applies.)

Grep gate:
```bash
python -c "s=open('src/shared/ui/cli.py').read(); assert 'load_config()' not in s.split('def check_configuration')[1].split('def ')[0]; print('OK')"
```
Expected: `OK` (no `load_config()` call remains inside `check_configuration`).

## Done criteria

- `check_configuration` reads creds from `os.getenv` after `load_dotenv()`, not from
  `load_config()`.
- `py_compile` passes; grep gate prints `OK`.

## Test plan

Optional: add `tests/test_check_command.py` that monkeypatches env vars and asserts
`check_configuration` runs without raising. Low priority; the grep + compile gates
suffice for this small change.

## Maintenance note

If credential storage ever moves from `.env`/env vars to a config file, update this
check to match the real run path again — the principle is "check what the app actually
reads."

## Escape hatch

If `check_configuration`'s body differs from the excerpt above (someone changed it),
STOP and report — do not blindly string-replace.
