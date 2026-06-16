"""
Download manager for Spotify Playlist Downloader.
Orchestrates the download process with concurrent execution.
"""

import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import urllib.error
import socket

from src.app.config import AppConfig
from src.features.spotify.infrastructure.spotify_client import SpotifyClient
from src.features.spotify.domain.repositories import SpotifyTrack, Playlist
from src.features.download.infrastructure.youtube_matcher import YouTubeMatcher
from src.features.metadata.infrastructure.metadata_handler import MetadataHandler
from src.shared.lib.file_manager import FileManager
from src.shared.ui.progress import ProgressTracker

logger = logging.getLogger(__name__)


def safe_str(text: str) -> str:
    """
    Convert string to ASCII-safe representation for Windows console.
    
    Args:
        text: Input string that may contain Unicode characters
        
    Returns:
        ASCII-safe string
    """
    try:
        # Try to encode/decode to check if it's safe
        text.encode('ascii')
        return text
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Replace non-ASCII characters with '?'
        return text.encode('ascii', 'replace').decode('ascii')


class DownloadResult:
    """Result of a download operation."""
    
    def __init__(self):
        self.total_tracks = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.failed_tracks: List[Dict[str, str]] = []
        self.duration_seconds = 0.0
    
    def add_success(self):
        """Increment successful downloads."""
        self.successful += 1
    
    def add_failure(self, track_name: str, error: str):
        """Add failed download."""
        self.failed += 1
        self.failed_tracks.append({
            'track': track_name,
            'error': error
        })
    
    def add_skip(self):
        """Increment skipped tracks."""
        self.skipped += 1
    
    def __repr__(self) -> str:
        return f"DownloadResult(successful={self.successful}, failed={self.failed}, skipped={self.skipped})"


