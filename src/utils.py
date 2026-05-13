"""
Utility functions for Spotify Playlist Downloader.
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(invalid_chars, '', filename)
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Truncate if too long (leave room for extension)
    if len(filename) > max_length - 10:
        filename = filename[:max_length - 10]
    
    return filename or 'untitled'


def normalize_string(text: str) -> str:
    """
    Normalize string by removing accents and special characters.
    
    Args:
        text: Input text
        
    Returns:
        Normalized text
    """
    # Normalize unicode characters
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration (e.g., "3m 45s")
    """
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds}s"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"


def format_size(bytes_size: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted size (e.g., "3.5 MB")
    """
    size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_speed(bytes_per_second: float) -> str:
    """
    Format download speed to human-readable string.
    
    Args:
        bytes_per_second: Speed in bytes per second
        
    Returns:
        Formatted speed (e.g., "3.2 MB/s")
    """
    return f"{format_size(int(bytes_per_second))}/s"


def extract_playlist_id(url: str) -> Optional[str]:
    """
    Extract playlist ID from Spotify URL.
    
    Args:
        url: Spotify playlist URL
        
    Returns:
        Playlist ID or None if invalid
    """
    # Pattern: https://open.spotify.com/playlist/{id}?si=...
    pattern = r'playlist/([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    
    logger.warning(f"Could not extract playlist ID from URL: {url}")
    return None


def extract_track_id(url: str) -> Optional[str]:
    """
    Extract track ID from Spotify URL.
    
    Args:
        url: Spotify track URL
        
    Returns:
        Track ID or None if invalid
    """
    pattern = r'track/([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    
    return None


def validate_url(url: str) -> bool:
    """
    Validate if string is a valid Spotify URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid Spotify URL
    """
    spotify_pattern = r'https?://open\.spotify\.com/(playlist|track|album)/[a-zA-Z0-9]+'
    return bool(re.match(spotify_pattern, url))


def create_directory(path: Path, exist_ok: bool = True) -> bool:
    """
    Create directory if it doesn't exist.
    
    Args:
        path: Directory path
        exist_ok: Don't raise error if directory exists
        
    Returns:
        True if directory was created or already exists
    """
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def get_file_extension(format_name: str) -> str:
    """
    Get file extension for audio format.
    
    Args:
        format_name: Audio format (mp3, m4a, flac)
        
    Returns:
        File extension with dot
    """
    extensions = {
        'mp3': '.mp3',
        'm4a': '.m4a',
        'flac': '.flac',
        'opus': '.opus',
        'ogg': '.ogg'
    }
    return extensions.get(format_name.lower(), '.mp3')


def parse_artists(artists: List[str]) -> str:
    """
    Parse list of artists into a single string.
    
    Args:
        artists: List of artist names
        
    Returns:
        Comma-separated artist names
    """
    if not artists:
        return "Unknown Artist"
    
    if len(artists) == 1:
        return artists[0]
    
    if len(artists) == 2:
        return f"{artists[0]} & {artists[1]}"
    
    # For 3+ artists, use commas and "and" for the last one
    return ", ".join(artists[:-1]) + f" & {artists[-1]}"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def is_valid_audio_file(file_path: Path, min_size: int = 1024) -> bool:
    """
    Check if file is a valid audio file.
    
    Args:
        file_path: Path to audio file
        min_size: Minimum file size in bytes
        
    Returns:
        True if file exists and meets minimum size
    """
    if not file_path.exists():
        return False
    
    if not file_path.is_file():
        return False
    
    if file_path.stat().st_size < min_size:
        logger.warning(f"File too small: {file_path} ({file_path.stat().st_size} bytes)")
        return False
    
    return True


def clean_search_query(query: str) -> str:
    """
    Clean search query for better matching.
    
    Args:
        query: Original search query
        
    Returns:
        Cleaned query
    """
    # Remove content in parentheses (often contains extra info)
    query = re.sub(r'\([^)]*\)', '', query)
    
    # Remove content in brackets
    query = re.sub(r'\[[^\]]*\]', '', query)
    
    # Remove "feat.", "ft.", "featuring"
    query = re.sub(r'\b(feat\.|ft\.|featuring)\b.*', '', query, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    query = re.sub(r'\s+', ' ', query).strip()
    
    return query


def calculate_eta(completed: int, total: int, elapsed_seconds: float) -> str:
    """
    Calculate estimated time of arrival.
    
    Args:
        completed: Number of completed items
        total: Total number of items
        elapsed_seconds: Time elapsed so far
        
    Returns:
        Formatted ETA string
    """
    if completed == 0 or total == 0:
        return "calculating..."
    
    remaining = total - completed
    avg_time_per_item = elapsed_seconds / completed
    eta_seconds = int(remaining * avg_time_per_item)
    
    return format_duration(eta_seconds)


def get_duplicate_filename(file_path: Path) -> Path:
    """
    Generate a new filename for duplicate file.
    
    Args:
        file_path: Original file path
        
    Returns:
        New file path with suffix
    """
    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent
    
    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def batch_list(items: List, batch_size: int) -> List[List]:
    """
    Split list into batches.
    
    Args:
        items: List of items
        batch_size: Size of each batch
        
    Returns:
        List of batches
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def safe_int(value, default: int = 0) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

# Made with Bob
