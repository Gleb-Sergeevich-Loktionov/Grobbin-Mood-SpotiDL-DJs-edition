# Plan 014 — Exact-version track matching (reject wrong versions/remixes)

> Written against commit `6eeab9c`. Confirm with `git rev-parse --short HEAD`
> before starting. If the matcher file below has changed substantially since this
> commit, re-read it and STOP if the structure no longer matches the excerpts.

## Finding

| Field | Value |
|-------|-------|
| Category | Correctness / bug |
| Impact | HIGH — downloaded audio is the **wrong version** of the right song |
| Effort | M |
| Risk of the fix | Low–Medium (ranking already works; this adds a hard gate + tests) |
| Confidence | HIGH |
| Evidence | `src/features/download/infrastructure/youtube_matcher.py` — `_has_text_relevance` (~line 200) and `_calculate_match_score` (~line 250) |

### The problem in plain terms

A previous fix ("Round 3" in `plans/README.md`) stopped the downloader from
grabbing **completely unrelated songs** by adding two hard gates in
`_find_best_match`: a duration gate and a title/artist relevance gate. That works
for "is this even the same song", but it does **not** pin the **version**.

The user's requirement: if the Spotify track is `Officer John - Stay`, the
download must be exactly that recording — **not** `Officer John - Stay (Morgan
Buckley Remix)`, not a live version, not an extended mix, not an acoustic
re-record. And symmetrically: if the Spotify track *is* `Stay (Morgan Buckley
Remix)`, then the plain `Stay` (original) must be rejected.

### Why the current code lets the wrong version through

Two concrete gaps, both verified by reading the code at `6eeab9c`:

**Gap 1 — the title-relevance gate is one-directional and ignores extra words.**

`_has_text_relevance` only checks that ~60% of the *Spotify track-title* words
appear in the YouTube title, plus the artist. It never checks the reverse — words
present in the YouTube title but absent from the track. Current code:

```python
def _has_text_relevance(self, title: str, track: SpotifyTrack, uploader: str = '') -> bool:
    title_set = self._word_set(title)
    uploader_set = self._word_set(uploader)

    title_words = self._word_list(track.name, min_len=2) or self._word_list(track.name, min_len=1)
    artist_words = self._word_list(track.artist, min_len=2) or self._word_list(track.artist, min_len=1)

    if not title_words:
        return False

    title_hits = sum(1 for w in title_words if w in title_set)
    title_ratio = title_hits / len(title_words)

    if artist_words:
        artist_present = any(w in title_set or w in uploader_set for w in artist_words)
    else:
        artist_present = True

    return title_ratio >= 0.6 and artist_present
```

For Spotify track `Stay` and YouTube title `Officer John - Stay (Morgan Buckley
Remix)`: `title_words = ['stay']`, all present → `title_ratio = 1.0`, artist
present → **passes the gate**. The "remix" qualifier is invisible to this gate.

**Gap 2 — the remix/version penalty is soft, partial, and self-disabling.**

In `_calculate_match_score`:

```python
track_is_remix = any(word in track.name.lower() for word in ['remix', 'edit', 'mix', 'version'])

if self.settings.get('avoid_covers', True):
    if 'cover' in title or 'karaoke' in title:
        score -= 15.0
    # Не штрафуем за remix/edit если исходный трек сам является ремиксом
    if not track_is_remix:
        if 'remix' in title or 'edit' in title:
            score -= 10.0
    ...
```

Problems:
1. It is a **ranking nudge** (`-10`), not a gate. If the remix is the *only*
   candidate that passed the duration+title gates, it is still returned and
   downloaded.
2. `track_is_remix` is a coarse substring test. The word `mix` matches `Stay`'s
   own title only if present, but it also flips on for unrelated words and, more
   importantly, **once the track is "a remix" the penalty is disabled entirely**,
   so a track titled `... (Radio Edit)` will happily accept `... (Club Remix)`.