class DownloadManager:
    """Manages the download process for playlists."""
    
    def __init__(
        self,
        config: AppConfig,
        spotify_client: SpotifyClient,
        progress_tracker: ProgressTracker,
        youtube_matcher: YouTubeMatcher,
        metadata_handler: MetadataHandler,
        file_manager: FileManager
    ):
        """
        Initialize download manager.
        
        Args:
            config: Configuration object
            spotify_client: Authenticated Spotify client
            progress_tracker: Progress tracker instance
            youtube_matcher: YouTube matcher instance
            metadata_handler: Metadata handler instance
            file_manager: File manager instance
        """
        self.config = config
        self.spotify_client = spotify_client
        self.progress_tracker = progress_tracker
        self.youtube_matcher = youtube_matcher
        self.metadata_handler = metadata_handler
        self.file_manager = file_manager
        
        # Get settings from config
        self.download_settings = {
            'format': config.download.format,
            'quality': config.download.quality,
            'concurrent_downloads': config.download.max_concurrent,
            'skip_existing': config.download.skip_existing,
            'adaptive_concurrency': False,
            'min_concurrent': 3,
            'max_concurrent': config.download.max_concurrent
        }
        self.metadata_settings = {
            'download_artwork': config.metadata.download_artwork,
            'embed_lyrics': config.metadata.embed_lyrics,
            'filename_template': '{track_number:02d} - {artist} - {title}'
        }
        
        # Adaptive concurrency settings
        self.adaptive_concurrency = self.download_settings.get('adaptive_concurrency', False)
        self.min_concurrent = self.download_settings.get('min_concurrent', 3)
        self.max_concurrent = self.download_settings.get('max_concurrent', 8)
        self.current_concurrent = self.download_settings['concurrent_downloads']
        
        # Performance tracking for adaptive concurrency
        self._download_speeds = []
        self._speed_window_size = 10
        
        logger.info(f"Download manager initialized (adaptive: {self.adaptive_concurrency})")
    
    def download_playlist(self, playlist_url: str) -> DownloadResult:
        """
        Download entire playlist.
        
        Args:
            playlist_url: Spotify playlist URL
            
        Returns:
            DownloadResult object
        """
        start_time = time.time()
        result = DownloadResult()
        
        try:
            # Get playlist info
            playlist_info = self.spotify_client.get_playlist_info(playlist_url)
            logger.info(f"Starting download for playlist: {playlist_info.name}")
            
            # Get all tracks
            tracks = self.spotify_client.get_playlist_tracks(playlist_info.id)
            result.total_tracks = len(tracks)
            
            if not tracks:
                logger.warning("No tracks found in playlist")
                return result
            
            # Create playlist directory
            playlist_dir = self.file_manager.create_playlist_directory(playlist_info.name)
            logger.debug(f"Playlist directory created/retrieved: {playlist_dir}")
            logger.debug(f"Playlist directory exists: {playlist_dir.exists()}")
            
            # Check for resume state
            resume_state = self.file_manager.load_resume_state(playlist_info.id)
            completed_track_ids = set()
            
            if resume_state and self.download_settings.get('skip_existing'):
                completed_track_ids = set(resume_state.get('completed_tracks', []))
                logger.info(f"Resuming download, {len(completed_track_ids)} tracks already completed")
            
            # Start progress tracking
            self.progress_tracker.start_playlist(playlist_info.name, len(tracks))
            
            # Download tracks
            if self.download_settings['concurrent_downloads'] > 1:
                self._download_tracks_concurrent(
                    tracks,
                    playlist_dir,
                    playlist_info.id,
                    completed_track_ids,
                    result
                )
            else:
                self._download_tracks_sequential(
                    tracks,
                    playlist_dir,
                    playlist_info.id,
                    completed_track_ids,
                    result
                )
            
            # Generate M3U playlist
            if self.config.download.create_playlist_file:
                track_files = list(playlist_dir.glob('*.mp3')) + \
                             list(playlist_dir.glob('*.m4a')) + \
                             list(playlist_dir.glob('*.flac'))
                self.file_manager.generate_m3u_playlist(
                    playlist_dir,
                    playlist_info.name,
                    sorted(track_files)
                )
            
            # Complete progress tracking
            self.progress_tracker.complete_playlist()
            
            # Clean up resume state if all successful
            if result.failed == 0:
                self.file_manager.delete_resume_state(playlist_info.id)
            
        except Exception as e:
            logger.error(f"Failed to download playlist: {e}")
            self.progress_tracker.log_error(str(e))
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def _download_tracks_sequential(
        self,
        tracks: List[SpotifyTrack],
        playlist_dir: Path,
        playlist_id: str,
        completed_track_ids: set,
        result: DownloadResult
    ) -> None:
        """Download tracks sequentially."""
        for i, track in enumerate(tracks, 1):
            if track.id in completed_track_ids:
                result.add_skip()
                continue
            
            success = self._download_single_track(track, i, playlist_dir)
            
            if success:
                result.add_success()
                completed_track_ids.add(track.id)
            else:
                result.add_failure(track.name, "Download failed")
            
            # Save resume state periodically
            if i % 5 == 0:
                self._save_resume_state(playlist_id, completed_track_ids, result.failed_tracks)
    
    def _download_tracks_concurrent(
        self,
        tracks: List[SpotifyTrack],
        playlist_dir: Path,
        playlist_id: str,
        completed_track_ids: set,
        result: DownloadResult
    ) -> None:
        """Download tracks concurrently with adaptive parallelism."""
        max_workers = self.current_concurrent if self.adaptive_concurrency else self.download_settings['concurrent_downloads']
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_track = {}
            
            for i, track in enumerate(tracks, 1):
                if track.id in completed_track_ids:
                    result.add_skip()
                    continue
                
                future = executor.submit(self._download_single_track, track, i, playlist_dir)
                future_to_track[future] = track
            
            # Process completed downloads
            completed_count = 0
            for future in as_completed(future_to_track):
                track = future_to_track[future]
                
                try:
                    success = future.result()
                    
                    if success:
                        result.add_success()
                        completed_track_ids.add(track.id)
                    else:
                        # Safe encoding for error logging
                        track_name_safe = safe_str(track.name)
                        result.add_failure(track_name_safe, "Download failed")
                
                except Exception as e:
                    # Safe encoding for error logging
                    track_name_safe = safe_str(track.name)
                    error_msg = safe_str(str(e))
                    
                    logger.error(f"Exception during download: {error_msg}")
                    result.add_failure(track_name_safe, error_msg)
                
                completed_count += 1
                
                # Adjust concurrency adaptively
                if self.adaptive_concurrency and completed_count % 5 == 0:
                    self._adjust_concurrency()
                
                # Save resume state periodically
                if (result.successful + result.failed) % 5 == 0:
                    self._save_resume_state(playlist_id, completed_track_ids, result.failed_tracks)
    
    def _download_single_track(
        self,
        track: SpotifyTrack,
        track_number: int,
        playlist_dir: Path
    ) -> bool:
        """
        Download a single track.
        
        Args:
            track: Track metadata
            track_number: Track number in playlist
            playlist_dir: Directory to save track
            
        Returns:
            True if successful
        """
        # Safe encoding for track name to avoid Windows console errors
        artist_safe = safe_str(track.artist)
        name_safe = safe_str(track.name)
        track_name = f"{artist_safe} - {name_safe}"
        
        try:
            # Start track progress
            self.progress_tracker.start_track(track_name)
            
            logger.debug(f"Received playlist_dir for track: {playlist_dir}")
            
            # Generate output path FIRST (before YouTube search)
            output_path = self.file_manager.get_output_path(
                playlist_dir,
                track_number,
                track.artist,
                track.name,
                self.download_settings['format'],
                self.metadata_settings['filename_template']
            )
            logger.debug(f"Generated output_path: {output_path}")
            logger.debug(f"Output path parent directory: {output_path.parent}")
            
            # CRITICAL: Check if file already exists BEFORE YouTube search
            # This prevents unnecessary API calls and duplicate downloads
            if self.download_settings.get('skip_existing', True):
                existing_file = self._check_existing_file(output_path)
                if existing_file:
                    logger.info(f"✓ File already exists, skipping download: {existing_file.name}")
                    self.progress_tracker.complete_track(True)
                    return True
                else:
                    logger.info(f"✗ File not found, proceeding with download: {output_path.name}")
            
            # Search for track on YouTube (only if file doesn't exist)
            logger.info(f"Searching YouTube for: {track_name}")
            youtube_url = self.youtube_matcher.search_track(track)
            
            if not youtube_url:
                logger.warning(f"YouTube match not found for: {track_name}")
                self.progress_tracker.complete_track(False, "YouTube match not found")
                return False
            
            logger.info(f"Found YouTube match: {youtube_url}")
            logger.debug(f"Final output_path before yt-dlp: {output_path}")
            
            # Download with yt-dlp
            success = self._download_with_ytdlp(youtube_url, output_path)
            
            if not success:
                self.progress_tracker.complete_track(False, "Download failed")
                return False
            
            # Validate downloaded file
            if not self.file_manager.validate_file(output_path):
                logger.error(f"Downloaded file is invalid: {output_path}")
                self.file_manager.delete_file(output_path)
                self.progress_tracker.complete_track(False, "Invalid file")
                return False
            
            # Embed metadata
            artwork_url = track.album_art_url
            metadata_success = self.metadata_handler.embed_metadata(
                output_path,
                track,
                artwork_url
            )
            
            if not metadata_success:
                logger.warning(f"Failed to embed metadata for: {track_name}")
            
            self.progress_tracker.complete_track(True)
            logger.info(f"Successfully downloaded: {track_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error downloading track {track_name}: {e}")
            self.progress_tracker.complete_track(False, str(e))
            return False
    
    def _check_existing_file(self, file_path: Path) -> Optional[Path]:
        """
        Check if file already exists, including variations with suffixes like (1), (2), etc.
        
        This method performs comprehensive checks to detect existing files:
        1. Exact filename match
        2. Variations with (1), (2), (3), etc. suffixes
        3. Case-insensitive matches
        4. Files with extra spaces or formatting differences
        
        Args:
            file_path: Original file path to check
            
        Returns:
            Path to existing file if found, None otherwise
        """
        stem = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent
        
        # Ensure parent directory exists
        if not parent.exists():
            logger.debug(f"[DUPLICATE CHECK] Parent directory does not exist: {parent}")
            return None
        
        # 1. Check exact match first
        if file_path.exists():
            logger.info(f"[DUPLICATE CHECK] ✓ Found exact match: {file_path.name}")
            return file_path
        
        # 2. Check for variations with suffixes (1), (2), etc. up to 20
        logger.debug(f"[DUPLICATE CHECK] Checking for variations of: {stem}{suffix}")
        for i in range(1, 21):
            variation_path = parent / f"{stem} ({i}){suffix}"
            if variation_path.exists():
                logger.info(f"[DUPLICATE CHECK] ✓ Found variation with suffix ({i}): {variation_path.name}")
                return variation_path
        
        # 3. Check for similar files (case-insensitive, ignoring extra spaces)
        # This catches files that might have been renamed or have slight differences
        normalized_stem = stem.lower().replace(' ', '').replace('-', '')
        
        logger.debug(f"[DUPLICATE CHECK] Scanning directory for similar files...")
        files_checked = 0
        
        for existing_file in parent.glob(f"*{suffix}"):
            files_checked += 1
            existing_stem = existing_file.stem.lower().replace(' ', '').replace('-', '')
            
            # Remove potential (N) suffixes for comparison
            existing_stem_clean = re.sub(r'\(\d+\)$', '', existing_stem)
            
            if normalized_stem == existing_stem_clean:
                logger.info(f"[DUPLICATE CHECK] ✓ Found similar file: {existing_file.name}")
                return existing_file
        
        logger.debug(f"[DUPLICATE CHECK] ✗ No existing file found (checked {files_checked} files)")
        return None
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((
            urllib.error.URLError,
            socket.timeout,
            ConnectionError,
            TimeoutError
        ))
    )
    def _download_with_ytdlp(self, url: str, output_path: Path) -> bool:
        """
        Download audio using yt-dlp with optimized retry logic.
        Only retries on network errors.
        
        Args:
            url: YouTube video URL
            output_path: Output file path
            
        Returns:
            True if successful
        """
        import yt_dlp
        
        audio_format = self.download_settings['format']
        quality = self.download_settings['quality']
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_path.with_suffix('')),  # Without extension
            'quiet': True,
            'no_warnings': True,
            'extract_audio': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': str(quality) if audio_format != 'flac' else '0',
            }],
            'progress_hooks': [self._ytdlp_progress_hook],
            # Anti-bot protection bypass
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
        }
        
        # Add cookies from browser if configured
        if (hasattr(self.config, 'youtube') and
            hasattr(self.config.youtube, 'cookiesfrombrowser') and
            self.config.youtube.cookiesfrombrowser):
            cookies_browser = self.config.youtube.cookiesfrombrowser
            ydl_opts['cookiesfrombrowser'] = (cookies_browser,)
            logger.debug(f"Using cookies from browser: {cookies_browser}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            return True
        
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return False
    
    def _ytdlp_progress_hook(self, d: Dict[str, Any]) -> None:
        """
        Progress hook for yt-dlp with speed tracking for adaptive concurrency.
        
        Args:
            d: Progress dictionary from yt-dlp
        """
        if d['status'] == 'downloading':
            # Calculate progress percentage
            if 'total_bytes' in d and d['total_bytes'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                progress = 0
            
            # Calculate speed
            speed = d.get('speed', 0) or 0
            
            # Track speed for adaptive concurrency
            if speed > 0 and self.adaptive_concurrency:
                self._track_download_speed(speed)
            
            # Update progress tracker
            self.progress_tracker.update_track_progress(progress, speed)
    
    def _save_resume_state(
        self,
        playlist_id: str,
        completed_track_ids: set,
        failed_tracks: List[Dict[str, str]]
    ) -> None:
        """Save resume state."""
        state = {
            'playlist_id': playlist_id,
            'completed_tracks': list(completed_track_ids),
            'failed_tracks': failed_tracks
        }
        self.file_manager.save_resume_state(playlist_id, state)
    
    def _track_download_speed(self, speed: float) -> None:
        """
        Track download speed for adaptive concurrency.
        
        Args:
            speed: Download speed in bytes/second
        """
        self._download_speeds.append(speed)
        
        # Keep only recent speeds
        if len(self._download_speeds) > self._speed_window_size:
            self._download_speeds.pop(0)
    
    def _get_average_speed(self) -> float:
        """
        Get average download speed.
        
        Returns:
            Average speed in bytes/second
        """
        if not self._download_speeds:
            return 0.0
        return sum(self._download_speeds) / len(self._download_speeds)
    
    def _adjust_concurrency(self) -> None:
        """
        Adjust concurrency level based on download performance.
        Increases concurrency if speeds are good, decreases if poor.
        """
        if not self.adaptive_concurrency or len(self._download_speeds) < 3:
            return
        
        avg_speed = self._get_average_speed()
        
        # If we have recent speeds, compare with older speeds
        if len(self._download_speeds) >= 6:
            recent_avg = sum(self._download_speeds[-3:]) / 3
            older_avg = sum(self._download_speeds[-6:-3]) / 3
            
            # Speed improving - increase concurrency
            if recent_avg > older_avg * 1.1 and self.current_concurrent < self.max_concurrent:
                self.current_concurrent = min(self.current_concurrent + 1, self.max_concurrent)
                logger.info(f"Increasing concurrency to {self.current_concurrent}")
            
            # Speed degrading - decrease concurrency
            elif recent_avg < older_avg * 0.9 and self.current_concurrent > self.min_concurrent:
                self.current_concurrent = max(self.current_concurrent - 1, self.min_concurrent)
                logger.info(f"Decreasing concurrency to {self.current_concurrent}")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"DownloadManager(format={self.download_settings['format']}, concurrent={self.download_settings['concurrent_downloads']})"

# Made with Bob
