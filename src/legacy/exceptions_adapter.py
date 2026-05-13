"""
Legacy adapter for Exceptions.
Provides backward compatibility with old import paths.
"""

from src.shared.lib.exceptions import (
    SpotifyDownloaderError,
    UserFriendlyError,
    EncodingError,
    SpotifyAPIError,
    YouTubeMatchError,
    DownloadError,
    MetadataError,
    FileOperationError,
    ConfigurationError,
    AuthenticationError,
    create_error,
    format_warning,
    format_success,
    format_info,
    ERROR_MESSAGES,
)

__all__ = [
    'SpotifyDownloaderError',
    'UserFriendlyError',
    'EncodingError',
    'SpotifyAPIError',
    'YouTubeMatchError',
    'DownloadError',
    'MetadataError',
    'FileOperationError',
    'ConfigurationError',
    'AuthenticationError',
    'create_error',
    'format_warning',
    'format_success',
    'format_info',
    'ERROR_MESSAGES',
]

# Made with Bob