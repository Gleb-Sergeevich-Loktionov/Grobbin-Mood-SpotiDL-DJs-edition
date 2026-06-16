"""Filesystem operations: playlist dirs, output paths, resume state, M3U."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from src.shared.lib.utils import (
    sanitize_filename,
    get_file_extension,
    is_valid_audio_file,
)

logger = logging.getLogger(__name__)


class FileManager:
    """Manages output directories, file paths, and resume state on disk."""

    def __init__(self, base_output_dir: str):
        self.base_output_dir = Path(base_output_dir)
        self.resume_dir = self.base_output_dir / ".resume_state"
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

    def create_playlist_directory(self, name: str) -> Path:
        safe_name = sanitize_filename(name)
        playlist_dir = self.base_output_dir / safe_name
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return playlist_dir

    def get_output_path(
        self,
        playlist_dir: Path,
        track_number: int,
        artist: str,
        title: str,
        fmt: str,
        filename_template: str,
    ) -> Path:
        safe_artist = sanitize_filename(artist)
        safe_title = sanitize_filename(title)
        try:
            stem = filename_template.format(
                track_number=track_number, artist=safe_artist, title=safe_title
            )
        except (KeyError, ValueError):
            stem = f"{track_number:02d} - {safe_artist} - {safe_title}"
        stem = sanitize_filename(stem)
        ext = get_file_extension(fmt)
        return playlist_dir / f"{stem}{ext}"

    def validate_file(self, path: Path) -> bool:
        return is_valid_audio_file(path)

    def delete_file(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"Failed to delete file {path}: {e}")

    def _resume_path(self, playlist_id: str) -> Path:
        return self.resume_dir / f"{playlist_id}.json"

    def save_resume_state(self, playlist_id: str, state: dict) -> None:
        try:
            self.resume_dir.mkdir(parents=True, exist_ok=True)
            with open(self._resume_path(playlist_id), "w", encoding="utf-8") as f:
                json.dump(state, f)
        except OSError as e:
            logger.warning(f"Failed to save resume state: {e}")

    def load_resume_state(self, playlist_id: str) -> Optional[dict]:
        path = self._resume_path(playlist_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load resume state: {e}")
            return None

    def delete_resume_state(self, playlist_id: str) -> None:
        path = self._resume_path(playlist_id)
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"Failed to delete resume state: {e}")

    def generate_m3u_playlist(
        self, playlist_dir: Path, name: str, track_files: List[Path]
    ) -> None:
        try:
            m3u_path = playlist_dir / f"{sanitize_filename(name)}.m3u"
            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for track_file in track_files:
                    f.write(f"{track_file.name}\n")
        except OSError as e:
            logger.warning(f"Failed to generate M3U playlist: {e}")
