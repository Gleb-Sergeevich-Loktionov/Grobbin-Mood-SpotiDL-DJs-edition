"""
Progress tracking and display for Spotify Playlist Downloader.
"""

import time
from typing import Optional
from tqdm import tqdm
from colorama import Fore, Style, init
import logging

# Initialize colorama for Windows support
init(autoreset=True)

logger = logging.getLogger(__name__)


class OverallProgress:
    """Tracks overall progress across multiple playlists."""
    
    def __init__(self, total_playlists: int):
        """
        Initialize overall progress tracker.
        
        Args:
            total_playlists: Total number of playlists to process
        """
        self.total_playlists = total_playlists
        self.completed_playlists = 0
        self.total_tracks = 0
        self.completed_tracks = 0
        self.failed_tracks = 0
        self.start_time = time.time()
        
        # Statistics per playlist
        self.playlist_stats = []
    
    def add_playlist(self, name: str, total_tracks: int) -> None:
        """
        Add a new playlist to track.
        
        Args:
            name: Playlist name
            total_tracks: Total tracks in playlist
        """
        self.total_tracks += total_tracks
    
    def update_playlist_complete(self, successful: int, failed: int) -> None:
        """
        Mark current playlist as complete.
        
        Args:
            successful: Number of successful downloads
            failed: Number of failed downloads
        """
        self.completed_playlists += 1
        self.completed_tracks += successful
        self.failed_tracks += failed
    
    def get_overall_progress(self) -> float:
        """
        Get overall progress percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        if self.total_tracks == 0:
            return 0.0
        return (self.completed_tracks / self.total_tracks) * 100
    
    def get_playlist_progress(self) -> str:
        """
        Get playlist progress string.
        
        Returns:
            Progress string like "2/4 (50%)"
        """
        if self.total_playlists == 0:
            return "0/0"
        
        percentage = (self.completed_playlists / self.total_playlists) * 100
        return f"{self.completed_playlists}/{self.total_playlists} ({percentage:.0f}%)"
    
    def get_estimated_time_remaining(self) -> str:
        """
        Estimate time remaining based on current progress.
        
        Returns:
            Formatted time string
        """
        if self.completed_tracks == 0:
            return "Расчет..."
        
        elapsed = time.time() - self.start_time
        avg_time_per_track = elapsed / self.completed_tracks
        remaining_tracks = self.total_tracks - self.completed_tracks - self.failed_tracks
        
        if remaining_tracks <= 0:
            return "Завершено"
        
        estimated_seconds = remaining_tracks * avg_time_per_track
        
        from src.shared.lib.utils import format_duration
        return format_duration(int(estimated_seconds))
    
    def get_summary_line(self) -> str:
        """
        Get one-line summary of overall progress.
        
        Returns:
            Summary string
        """
        playlist_prog = self.get_playlist_progress()
        track_prog = f"{self.completed_tracks}/{self.total_tracks}"
        success_rate = f"OK: {self.completed_tracks}"
        fail_info = f"| Ошибки: {self.failed_tracks}" if self.failed_tracks > 0 else ""
        eta = f"| Осталось: {self.get_estimated_time_remaining()}"
        
        return f"Плейлисты: {playlist_prog} | Треки: {track_prog} | {success_rate} {fail_info} {eta}"


class ProgressTracker:
    """Tracks and displays download progress with multiple levels."""
    
    def __init__(self, total_playlists: int, colored_output: bool = True):
        """
        Initialize progress tracker.
        
        Args:
            total_playlists: Total number of playlists to process
            colored_output: Enable colored terminal output
        """
        self.total_playlists = total_playlists
        self.current_playlist = 0
        self.colored_output = colored_output
        
        # Overall progress tracking
        self.overall_progress = OverallProgress(total_playlists)
        
        # Playlist-level tracking
        self.playlist_name: Optional[str] = None
        self.total_tracks = 0
        self.completed_tracks = 0
        self.failed_tracks = 0
        
        # Track-level tracking
        self.current_track_name: Optional[str] = None
        self.track_start_time: Optional[float] = None
        self.playlist_start_time: Optional[float] = None
        
        # Progress bars
        self.overall_pbar: Optional[tqdm] = None
        self.playlist_pbar: Optional[tqdm] = None
        self.track_pbar: Optional[tqdm] = None
        
        # Statistics
        self.total_completed = 0
        self.total_failed = 0
        self.start_time = time.time()
    
    def start_playlist(self, playlist_name: str, total_tracks: int) -> None:
        """
        Start tracking a new playlist.
        
        Args:
            playlist_name: Name of the playlist
            total_tracks: Total number of tracks in playlist
        """
        self.current_playlist += 1
        self.playlist_name = playlist_name
        self.total_tracks = total_tracks
        self.completed_tracks = 0
        self.failed_tracks = 0
        self.playlist_start_time = time.time()
        
        # Update overall progress
        self.overall_progress.add_playlist(playlist_name, total_tracks)
        
        # Display playlist header
        self._print_playlist_header()
        
        # Create overall progress bar (only once)
        if self.overall_pbar is None and self.total_playlists > 1:
            overall_desc = self._colorize("Общий прогресс", Fore.MAGENTA)
            self.overall_pbar = tqdm(
                total=100,
                desc=overall_desc,
                unit="%",
                position=0,
                leave=True,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {postfix}'
            )
        
        # Create playlist progress bar
        desc = self._colorize(f"[{self.current_playlist}/{self.total_playlists}] {playlist_name}", Fore.CYAN)
        position = 1 if self.overall_pbar else 0
        self.playlist_pbar = tqdm(
            total=total_tracks,
            desc=desc,
            unit="track",
            position=position,
            leave=True,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
        )
        
        # Update overall progress bar
        if self.overall_pbar:
            self._update_overall_progress()
    
    def start_track(self, track_name: str) -> None:
        """
        Start tracking a new track download.
        
        Args:
            track_name: Name of the track
        """
        self.current_track_name = track_name
        self.track_start_time = time.time()
        
        # Create track progress bar
        desc = self._colorize(f"  ↳ {track_name[:50]}", Fore.WHITE)
        self.track_pbar = tqdm(
            total=100,
            desc=desc,
            unit="%",
            position=1,
            leave=False,
            bar_format='{l_bar}{bar}| {n_fmt}% [{rate_fmt}]'
        )
    
    def update_track_progress(self, progress: float, speed: Optional[float] = None) -> None:
        """
        Update current track download progress.
        
        Args:
            progress: Progress percentage (0-100)
            speed: Download speed in bytes/second
        """
        if self.track_pbar:
            # Update to the new progress value
            self.track_pbar.n = int(progress)
            
            # Update postfix with speed if available
            if speed:
                from src.shared.lib.utils import format_speed
                self.track_pbar.set_postfix_str(format_speed(speed))
            
            self.track_pbar.refresh()
    
    def complete_track(self, success: bool, error_msg: Optional[str] = None) -> None:
        """
        Mark current track as completed.
        
        Args:
            success: Whether track was downloaded successfully
            error_msg: Error message if failed
        """
        if self.track_pbar:
            self.track_pbar.close()
            self.track_pbar = None
        
        if success:
            self.completed_tracks += 1
            self.total_completed += 1
            status = self._colorize("[OK]", Fore.GREEN)
        else:
            self.failed_tracks += 1
            self.total_failed += 1
            status = self._colorize("[FAIL]", Fore.RED)
            if error_msg:
                logger.warning(f"Failed to download {self.current_track_name}: {error_msg}")
        
        # Update playlist progress bar
        if self.playlist_pbar:
            self.playlist_pbar.update(1)
            
            # Update description with status
            success_count = self._colorize(f"[OK]{self.completed_tracks}", Fore.GREEN)
            failed_count = self._colorize(f"[FAIL]{self.failed_tracks}", Fore.RED) if self.failed_tracks > 0 else ""
            status_str = f"{success_count} {failed_count}".strip()
            
            self.playlist_pbar.set_postfix_str(status_str)
    
    def complete_playlist(self) -> None:
        """Mark current playlist as completed and display summary."""
        if self.playlist_pbar:
            self.playlist_pbar.close()
            self.playlist_pbar = None
        
        # Update overall progress
        self.overall_progress.update_playlist_complete(
            self.completed_tracks,
            self.failed_tracks
        )
        
        # Calculate playlist statistics
        if self.playlist_start_time:
            elapsed = time.time() - self.playlist_start_time
            from src.shared.lib.utils import format_duration
            duration_str = format_duration(int(elapsed))
        else:
            duration_str = "unknown"
        
        # Display playlist summary
        self._print_playlist_summary(duration_str)
        
        # Update overall progress bar
        if self.overall_pbar:
            self._update_overall_progress()
        
        print()  # Empty line between playlists
    
    def _update_overall_progress(self) -> None:
        """Update overall progress bar with current statistics."""
        if not self.overall_pbar:
            return
        
        # Update progress percentage
        progress = self.overall_progress.get_overall_progress()
        self.overall_pbar.n = int(progress)
        
        # Update postfix with detailed stats
        summary = self.overall_progress.get_summary_line()
        self.overall_pbar.set_postfix_str(summary)
        self.overall_pbar.refresh()
    
    def display_final_summary(self, successful: int = None, failed: int = None, skipped: int = 0) -> None:
        """Display final summary of all downloads."""
        successful = self.total_completed if successful is None else successful
        failed = self.total_failed if failed is None else failed

        total_elapsed = time.time() - self.start_time
        from src.shared.lib.utils import format_duration

        print("\n" + "=" * 60)
        print(self._colorize("Download Summary", Fore.CYAN, Style.BRIGHT))
        print("=" * 60)

        print(f"Total playlists processed: {self.current_playlist}/{self.total_playlists}")
        print(f"{self._colorize('[OK] Successfully downloaded:', Fore.GREEN)} {successful} tracks")

        if failed > 0:
            print(f"{self._colorize('[FAIL] Failed downloads:', Fore.RED)} {failed} tracks")

        if skipped > 0:
            print(f"{self._colorize('[SKIP] Skipped (already downloaded):', Fore.YELLOW)} {skipped} tracks")

        print(f"⏱ Total time: {format_duration(int(total_elapsed))}")

        if successful > 0:
            avg_time = total_elapsed / successful
            print(f"⚡ Average time per track: {format_duration(int(avg_time))}")

        print("=" * 60)
    
    def _print_playlist_header(self) -> None:
        """Print playlist header."""
        print("\n" + "-" * 60)
        header = f"Playlist {self.current_playlist}/{self.total_playlists}: {self.playlist_name}"
        print(self._colorize(header, Fore.CYAN, Style.BRIGHT))
        print(f"   Tracks: {self.total_tracks}")
        print("-" * 60)
    
    def _print_playlist_summary(self, duration: str) -> None:
        """Print playlist completion summary."""
        print("-" * 60)
        print(self._colorize(f"Playlist completed: {self.playlist_name}", Fore.GREEN))
        print(f"   Downloaded: {self.completed_tracks}/{self.total_tracks}")
        
        if self.failed_tracks > 0:
            print(f"   Failed: {self.failed_tracks}")
        
        print(f"   Time: {duration}")
        print("-" * 60)
    
    def _colorize(self, text: str, *colors) -> str:
        """
        Apply color to text if colored output is enabled.
        
        Args:
            text: Text to colorize
            *colors: Color codes from colorama
            
        Returns:
            Colored text or plain text
        """
        if not self.colored_output:
            return text
        
        color_str = ''.join(colors)
        return f"{color_str}{text}{Style.RESET_ALL}"
    
    def log_error(self, message: str) -> None:
        """
        Log an error message.
        
        Args:
            message: Error message
        """
        error_msg = self._colorize(f"ERROR: {message}", Fore.RED, Style.BRIGHT)
        print(f"\n{error_msg}")
        logger.error(message)
    
    def log_warning(self, message: str) -> None:
        """
        Log a warning message.
        
        Args:
            message: Warning message
        """
        warning_msg = self._colorize(f"WARNING: {message}", Fore.YELLOW)
        print(f"\n{warning_msg}")
        logger.warning(message)
    
    def log_info(self, message: str) -> None:
        """
        Log an info message.
        
        Args:
            message: Info message
        """
        info_msg = self._colorize(message, Fore.CYAN)
        print(f"\n{info_msg}")
        logger.info(message)


class SimpleProgressTracker:
    """Simplified progress tracker without fancy UI (for non-TTY environments)."""
    
    def __init__(self, total_playlists: int):
        """Initialize simple progress tracker."""
        self.total_playlists = total_playlists
        self.current_playlist = 0
        self.playlist_name = ""
        self.total_tracks = 0
        self.completed_tracks = 0
        self.failed_tracks = 0
        self.start_time = time.time()
    
    def start_playlist(self, playlist_name: str, total_tracks: int) -> None:
        """Start tracking a new playlist."""
        self.current_playlist += 1
        self.playlist_name = playlist_name
        self.total_tracks = total_tracks
        self.completed_tracks = 0
        self.failed_tracks = 0
        print(f"\n[{self.current_playlist}/{self.total_playlists}] Processing playlist: {playlist_name}")
        print(f"Total tracks: {total_tracks}")
    
    def start_track(self, track_name: str) -> None:
        """Start tracking a new track."""
        print(f"  Downloading: {track_name}")
    
    def update_track_progress(self, progress: float, speed: Optional[float] = None) -> None:
        """Update track progress (no-op for simple tracker)."""
        pass
    
    def complete_track(self, success: bool, error_msg: Optional[str] = None) -> None:
        """Mark track as completed."""
        self.completed_tracks += 1
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} [{self.completed_tracks}/{self.total_tracks}]")
        if not success and error_msg:
            print(f"    Error: {error_msg}")
    
    def complete_playlist(self) -> None:
        """Mark playlist as completed."""
        print(f"\nPlaylist completed: {self.completed_tracks}/{self.total_tracks} successful")
        if self.failed_tracks > 0:
            print(f"Failed: {self.failed_tracks}")
    
    def display_final_summary(self) -> None:
        """Display final summary."""
        elapsed = time.time() - self.start_time
        from src.shared.lib.utils import format_duration
        print(f"\n{'='*60}")
        print(f"All downloads completed in {format_duration(int(elapsed))}")
        print(f"{'='*60}")
    
    def log_error(self, message: str) -> None:
        """Log error."""
        print(f"ERROR: {message}")
    
    def log_warning(self, message: str) -> None:
        """Log warning."""
        print(f"WARNING: {message}")
    
    def log_info(self, message: str) -> None:
        """Log info."""
        print(f"INFO: {message}")

# Made with Bob
