"""Correctness tests for YouTube track matching.

Regression guard for the wrong-track bug: search results used to be accepted with
no real duration/title verification, so a completely different song could be
downloaded. These tests assert the duration + title hard gates reject mismatches
and select the correct video. They are fully offline — `_find_best_match` and its
helpers are pure Python over result dicts, so no yt-dlp / network is needed.
"""

import types

import pytest

pytest.importorskip("yaml")  # src.app.config imports yaml at module import time

from src.features.download.infrastructure.youtube_matcher import YouTubeMatcher


def _matcher() -> YouTubeMatcher:
    config = types.SimpleNamespace(
        search=types.SimpleNamespace(max_results=5, use_isrc=True),
        cache=types.SimpleNamespace(enabled=False, youtube_dir=".", max_age_days=30),
    )
    return YouTubeMatcher(config)


def _track(name="Get Lucky", artist="Daft Punk", duration_ms=248000):
    return types.SimpleNamespace(id="t1", name=name, artist=artist, duration_ms=duration_ms)


def test_rejects_wrong_duration_even_with_matching_title():
    # Arrange: correct title, wildly wrong length (90s vs 248s)
    m, track = _matcher(), _track()
    results = [{"id": "a", "title": "Daft Punk - Get Lucky", "duration": 90}]

    # Act / Assert: duration gate rejects -> no match (skip beats wrong track)
    assert m._find_best_match(results, track) is None


def test_rejects_unrelated_title_with_matching_duration():
    # Arrange: right length, unrelated title
    m, track = _matcher(), _track()
    results = [{"id": "b", "title": "Some Completely Different Song", "duration": 248}]

    # Act / Assert: title-relevance gate rejects
    assert m._find_best_match(results, track) is None


def test_selects_correct_match():
    # Arrange
    m, track = _matcher(), _track()
    results = [{"id": "c", "title": "Daft Punk - Get Lucky (Official Audio)",
                "duration": 249, "view_count": 5_000_000}]

    # Act
    best = m._find_best_match(results, track)

    # Assert
    assert best is not None and best["id"] == "c"


def test_picks_correct_among_mixed_results():
    # Arrange: only one result is both right-length and right-title
    m, track = _matcher(), _track()
    results = [
        {"id": "wrongdur", "title": "Daft Punk - Get Lucky", "duration": 60},
        {"id": "wrongtitle", "title": "Random Unrelated Track", "duration": 248},
        {"id": "right", "title": "Daft Punk - Get Lucky (Official Audio)",
         "duration": 247, "view_count": 9_000_000},
        {"id": "live", "title": "Daft Punk - Get Lucky (Live)", "duration": 250},
    ]

    # Act
    best = m._find_best_match(results, track)

    # Assert: the official studio cut wins over the (eligible but penalized) live one
    assert best is not None and best["id"] == "right"


def test_no_results_returns_none():
    assert _matcher()._find_best_match([], _track()) is None


def test_all_garbage_returns_none():
    # Arrange: nothing passes both gates
    m, track = _matcher(), _track()
    results = [
        {"id": "g1", "title": "Top 50 Hits 2020", "duration": 3600},
        {"id": "g2", "title": "Lofi beats to study", "duration": 248},
        {"id": "g3", "title": "Get Lucky", "duration": 5},
    ]

    # Act / Assert: better to return nothing than a wrong track
    assert m._find_best_match(results, track) is None


def test_text_relevance_helper():
    m, track = _matcher(), _track()
    assert m._has_text_relevance("Daft Punk - Get Lucky (Official Audio)", track) is True
    assert m._has_text_relevance("Get Lucky - Daft Punk", track) is True
    assert m._has_text_relevance("Completely Unrelated Title", track) is False


def test_topic_upload_without_artist_in_title_passes_via_uploader():
    # Auto-generated "Topic" uploads omit the artist from the visible title but
    # carry it in the channel/uploader. That should pass; nothing at all rejects.
    m = _matcher()
    track = _track(name="Instant Crush", artist="Daft Punk", duration_ms=337000)
    assert m._has_text_relevance("Instant Crush", track, uploader="Daft Punk - Topic") is True
    assert m._has_text_relevance("Instant Crush", track) is False


def test_rejects_substring_only_match():
    # 'air' must not match by being a substring of 'repair' (whole-word gate).
    m = _matcher()
    track = _track(name="Air", artist="Test", duration_ms=200000)
    results = [{"id": "x", "title": "Repair Manual - Test", "duration": 200}]
    assert m._find_best_match(results, track) is None


def test_single_word_title_requires_artist():
    # A single-word track name must still require the artist — otherwise any
    # same-length video whose title contains that word would be accepted.
    m = _matcher()
    track = _track(name="Roses", artist="SAINt JHN", duration_ms=167000)

    wrong = [{"id": "wed", "title": "Roses - Best Wedding Moments 2022", "duration": 165}]
    assert m._find_best_match(wrong, track) is None

    right = [{"id": "ok", "title": "SAINt JHN - Roses (Audio)", "duration": 166}]
    assert m._find_best_match(right, track)["id"] == "ok"


def test_cyrillic_track_matches_transliterated_title():
    # Cyrillic track name vs Latin-transliterated YouTube title must match.
    m = _matcher()
    track = _track(name="Кукушка", artist="Кино", duration_ms=366000)
    results = [{"id": "kino", "title": "Kino - Kukushka", "duration": 364}]
    best = m._find_best_match(results, track)
    assert best is not None and best["id"] == "kino"


def test_score_prefers_closer_duration_and_official():
    m, track = _matcher(), _track()
    official = {"title": "Daft Punk - Get Lucky (Official Audio)",
                "duration": 248, "view_count": 5_000_000}
    plain = {"title": "Daft Punk - Get Lucky", "duration": 255}
    assert m._calculate_match_score(official, track) > m._calculate_match_score(plain, track)


def test_picks_original_over_alternate_version():
    # Both are the right song at the right length; the original studio cut must
    # outrank a piano/acoustic re-recording.
    m = _matcher()
    track = _track(name="Never Gonna Give You Up", artist="Rick Astley", duration_ms=213000)
    results = [
        {"id": "piano", "title": "Rick Astley - Never Gonna Give You Up (Pianoforte) (Official)",
         "duration": 210, "view_count": 5_000_000},
        {"id": "orig", "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
         "duration": 213, "view_count": 1_000_000_000},
    ]
    assert m._find_best_match(results, track)["id"] == "orig"
