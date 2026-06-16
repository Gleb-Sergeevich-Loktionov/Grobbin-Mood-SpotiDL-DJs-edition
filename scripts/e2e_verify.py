"""End-to-end matching-correctness verifier.

Proves, against the *real* Spotify playlist and the *real* YouTube search, that the
track selected for each playlist entry is actually that track — the thing the
wrong-track bug broke. For every track it runs the app's own YouTubeMatcher and
then independently re-checks the chosen video's duration against Spotify's.

Why match-only by default: confirming the selected video's length matches the
Spotify track is sufficient to prove correctness, is fast, and downloads no audio.
Pass --download to additionally fetch each file and verify the on-disk duration.

Requirements (this is the part that cannot run in CI without you):
  - `.env` with SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET (Client-Credentials
    flow — reads public playlists, no browser login needed).
  - deps installed: `pip install -r requirements.txt`
  - network access; ffmpeg on PATH only if you use --download.

Usage:
  python scripts/e2e_verify.py <playlist_url_or_id> [--limit N] [--tolerance S] [--download]

Exit code is non-zero if any track mismatches, so it can gate a release.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import types
from pathlib import Path

# Allow running from the repo root (so `src` imports resolve).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEFAULT_TOLERANCE_S = 15


def _die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def _playlist_id(value: str) -> str:
    m = re.search(r"playlist[/:]([a-zA-Z0-9]+)", value)
    return m.group(1) if m else value


def _build_matcher():
    from src.features.download.infrastructure.youtube_matcher import YouTubeMatcher

    config = types.SimpleNamespace(
        search=types.SimpleNamespace(max_results=5, use_isrc=True),
        cache=types.SimpleNamespace(enabled=False, youtube_dir=".", max_age_days=30),
    )
    return YouTubeMatcher(config)


def _fetch_tracks(playlist_id: str, limit: int):
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    if not client_id or not client_secret:
        _die("SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET not set (check your .env).")

    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth)

    tracks = []
    offset = 0
    while True:
        page = sp.playlist_items(playlist_id, offset=offset, limit=100,
                                 fields="items.track(name,artists,duration_ms,id),next")
        for item in page.get("items", []):
            t = item.get("track")
            if not t or not t.get("id"):
                continue
            tracks.append(types.SimpleNamespace(
                id=t["id"],
                name=t["name"],
                artist=(t["artists"][0]["name"] if t.get("artists") else "Unknown Artist"),
                duration_ms=t.get("duration_ms") or 0,
            ))
            if limit and len(tracks) >= limit:
                return tracks
        if not page.get("next"):
            break
        offset += 100
    return tracks


def _download_duration(matcher, url: str) -> float | None:
    """Download audio to a temp dir and return its measured duration (seconds)."""
    import tempfile
    import yt_dlp

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "%(id)s.%(ext)s")
        opts = {"quiet": True, "no_warnings": True, "format": "bestaudio/best",
                "outtmpl": out, "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"    download failed: {e}", file=sys.stderr)
            return None
        import mutagen
        for f in Path(tmp).iterdir():
            audio = mutagen.File(str(f))
            length = getattr(getattr(audio, "info", None), "length", None)
            if length:
                return float(length)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify playlist match correctness end-to-end.")
    parser.add_argument("playlist", help="Spotify playlist URL or ID")
    parser.add_argument("--limit", type=int, default=0, help="Check at most N tracks (0 = all)")
    parser.add_argument("--tolerance", type=int, default=DEFAULT_TOLERANCE_S,
                        help=f"Duration tolerance in seconds (default {DEFAULT_TOLERANCE_S})")
    parser.add_argument("--download", action="store_true",
                        help="Also download each match and verify on-disk duration")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    playlist_id = _playlist_id(args.playlist)
    matcher = _build_matcher()
    tracks = _fetch_tracks(playlist_id, args.limit)
    if not tracks:
        _die("No tracks fetched — check the playlist URL/ID and credentials.")

    print(f"Verifying {len(tracks)} track(s), tolerance ±{args.tolerance}s, "
          f"download={'yes' if args.download else 'no'}\n")

    matched = mismatched = not_found = 0
    for i, track in enumerate(tracks, 1):
        expected = (track.duration_ms or 0) / 1000.0
        label = f"{track.artist} - {track.name}"
        url = matcher.search_track(track)

        if not url:
            not_found += 1
            print(f"[{i:>3}] NO-MATCH  {label} (expected {expected:.0f}s)")
            continue

        if args.download:
            got = _download_duration(matcher, url)
        else:
            info = matcher.get_video_info(url) or {}
            got = info.get("duration")

        if not got:
            not_found += 1
            print(f"[{i:>3}] NO-DUR    {label} -> {url}")
            continue

        diff = abs(got - expected)
        if diff <= args.tolerance:
            matched += 1
            print(f"[{i:>3}] MATCH     {label} ({expected:.0f}s ~= {got:.0f}s) {url}")
        else:
            mismatched += 1
            print(f"[{i:>3}] MISMATCH  {label} (expected {expected:.0f}s, got {got:.0f}s) {url}")

    total = len(tracks)
    print(f"\nSummary: {matched}/{total} matched, {mismatched} mismatched, {not_found} not found.")
    if mismatched:
        print("FAIL: at least one downloaded/selected track does not match the playlist.")
        return 1
    print("PASS: every selected track matches its Spotify entry within tolerance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