3. The `alt_version_markers` list (piano/acoustic/8-bit/nightcore/…) deliberately
   excludes remix/edit/mix, so those alternate-version cases have no ranking
   protection at all.

The fix is to make **version equality a hard gate**, symmetric in both
directions, applied in `_find_best_match` next to the existing duration and
title gates.

## What "correct version" means (the rule to implement)

Define a normalized **version descriptor** for any title string:

- Take all parenthetical/bracketed qualifiers: the contents of `(...)` and `[...]`,
  plus any trailing `- ... Remix` / `- ... Mix` style suffix.
- From those, detect a small set of **version keywords**:
  `remix`, `edit`, `mix` (as in "club mix"/"extended mix"), `version`, `live`,
  `acoustic`, `unplugged`, `instrumental`, `radio edit`, `extended`, `vip`,
  `bootleg`, `rework`, `reprise`, `demo`, `remaster`/`remastered`, `mono`,
  `karaoke`, `cover`, `sped up`, `slowed`, `nightcore`.
- **Ignore** non-version qualifiers that commonly appear on legitimate originals:
  `feat`, `ft`, `featuring`, `official`, `official audio`, `official video`,
  `audio`, `lyrics`, `lyric video`, `hd`, `hq`, `4k`, `explicit`, `clean`, `prod`,
  and a bare year. These must NOT count as a version difference.
- A title with **no** version keyword has descriptor = "original".

The **gate rule** (hard, in `_find_best_match`):

- Compute `track_version` from `track.name` and `video_version` from the candidate
  `title`.
- **Reject** the candidate if the version sets differ in a meaningful way:
  - If the track is **original** (no version keyword) but the candidate carries a
    version keyword (remix/live/acoustic/…), reject. *(This is the
    `Stay` vs `Stay (Morgan Buckley Remix)` case.)*
  - If the track **is** a specific version (e.g. has `remix`), the candidate must
    carry the **same** primary version keyword; reject otherwise. *(This is the
    `Stay (Morgan Buckley Remix)` vs plain `Stay` case, and remix-vs-different-remix.)*
- When the track is a named remix (`(Morgan Buckley Remix)`), prefer that the
  remixer name also appear in the candidate title; if a same-keyword candidate
  with the remixer name exists, it must outrank one without. This part is a
  **ranking** refinement, not a gate (the remixer name is often abbreviated on
  YouTube), so keep it in `_calculate_match_score`.

This makes the accepted result's *version* provably equal to the Spotify track's
version, which is exactly the guarantee the user asked for.

## Files in scope

- `src/features/download/infrastructure/youtube_matcher.py` — add the version
  helpers and wire the hard gate into `_find_best_match`; refine ranking.
- `tests/test_youtube_matching.py` — add regression tests (this is the canonical
  test file and the pattern to follow).

## Files explicitly OUT of scope — do not touch

- `src/features/download/domain/strategies.py` — these `*MatchStrategy` classes are
  **not** on the live download path (the live path is
  `DownloadManager._download_single_track` → `YouTubeMatcher.search_track` →
  `_find_best_match`). Editing them changes nothing the user sees. Leave them.
- `src/features/download/infrastructure/download_manager.py` — its post-download
  `_verify_audio_duration` is a duration-only guard and is fine as-is. Do not add
  version logic there; duration cannot distinguish a remix of similar length.
- `src/features/spotify/**` — the `SpotifyTrack` model already carries everything
  needed (`name`, `artist`, `duration_ms`, `isrc`). No schema change.
- Caching layer — the YouTube cache keys on `track.id`, which already differs
  between the original and the remix (they are distinct Spotify tracks), so no
  cache-poisoning risk. Do not modify the cache.

## Conventions to follow (from the existing file)

- Helpers are `@staticmethod` or instance methods using `re.findall(r'\w+', ...)`
  with `unidecode(...).lower()` for ASCII-folded, whole-word tokenization. Reuse
  `self._word_set` / `self._word_list` style. See the top of the file:

