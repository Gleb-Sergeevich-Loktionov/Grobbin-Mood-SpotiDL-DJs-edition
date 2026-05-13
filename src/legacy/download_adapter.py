"""
Legacy adapter for Download Manager.
Provides backward compatibility with old import paths.
"""

from src.features.download.infrastructure.download_manager import (
    DownloadManager,
    DownloadResult
)
from src.app.config import Config
from src.features.spotify.infrastructure.spotify_client import SpotifyClient
from src.shared.ui.progress import ProgressTracker

__all__ = [
    'DownloadManager',
    'DownloadResult',
]

# Made with Bob