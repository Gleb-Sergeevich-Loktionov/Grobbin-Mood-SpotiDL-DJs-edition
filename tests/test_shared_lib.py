"""Unit tests for src.shared.lib pure-Python utilities."""

import tempfile
from pathlib import Path

from src.shared.lib import utils
from src.shared.lib.file_manager import FileManager
from src.shared.lib.cache import YouTubeCache


def test_validate_url_accepts_spotify_playlist():
    assert utils.validate_url("https://open.spotify.com/playlist/abc123")


def test_validate_url_rejects_garbage():
    assert not utils.validate_url("not a url")


def test_extract_playlist_id():
    url = "https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS?si=x"
    assert utils.extract_playlist_id(url) == "7ooZ1OdYCD6wibrLAfrgXS"


def test_sanitize_filename_strips_invalid_chars():
    assert ":" not in utils.sanitize_filename("a:b/c?")


def test_format_duration():
    assert utils.format_duration(65) == "1m 5s"


def test_file_manager_roundtrip():
    d = tempfile.mkdtemp()
    fm = FileManager(d)
    pd = fm.create_playlist_directory("My: Playlist?")
    assert pd.exists()
    op = fm.get_output_path(pd, 3, "Artist", "Title", "mp3",
                            "{track_number:02d} - {artist} - {title}")
    assert op.suffix == ".mp3"
    assert op.name.startswith("03 -")


def test_resume_state_roundtrip():
    fm = FileManager(tempfile.mkdtemp())
    fm.save_resume_state("pl", {"completed_tracks": ["a", "b"]})
    assert fm.load_resume_state("pl")["completed_tracks"] == ["a", "b"]
    fm.delete_resume_state("pl")
    assert fm.load_resume_state("pl") is None


def test_youtube_cache_set_get():
    c = YouTubeCache(tempfile.mkdtemp(), 86400)
    c.set("track-id", "https://youtube.com/watch?v=x")
    assert c.get("track-id") == "https://youtube.com/watch?v=x"


def test_youtube_cache_missing_key_returns_none():
    c = YouTubeCache(tempfile.mkdtemp(), 86400)
    assert c.get("nope") is None
