"""
Command-line interface for Spotify Playlist Downloader.
Refactored to support Dependency Injection.
"""

import sys
import os
import argparse
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
import signal
from colorama import Fore, Style, init

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        # Try to set console to UTF-8
        os.system('chcp 65001 >nul 2>&1')
        # Set stdout encoding to UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass  # Fallback to default encoding

# Initialize colorama
init(autoreset=True)

# Version
__version__ = "1.0.0"

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle shutdown signals (CTRL+C)."""
    global shutdown_requested
    print("\n\n[WARNING] Shutdown requested. Completing current downloads...")
    shutdown_requested = True


class CLI:
    """
    Command-line interface class with Dependency Injection support.
    
    Attributes:
        config: Application configuration
        spotify_client: Spotify API client
        download_manager: Download manager
        progress_tracker: Progress tracker
    """
    
    def __init__(
        self,
        config,
        spotify_client,
        download_manager,
        progress_tracker,
        legacy_spotify_client=None
    ):
        """
        Initialize CLI with dependencies.
        
        Args:
            config: Application configuration
            spotify_client: Spotify API client (new)
            download_manager: Download manager
            progress_tracker: Progress tracker
            legacy_spotify_client: Legacy Spotify client (for download_manager)
        """
        self.config = config
        self.spotify_client = spotify_client
        self.download_manager = download_manager
        self.progress_tracker = progress_tracker
        self.legacy_spotify_client = legacy_spotify_client
        self.logger = logging.getLogger(__name__)
    
    def run(self) -> int:
        """
        Run the CLI application.
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Parse arguments
        args = self.parse_arguments()
        
        # Handle special commands
        if args.setup:
            return self.run_setup_wizard()
        
        if args.check:
            return self.check_configuration()
        
        if args.update:
            return self.update_ytdlp()
        
        # Require playlist input for download operations
        if not args.playlist and not args.playlists:
            print(f"{Fore.RED}Ошибка: Требуется --playlist или --playlists{Style.RESET_ALL}")
            print(f"\nИспользуйте --help для справки")
            print(f"Или запустите --setup для первоначальной настройки")
            return 1
        
        try:
            # Override config with command-line arguments
            self.apply_cli_overrides(args)
            
            # Setup logging
            self.setup_logging(args)
            
            # Print banner
            if not args.quiet:
                self.print_banner()
                print()
            
            # Get and validate playlist URLs
            playlist_urls = self.get_playlist_urls(args)
            
            if not playlist_urls:
                print("ERROR: No valid playlist URLs found")
                return 1
            
            print(f"Found {len(playlist_urls)} playlist(s) to download\n")
            
            # Authenticate with Spotify
            if not self.authenticate_spotify():
                return 1
            
            # Download playlists
            return self.download_playlists(playlist_urls, args)
        
        except KeyboardInterrupt:
            print("\n\n[WARNING] Interrupted by user")
            return 130
        
        except Exception as e:
            print(f"\n[ERROR] Fatal error: {e}")
            self.logger.exception("Fatal error occurred")
            return 1
    
    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command-line arguments.
        
        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description='Spotify Playlist Downloader - Download Spotify playlists as audio files',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # First time setup
  python main.py --setup
  
  # Download single playlist
  python main.py --playlist "https://open.spotify.com/playlist/..."
  
  # Download multiple playlists from file
  python main.py --playlists playlists.txt
  
  # Custom settings
  python main.py --playlist "..." --format flac --quality lossless --concurrent 5
  
  # Resume interrupted download
  python main.py --playlists playlists.txt --resume
  
  # Check configuration
  python main.py --check
  
  # Update yt-dlp
  python main.py --update
            """
        )
        
        # Playlist input
        input_group = parser.add_mutually_exclusive_group(required=False)
        input_group.add_argument(
            '--playlist',
            type=str,
            help='Single Spotify playlist URL'
        )
        input_group.add_argument(
            '--playlists',
            type=str,
            help='File containing playlist URLs (one per line)'
        )
        
        # Setup and maintenance commands
        input_group.add_argument(
            '--setup',
            action='store_true',
            help='Run interactive setup wizard'
        )
        input_group.add_argument(
            '--check',
            action='store_true',
            help='Check configuration and dependencies'
        )
        input_group.add_argument(
            '--update',
            action='store_true',
            help='Update yt-dlp to latest version'
        )
        
        # Output settings
        parser.add_argument(
            '--output',
            type=str,
            help='Output directory (default: ./downloads)'
        )
        
        # Audio settings
        parser.add_argument(
            '--format',
            type=str,
            choices=['mp3', 'm4a', 'flac'],
            help='Audio format (default: mp3)'
        )
        parser.add_argument(
            '--quality',
            type=str,
            help='Audio quality in kbps or "lossless" for FLAC (default: 320 for MP3)'
        )
        
        # Download settings
        parser.add_argument(
            '--concurrent',
            type=int,
            help='Number of concurrent downloads (default: 3)'
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume interrupted downloads'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip already downloaded tracks'
        )
        
        # Configuration
        parser.add_argument(
            '--config',
            type=str,
            help='Path to custom config file'
        )
        parser.add_argument(
            '--env',
            type=str,
            help='Path to custom .env file'
        )
        
        # Logging
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimal output'
        )
        
        # Version
        parser.add_argument(
            '--version',
            action='version',
            version=f'Spotify Playlist Downloader v{__version__}'
        )
        
        return parser.parse_args()
    
    def apply_cli_overrides(self, args: argparse.Namespace) -> None:
        """Apply command-line argument overrides to config and live components.

        The DI container builds config and the download manager before args are
        parsed, so overrides must update both the config object and the already-
        constructed download_manager's snapshotted settings.
        """
        cfg = self.config

        if args.output:
            cfg.download.output_dir = Path(args.output)
            if self.download_manager and getattr(self.download_manager, "file_manager", None):
                self.download_manager.file_manager.base_output_dir = Path(args.output)

        if args.format:
            cfg.download.format = args.format
            if self.download_manager:
                self.download_manager.download_settings['format'] = args.format

        if args.quality:
            cfg.download.quality = args.quality
            if self.download_manager:
                self.download_manager.download_settings['quality'] = args.quality

        if args.concurrent:
            cfg.download.max_concurrent = args.concurrent
            if self.download_manager:
                self.download_manager.download_settings['concurrent_downloads'] = args.concurrent
                self.download_manager.download_settings['max_concurrent'] = args.concurrent

        if args.skip_existing or args.resume:
            cfg.download.skip_existing = True
            if self.download_manager:
                self.download_manager.download_settings['skip_existing'] = True
    
    def setup_logging(self, args: argparse.Namespace) -> None:
        """Setup logging configuration."""
        log_level = logging.DEBUG if args.verbose else logging.INFO
        if args.quiet:
            log_level = logging.ERROR
        
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        handlers = [logging.StreamHandler()]
        
        # Add file handler if configured
        log_file = Path("spotify_downloader.log")
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers
        )
        
        # Suppress verbose logs from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('yt_dlp').setLevel(logging.WARNING)
    
    def print_banner(self) -> None:
        """Print application banner."""
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}
============================================================
    Spotify Playlist Downloader v{__version__}
    Download Spotify playlists in high quality
============================================================
{Style.RESET_ALL}"""
        print(banner)
    
    def get_playlist_urls(self, args: argparse.Namespace) -> List[str]:
        """Get and validate playlist URLs from arguments."""
        if args.playlist:
            urls = [args.playlist]
        else:
            urls = self.load_playlist_urls(args.playlists)
        
        return self.validate_playlist_urls(urls)
    
    def load_playlist_urls(self, file_path: str) -> List[str]:
        """Load playlist URLs from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return urls
        except Exception as e:
            print(f"[ERROR] Error reading playlist file: {e}")
            sys.exit(1)
    
    def validate_playlist_urls(self, urls: List[str]) -> List[str]:
        """Validate playlist URLs."""
        from src.shared.lib.utils import validate_url
        
        valid_urls = []
        for url in urls:
            if validate_url(url):
                valid_urls.append(url)
            else:
                print(f"[WARNING] Invalid URL, skipping: {url}")
        
        return valid_urls
    
    def authenticate_spotify(self) -> bool:
        """Authenticate with Spotify API."""
        # Аутентифицировать новый клиент
        if not self.spotify_client.authenticate():
            print("ERROR: Failed to authenticate with Spotify API")
            print("Please check your credentials in .env file")
            return False
        
        self.logger.info("Successfully authenticated with Spotify")
        
        # Также аутентифицировать legacy клиент для download_manager
        if self.legacy_spotify_client:
            if not self.legacy_spotify_client.authenticate():
                print("ERROR: Failed to authenticate legacy Spotify client")
                return False
            self.logger.info("Successfully authenticated legacy Spotify client")
        
        return True
    
    def download_playlists(self, playlist_urls: List[str], args: argparse.Namespace) -> int:
        """Download all playlists."""
        total_successful = 0
        total_failed = 0
        total_skipped = 0

        for i, playlist_url in enumerate(playlist_urls, 1):
            if shutdown_requested:
                print("\n[WARNING] Shutdown requested, stopping...")
                break
            
            self.logger.info(f"Processing playlist {i}/{len(playlist_urls)}: {playlist_url}")
            
            try:
                result = self.download_manager.download_playlist(playlist_url)
                total_successful += result.successful
                total_failed += result.failed
                total_skipped += result.skipped
                
                # Log failed tracks
                if result.failed_tracks:
                    self.log_failed_tracks(playlist_url, result.failed_tracks)
            
            except Exception as e:
                self.logger.error(f"Error processing playlist: {e}")
                self.progress_tracker.log_error(f"Failed to process playlist: {str(e)}")
        
        # Display final summary
        if not args.quiet:
            self.progress_tracker.display_final_summary(
                successful=total_successful,
                failed=total_failed,
                skipped=total_skipped,
            )
            
            if total_failed > 0:
                print(f"\nWARNING: {total_failed} track(s) failed. See failed_tracks.log for details.")
        
        return 0 if total_failed == 0 else 1
    
    def log_failed_tracks(self, playlist_url: str, failed_tracks: List[dict]) -> None:
        """Log failed tracks to file."""
        failed_log = Path("failed_tracks.log")
        with open(failed_log, 'a', encoding='utf-8') as f:
            f.write(f"\n# Playlist: {playlist_url}\n")
            for failed in failed_tracks:
                f.write(f"{failed['track']}: {failed['error']}\n")
    
    def run_setup_wizard(self) -> int:
        """Run the setup wizard."""
        from src.widgets.setup_wizard.wizard import SetupWizard
        wizard = SetupWizard()
        success = wizard.run()
        return 0 if success else 1
    
    def check_configuration(self) -> int:
        """Check configuration and dependencies."""
        from src.widgets.setup_wizard.wizard import SetupWizard
        
        self.print_banner()
        print(f"\n{Fore.CYAN}Проверка конфигурации...{Style.RESET_ALL}\n")
        
        wizard = SetupWizard()
        
        # Check Python
        wizard._check_python_version()
        
        # Check FFmpeg
        wizard._check_ffmpeg()
        
        # Check .env file
        print(f"\n{Fore.CYAN}Проверка файла конфигурации...{Style.RESET_ALL}")
        if wizard.env_file.exists():
            print(f"{Fore.GREEN}✓ Файл .env найден{Style.RESET_ALL}")
            
            # Try to load config
            try:
                import os
                from dotenv import load_dotenv
                load_dotenv()
                client_id = os.getenv("SPOTIPY_CLIENT_ID", "")
                client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")

                if client_id and client_secret:
                    print(f"{Fore.GREEN}✓ Spotify credentials настроены{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}✗ Spotify credentials не найдены{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Запустите: python main.py --setup{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ Ошибка загрузки конфигурации: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}✗ Файл .env не найден{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Запустите: python main.py --setup{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}Проверка завершена!{Style.RESET_ALL}\n")
        return 0
    
    def update_ytdlp(self) -> int:
        """Update yt-dlp to latest version."""
        self.print_banner()
        print(f"\n{Fore.CYAN}Обновление yt-dlp...{Style.RESET_ALL}\n")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}✓ yt-dlp успешно обновлен!{Style.RESET_ALL}")
                print(result.stdout)
                return 0
            else:
                print(f"{Fore.RED}✗ Ошибка обновления yt-dlp{Style.RESET_ALL}")
                print(result.stderr)
                return 1
        except subprocess.TimeoutExpired:
            print(f"{Fore.RED}✗ Превышено время ожидания обновления{Style.RESET_ALL}")
            return 1
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
            return 1


# Legacy main() function for backward compatibility
def main():
    """
    Legacy main function.
    Now uses DI container internally.
    """
    from src.app.providers import create_container
    
    try:
        # Create DI container
        container = create_container()
        
        # Get CLI from container
        cli = container.cli()
        
        # Run CLI
        return cli.run()
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logging.getLogger(__name__).debug("Critical error traceback", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
