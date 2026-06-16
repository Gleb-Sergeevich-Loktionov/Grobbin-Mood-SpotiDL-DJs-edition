"""Application exception hierarchy and user-facing message helpers."""

from __future__ import annotations

from typing import Optional


class SpotifyDownloaderError(Exception):
    """Base class for all application errors."""


class UserFriendlyError(SpotifyDownloaderError):
    """Error carrying a message safe to show the end user."""


class EncodingError(SpotifyDownloaderError):
    """Raised on text encoding/decoding problems."""


class SpotifyAPIError(SpotifyDownloaderError):
    """Raised on Spotify API failures."""


class YouTubeMatchError(SpotifyDownloaderError):
    """Raised when no acceptable YouTube match is found."""


class DownloadError(SpotifyDownloaderError):
    """Raised on download failures."""


class MetadataError(SpotifyDownloaderError):
    """Raised on metadata embedding failures."""


class FileOperationError(SpotifyDownloaderError):
    """Raised on filesystem operation failures."""


class ConfigurationError(SpotifyDownloaderError):
    """Raised on invalid or missing configuration."""


class AuthenticationError(SpotifyDownloaderError):
    """Raised on authentication failures."""


ERROR_MESSAGES = {
    "spotify_auth": "Spotify authentication failed. Check your credentials in .env.",
    "no_match": "No acceptable YouTube match was found for this track.",
    "download_failed": "Download failed. See the log for details.",
    "config_missing": "Configuration is missing or invalid.",
}


def create_error(key: str, default: str = "An error occurred.") -> UserFriendlyError:
    return UserFriendlyError(ERROR_MESSAGES.get(key, default))


def format_warning(message: str) -> str:
    return f"WARNING: {message}"


def format_success(message: str) -> str:
    return f"OK: {message}"


def format_info(message: str) -> str:
    return f"INFO: {message}"