```python
@staticmethod
def _word_set(text: str) -> set:
    """Whole-word token set, transliterated to ASCII and lowercased."""
    return set(re.findall(r'\w+', unidecode(text or '').lower()))
```

- The `unidecode` import already has a graceful fallback at the top of the file;
  reuse it, do not add a new dependency.
- Gates live in `_find_best_match`, log a `reject #N (reason)` debug line, and
  increment the local `rejected` counter, matching the existing duration/title
  gates. When nothing qualifies, return `None` (skip beats wrong track) — this is
  the established contract, asserted by existing tests.
- Comments in this file are full sentences explaining *why* a gate exists (see the
  `HARD GATE 1` / `HARD GATE 2` comments). Match that style for `HARD GATE 3`.

## Implementation steps

### Step 1 — add version-descriptor helpers

In `youtube_matcher.py`, near `_word_set` / `_word_list`, add two helpers and a
module-level keyword constant. Suggested shape (adapt names to match file style):

```python
# Version keywords that make a recording a DIFFERENT track from the original.
# Order matters for picking the "primary" keyword: remix/edit/live/etc.
_VERSION_KEYWORDS = (
    'remix', 'radio edit', 'extended mix', 'extended', 'club mix', 'vip',
    'bootleg', 'rework', 'edit', 'live', 'acoustic', 'unplugged',
    'instrumental', 'karaoke', 'cover', 'reprise', 'demo', 'remaster',
    'remastered', 'mono', 'nightcore', 'sped up', 'slowed', 'mix', 'version',
)

# Qualifiers that appear on legitimate ORIGINALS and must NOT count as a version
# difference.
_NEUTRAL_QUALIFIERS = (
    'feat', 'ft', 'featuring', 'official', 'audio', 'video', 'lyrics', 'lyric',
    'hd', 'hq', '4k', 'explicit', 'clean', 'prod', 'mv', 'mp3',
)


@classmethod
def _version_tokens(cls, text: str) -> frozenset:
    """Return the set of version keywords present in `text`.

    Empty set == "original recording". Neutral qualifiers (feat/official/audio/…)
    are never version tokens, so 'Stay (feat. X) [Official Audio]' is still
    "original".
    """
    folded = unidecode(text or '').lower()
    found = set()
    for kw in cls._VERSION_KEYWORDS:
        # whole-word / phrase match, not substring (so 'mix' does not fire on 'remix'
        # twice or on unrelated words); require word boundaries.
        if re.search(r'\b' + re.escape(kw) + r'\b', folded):
            found.add(kw)
    # 'remix' implies 'mix'/'edit' substrings — collapse to the most specific.
    if 'remix' in found:
        found.discard('mix')
        found.discard('edit')
    if 'radio edit' in found or 'extended mix' in found or 'club mix' in found:
        found.discard('mix')
        found.discard('edit')
        found.discard('extended')
    return frozenset(found)
```

> Note on `\b...\b` and multi-word keywords: `radio edit` etc. contain a space, and
> `re.search(r'\bradio edit\b', ...)` works correctly on the ASCII-folded string.
> Verify the `mix`/`remix` collapse with the unit tests in Step 4 — adjust the
> discard rules if a test reveals a missed combination. **If a real Spotify title
> uses a version word this list doesn't cover, that is acceptable: the failure mode
> is "skip and log", never "download wrong version".**

### Step 2 — add the version-equality gate method

```python
def _version_matches(self, candidate_title: str, track: SpotifyTrack) -> bool:
    """True only if the candidate is the SAME version as the Spotify track.

    Hard rule, both directions:
      * track is original  -> candidate must carry NO version keyword;
      * track is a version -> candidate must carry the SAME primary version keyword.
    This is what guarantees 'Officer John - Stay' never downloads
    'Officer John - Stay (... Remix)' and vice versa.
    """
    track_v = self._version_tokens(track.name)
    cand_v = self._version_tokens(candidate_title)

    if not track_v:
        # Original wanted: reject anything carrying a version keyword.
        return not cand_v

    # Specific version wanted: the candidate must share at least the primary keyword.
    return bool(track_v & cand_v)
```

