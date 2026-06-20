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


# --- Version-equality hard gate (plan 014) -----------------------------------

def test_original_rejects_remix_candidate():
    # Spotify track is the original 'Stay'; a remix must NOT be accepted even
    # though it is the same song at a similar length.
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


def test_prefers_named_remixer_among_remixes():
    # Two same-version remix candidates; the one naming the requested remixer wins.
    m = _matcher()
    track = _track(name="Stay (Morgan Buckley Remix)", artist="Officer John",
                   duration_ms=240000)
    results = [
        {"id": "other", "title": "Officer John - Stay (Some Other Remix)",
         "duration": 240, "view_count": 1_000_000},
        {"id": "right", "title": "Officer John - Stay (Morgan Buckley Remix)",
         "duration": 241, "view_count": 50_000},
    ]
    assert m._find_best_match(results, track)["id"] == "right"


def test_version_tokens_helper():
    m = _matcher()
    assert m._version_tokens("Stay") == frozenset()
    assert m._version_tokens("Stay (Official Audio)") == frozenset()
    assert "remix" in m._version_tokens("Stay (Morgan Buckley Remix)")
    assert "live" in m._version_tokens("Stay (Live at Wembley)")
    # 'remix' must not also register the looser 'mix'/'edit' substrings.
    assert "mix" not in m._version_tokens("Stay (Morgan Buckley Remix)")
    assert "edit" not in m._version_tokens("Stay (Morgan Buckley Remix)")
    # 'Original Mix' / 'Album Version' ARE the original — no version token.
    assert m._version_tokens("To the Disco 77 (Original Mix)") == frozenset()
    assert m._version_tokens("Song (Album Version)") == frozenset()
    assert m._version_tokens("Song (Original Version)") == frozenset()


def test_original_track_accepts_original_mix_label():
    # Spotify track has no version; YouTube labels it '(Original Mix)' — that IS
    # the original recording and must be accepted, not rejected as a "version".
    m = _matcher()
    track = _track(name="To the Disco 77", artist="Move D", duration_ms=419000)
    results = [{"id": "om", "title": "To the Disco 77 (Original Mix)",
                "duration": 419, "uploader": "Move D - Topic", "view_count": 60_000}]
    assert m._find_best_match(results, track)["id"] == "om"


def test_original_mix_still_rejects_club_mix():
    # Guard: relaxing 'Original Mix' must NOT let a genuine alternate through.
    m = _matcher()
    track = _track(name="To the Disco 77", artist="Move D", duration_ms=419000)
    results = [{"id": "club", "title": "To the Disco 77 (Club Mix)",
                "duration": 418, "uploader": "Move D - Topic"}]
    assert m._find_best_match(results, track) is None


# --- Search-query building + cross-query aggregation (real failures) ---------

def test_query_keeps_version_qualifier():
    # Regression: clean_search_query() used to strip '(David Penn Remix)', so the
    # search never surfaced the right version and the version gate rejected all.
    m = _matcher()
    track = _track(name="1, 2, 3, 4 (David Penn Remix)", artist="Cesar De Melero")
    queries = m.build_search_queries(track)
    assert any("david penn remix" in q.lower() for q in queries)
    # The plain 'artist title' query must come before any '… official audio' one.
    plain = next(i for i, q in enumerate(queries) if q.lower().startswith("cesar de melero"))
    official = [i for i, q in enumerate(queries) if "official audio" in q.lower()]
    assert not official or plain < min(official)


def test_query_adds_base_title_fallback_for_versioned_track():
    m = _matcher()
    track = _track(name="Infinity - Extended Mix", artist="Infinity Ink")
    queries = [q.lower() for q in m.build_search_queries(track)]
    # full title (with version) present...
    assert any("extended mix" in q for q in queries)
    # ...and a base-title fallback without the version qualifier.
    assert any(q.strip() in ("infinity ink infinity", "infinity infinity ink") for q in queries)


def test_artist_fallback_accepts_distinctive_title_without_artist():
    # Label/Topic upload whose visible title omits the artist and whose channel
    # name does not contain it. A versioned title is distinctive enough to accept.
    m = _matcher()
    track = _track(name="1, 2, 3, 4 (David Penn Remix)", artist="Cesar De Melero",
                   duration_ms=202000)
    results = [{"id": "ok", "title": "1, 2, 3, 4 (David Penn Remix)",
                "duration": 202, "uploader": "Release - Topic"}]
    assert m._find_best_match(results, track)["id"] == "ok"


def test_artist_fallback_still_requires_artist_for_short_generic_title():
    # A short, generic 2-word title must NOT be accepted without the artist —
    # otherwise any same-length video with that title would match.
    m = _matcher()
    track = _track(name="Instant Crush", artist="Daft Punk", duration_ms=337000)
    assert m._has_text_relevance("Instant Crush", track) is False
    # but the real artist (in title or channel) still passes:
    assert m._has_text_relevance("Instant Crush", track, uploader="Daft Punk - Topic") is True


def test_search_track_aggregates_best_across_all_queries(monkeypatch):
    # The systemic bug: search_track returned on the FIRST query that yielded any
    # eligible result, so a weak early query won. It must instead gather across all
    # queries and pick the globally best. Here the first query returns a weaker
    # (further-duration) candidate; a later query returns the perfect one.
    m = _matcher()
    track = _track(name="U Won't C Me", artist="Mystic Bill", duration_ms=473000)

    # Same title/artist signal on both; 'weak' is near the edge of the duration
    # tolerance with few views, 'perfect' is exact with many views -> higher score.
    weak = [{"id": "weak", "title": "U Won't C Me",
             "duration": 487, "uploader": "Mystic Bill - Topic", "view_count": 1000}]
    perfect = [{"id": "perfect", "title": "U Won't C Me",
                "duration": 473, "uploader": "Mystic Bill - Topic", "view_count": 40000}]

    calls = {"n": 0}

    def fake_results(query):
        calls["n"] += 1
        return weak if calls["n"] == 1 else perfect

    monkeypatch.setattr(m, "_search_results", fake_results)
    url = m.search_track(track)
    assert url == "https://www.youtube.com/watch?v=perfect"
    assert calls["n"] > 1  # proves it did NOT stop after the first query
