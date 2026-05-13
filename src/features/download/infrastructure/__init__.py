"""
Download infrastructure layer.
Contains implementations for downloading tracks.
"""

from .download_manager import DownloadManager, DownloadResult
from .youtube_matcher import YouTubeMatcher

__all__ = [
    'DownloadManager',
    'DownloadResult',
    'YouTubeMatcher',
]

# Made with Bob
