"""Валидатор входных данных CLI."""
import logging
from pathlib import Path
from typing import List, Optional
import argparse

logger = logging.getLogger(__name__)


class CLIValidator:
    """Отвечает только за валидацию входных данных."""
    
    def validate_args(self, args: argparse.Namespace) -> bool:
        """Валидировать аргументы командной строки."""
        # Проверка URLs
        if args.urls:
            if not self._validate_urls(args.urls):
                return False
        
        # Проверка файла с плейлистами
        if args.playlists:
            if not self._validate_playlist_file(args.playlists):
                return False
        
        # Проверка output директории
        if args.output:
            if not self._validate_output_dir(args.output):
                return False
        
        return True
    
    def _validate_urls(self, urls: List[str]) -> bool:
        """Валидировать Spotify URLs."""
        for url in urls:
            if not ('spotify.com/playlist/' in url or 'spotify:playlist:' in url):
                logger.error(f"Invalid Spotify URL: {url}")
                return False
        return True
    
    def _validate_playlist_file(self, filepath: str) -> bool:
        """Валидировать файл с плейлистами."""
        path = Path(filepath)
        if not path.exists():
            logger.error(f"Playlist file not found: {filepath}")
            return False
        return True
    
    def _validate_output_dir(self, dirpath: str) -> bool:
        """Валидировать output директорию."""
        path = Path(dirpath)
        if path.exists() and not path.is_dir():
            logger.error(f"Output path exists but is not a directory: {dirpath}")
            return False
        return True

# Made with Bob
