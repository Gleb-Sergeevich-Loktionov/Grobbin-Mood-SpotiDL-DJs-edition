"""Парсер аргументов командной строки."""
import argparse
from typing import Optional
from pathlib import Path


class CLIArgumentParser:
    """Отвечает только за парсинг аргументов командной строки."""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Создать парсер аргументов."""
        parser = argparse.ArgumentParser(
            description='Spotify Playlist Downloader',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Основные аргументы
        parser.add_argument('urls', nargs='*', help='Spotify playlist URLs')
        parser.add_argument('--playlists', type=str, help='File with playlist URLs')
        parser.add_argument('--setup', action='store_true', help='Run setup wizard')
        parser.add_argument('--check', action='store_true', help='Check configuration')
        parser.add_argument('--update', action='store_true', help='Update existing playlists')
        
        # Опции скачивания
        parser.add_argument('--format', type=str, choices=['mp3', 'flac'], help='Audio format')
        parser.add_argument('--quality', type=str, help='Audio quality')
        parser.add_argument('--output', type=str, help='Output directory')
        parser.add_argument('--threads', type=int, help='Number of download threads')
        
        return parser
    
    def parse(self, args: Optional[list] = None) -> argparse.Namespace:
        """Распарсить аргументы."""
        return self.parser.parse_args(args)

# Made with Bob