### Step 3 — wire the gate into `_find_best_match`

In `_find_best_match`, immediately **after** the existing HARD GATE 2 (title
relevance) and **before** `score = self._calculate_match_score(...)`, insert:

```python
            # HARD GATE 3 — the VERSION must match. Same song, wrong version
            # (remix/live/acoustic/edit/…) is still the wrong file. Symmetric:
            # an original track rejects a remix candidate, and a remix track
            # rejects the plain original.
            if not self._version_matches(title, track):
                rejected += 1
                logger.debug(f"  reject #{idx + 1} (version mismatch): '{title}'")
                continue
```

Do not change the existing duration or title gates. Keep the `eligible`/`rejected`
accounting and the final `None`-on-empty behavior exactly as they are.

### Step 4 — refine ranking for named remixes (optional nudge, not a gate)

In `_calculate_match_score`, when `track` is a named remix, give a small bonus when
the remixer name (the non-keyword words inside the track's parenthetical) also
appears in the candidate title. Keep it small (e.g. `+8`) so it only breaks ties
between same-keyword candidates. This is ranking-only; the gate in Step 3 already
guarantees correctness. Leave the existing `alt_version_markers` block as-is.

### Step 5 — add regression tests

Append to `tests/test_youtube_matching.py`, following the existing offline,
`types.SimpleNamespace`-based style (no network). Cover, at minimum:

```python
def test_original_rejects_remix_candidate():
    m = _matcher()
    track = _track(name="Stay", artist="Officer John", duration_ms=200000)
    results = [{"id": "remix", "title": "Officer John - Stay (Morgan Buckley Remix)",
                "duration": 201, "view_count": 5_000_000}]
    assert m._find_best_match(results, track) is None


def test_original_accepts_plain_original():
    m = _matcher()
    track = _track(name="Stay", artist="Officer John", duration_ms=200000)
    results = [{"id": "orig", "title": "Officer John - Stay (Official Audio)",
                "duration": 200, "view_count": 1_000_000}]
    assert m._find_best_match(results, track)["id"] == "orig"


def test_remix_track_rejects_plain_original():
    m = _matcher()
    track = _track(name="Stay (Morgan Buckley Remix)", artist="Officer John",
                   duration_ms=240000)
    results = [{"id": "orig", "title": "Officer John - Stay", "duration": 239}]
    assert m._find_best_match(results, track) is None


def test_remix_track_accepts_matching_remix():
    m = _matcher()
    track = _track(name="Stay (Morgan Buckley Remix)", artist="Officer John",
                   duration_ms=240000)
    results = [{"id": "rx", "title": "Officer John - Stay (Morgan Buckley Remix)",
                "duration": 241, "view_count": 200_000}]
    assert m._find_best_match(results, track)["id"] == "rx"


def test_neutral_qualifiers_do_not_block_original():
    # feat / official / audio / explicit are NOT versions.
    m = _matcher()
    track = _track(name="Stay", artist="Officer John", duration_ms=200000)
    results = [{"id": "ok", "title": "Officer John - Stay (feat. X) [Official Audio] (Explicit)",
                "duration": 200, "view_count": 9_000}]
    assert m._find_best_match(results, track)["id"] == "ok"


def test_live_and_acoustic_rejected_for_studio_original():
    m = _matcher()
    track = _track(name="Stay", artist="Officer John", duration_ms=200000)
    results = [
        {"id": "live", "title": "Officer John - Stay (Live)", "duration": 200},
        {"id": "ac", "title": "Officer John - Stay (Acoustic)", "duration": 201},
    ]
    assert m._find_best_match(results, track) is None


def test_version_tokens_helper():
    m = _matcher()
    assert m._version_tokens("Stay") == frozenset()
    assert m._version_tokens("Stay (Official Audio)") == frozenset()
    assert "remix" in m._version_tokens("Stay (Morgan Buckley Remix)")
    assert "live" in m._version_tokens("Stay (Live at Wembley)")
```

If a test reveals the `mix`/`remix`/`edit` collapse logic in `_version_tokens` is
wrong, fix the collapse rules in Step 1 until all tests pass. Do **not** weaken the
gate to make a test pass.

## Verification gates (run exactly these)

From the repo root `D:\dev_projects\Grobbin-Mood-SpotiDL-DJs-edition`:

1. Run the matcher tests (must all pass, new ones included):
   ```powershell
   python -m pytest tests/test_youtube_matching.py -q
   ```
   Expected: all tests pass, including the new `test_original_rejects_remix_candidate`,
   `test_remix_track_rejects_plain_original`, etc.

2. Run the full suite (no regressions elsewhere):
   ```powershell
   python -m pytest -q
   ```
   Expected: same pass count as before plus the newly added tests; zero failures.

3. Import smoke check (the matcher still imports cleanly):
   ```powershell
   python -c "from src.features.download.infrastructure.youtube_matcher import YouTubeMatcher; print('ok')"
   ```
   Expected output: `ok`

> Optional live check (requires `.env` Spotify creds and network — only if the user
> wants end-to-end confirmation): `python scripts/e2e_verify.py <playlist_url>` and
> confirm a playlist containing both an original and its remix downloads each to the
> correct version. This is NOT required to consider the plan done; the offline tests
> are the gate.

## Done criteria (machine-checkable)

- `python -m pytest tests/test_youtube_matching.py -q` exits 0 with the new tests
  present and passing.
- `python -m pytest -q` exits 0.
- `_find_best_match` returns `None` for the `Stay` vs `Stay (… Remix)` case and
  returns the correct id for the matching-version cases, as asserted by the tests
  above.
- No files outside the two in-scope files were modified
  (`git status --porcelain` shows only `youtube_matcher.py` and
  `tests/test_youtube_matching.py`).

## Test plan

New tests go in `tests/test_youtube_matching.py` (the canonical, offline matcher
test file). Follow its `_matcher()` / `_track()` helpers and `types.SimpleNamespace`
fakes — no network, no yt-dlp. Cover: original-rejects-remix, original-accepts-
original, remix-rejects-original, remix-accepts-remix, neutral-qualifiers-pass,
live/acoustic-rejected, and the `_version_tokens` helper directly.

## Maintenance note

- The version-keyword list is the one place future "wrong version slipped through"
  reports will point to. New cases (e.g. a label using "Sessions" or "Flip" to mean
  a remix) are a one-line addition to `_VERSION_KEYWORDS`. The fail-safe direction
  is "skip and log", so an unknown keyword never causes a wrong download — at worst
  a missed download that surfaces in `failed_tracks.log`.
- Watch the `mix`/`remix`/`edit`/`extended mix` collapse in `_version_tokens` in
  review: substring overlaps between keywords are the subtle part. The unit test
  `test_version_tokens_helper` guards it.
- This gate composes with the existing duration + title gates; if a future change
  loosens those, the version gate still holds version correctness independently.

## Escape hatches — STOP and report instead of improvising if:

- The file structure at the current commit no longer matches the excerpts above
  (e.g. `_find_best_match` or `_has_text_relevance` was refactored away). Report
  what changed; do not guess where to put the gate.
- Adding the gate makes a large fraction of a real playlist fail to match (many
  `version mismatch` rejects on titles that are genuinely the right version). That
  means a neutral qualifier is being misread as a version keyword — report the
  offending titles rather than deleting keywords wholesale.
- You find the live path does **not** actually go through `_find_best_match`
  (verify via `download_manager._download_single_track` →
  `youtube_matcher.search_track`). If so, the gate belongs wherever the real
  selection happens; report the discrepancy before coding.
