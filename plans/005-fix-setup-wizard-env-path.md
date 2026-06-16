# Plan 005 — Fix setup wizard writing `.env` to the wrong directory

**Written against commit:** `e5867eb`
**Finding:** #6 (HIGH) · **Effort:** S · **Risk:** Low
**Depends on:** nothing (independent)

## Why this matters

The setup wizard computes its project root wrong, so it writes `.env` into
`src/widgets/` instead of the repo root. The app loads `.env` from the repo root (via
`load_dotenv()` with the default search), so credentials saved by the wizard are never
read — setup silently does nothing useful.

## Current state (exact)

`src/widgets/setup_wizard/wizard.py:21-25`:
```python
    def __init__(self):
        """Initialize setup wizard."""
        self.root_dir = Path(__file__).parent.parent
        self.env_file = self.root_dir / ".env"
        self.env_example = self.root_dir / ".env.example"
        self.config = {}
```

`__file__` is `src/widgets/setup_wizard/wizard.py`. `Path(__file__).parent` →
`src/widgets/setup_wizard`. `.parent.parent` → `src/widgets`. So `root_dir` resolves to
`src/widgets`, and `.env` is written to `src/widgets/.env`.

The correct repo root is **three** directories up from the file's directory:
`setup_wizard` → `widgets` → `src` → repo root. That is `Path(__file__).parents[3]`
(or equivalently `Path(__file__).resolve().parents[3]`).

`load_dotenv()` in `providers.py:14` and `config.py` uses the default (CWD-based)
search, which finds the repo-root `.env` when the app is run from the repo root.

## Steps

1. In `src/widgets/setup_wizard/wizard.py`, change line 23 from:
   ```python
        self.root_dir = Path(__file__).parent.parent
   ```
   to:
   ```python
        self.root_dir = Path(__file__).resolve().parents[3]
   ```
   This makes `root_dir` the repo root regardless of CWD. `env_file` and `env_example`
   (lines 24-25) then correctly point at `<repo root>/.env` and `<repo root>/.env.example`.

2. Change nothing else in the file.

## Files

- **In scope:** `src/widgets/setup_wizard/wizard.py` (line 23 only).
- **Out of scope:** everything else.

## Verification (from repo root)

```bash
python -m py_compile src/widgets/setup_wizard/wizard.py
```
Expected: exit 0.

Prove the path now resolves to the repo root (this file lives at
`<root>/src/widgets/setup_wizard/wizard.py`, so `parents[3]` == repo root):
```bash
python -c "
from pathlib import Path
f = Path('src/widgets/setup_wizard/wizard.py').resolve()
root = f.parents[3]
assert (root / 'main.py').exists(), f'expected repo root, got {root}'
assert (root / 'requirements.txt').exists()
print('path OK:', root.name)
"
```
Expected: `path OK: Grobbin-Mood-SpotiDL-DJs-edition` (or whatever the repo dir is named).

Grep gate:
```bash
python -c "s=open('src/widgets/setup_wizard/wizard.py').read(); assert 'parents[3]' in s and 'parent.parent\n' not in s.replace(' ',''); print('OK')"
```
Expected: `OK`.

## Done criteria

- `root_dir` uses `Path(__file__).resolve().parents[3]`.
- Path verification prints the repo root name and both asserts pass.
- `py_compile` passes.

## Test plan

Optional `tests/test_wizard_paths.py`:
```python
from src.widgets.setup_wizard.wizard import SetupWizard
def test_env_file_at_repo_root():
    w = SetupWizard()
    assert (w.root_dir / "main.py").exists()
    assert w.env_file == w.root_dir / ".env"
```
(Requires `colorama`; guard with `pytest.importorskip("colorama")` if needed.)

## Maintenance note

`parents[3]` is brittle if the file is ever moved to a different depth. If the wizard
module relocates, recount the directory levels to the repo root. A more robust
alternative (optional, not required here) is to walk upward looking for a marker like
`requirements.txt`.

## Escape hatch

If the wizard file is not at `src/widgets/setup_wizard/wizard.py` (depth changed),
recount levels and report the correct index instead of assuming 3.
