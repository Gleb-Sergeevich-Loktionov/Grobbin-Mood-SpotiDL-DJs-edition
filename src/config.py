"""
Configuration Manager for Spotify Playlist Downloader.
Handles loading and validation of configuration from environment variables and YAML files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the application."""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default_config.yaml"
    
    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to custom YAML configuration file
            env_file: Path to custom .env file
        """
        self.config: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}
        
        # Load environment variables
        self._load_env_vars(env_file)
        
        # Load YAML configuration
        self._load_yaml_config(config_path)
        
        # Validate configuration
        self.validate_config()
        
    def _load_env_vars(self, env_file: Optional[str] = None) -> None:
        """
        Load environment variables from .env file.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Store relevant environment variables
        env_keys = [
            'SPOTIPY_CLIENT_ID',
            'SPOTIPY_CLIENT_SECRET',
            'SPOTIPY_REDIRECT_URI',
            'DEFAULT_OUTPUT_DIR',
            'DEFAULT_AUDIO_FORMAT',
            'DEFAULT_AUDIO_QUALITY',
            'MAX_CONCURRENT_DOWNLOADS',
            'LOG_LEVEL',
            'LOG_FILE',
            'RETRY_ATTEMPTS',
            'REQUEST_TIMEOUT',
            'ENABLE_CACHE',
            'CACHE_TTL'
        ]
        
        for key in env_keys:
            value = os.getenv(key)
            if value:
                self.env_vars[key] = value
                
        logger.debug(f"Loaded {len(self.env_vars)} environment variables")
    
    def _load_yaml_config(self, config_path: Optional[str] = None) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML config file (default: config/default_config.yaml)
        """
        yaml_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        
        if not yaml_path.exists():
            logger.warning(f"Config file not found: {yaml_path}. Using defaults.")
            self.config = self._get_default_config()
            return
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {yaml_path}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if YAML file is not available."""
        return {
            'download': {
                'format': 'mp3',
                'quality': {'mp3': 320, 'm4a': 256, 'flac': 'lossless'},
                'concurrent_downloads': 3,
                'retry_attempts': 3,
                'retry_delay': 2,
                'timeout': 300,
                'skip_existing': True
            },
            'metadata': {
                'embed_artwork': True,
                'artwork_min_size': 500,
                'artwork_preferred_size': 1000,
                'normalize_filenames': True,
                'filename_template': '{track_number:02d} - {artist} - {title}'
            },
            'youtube': {
                'search_templates': [
                    '{artist} - {title} official audio',
                    '{artist} - {title} audio',
                    '{artist} {title} lyrics',
                    '{title} {artist}'
                ],
                'duration_tolerance': 10,
                'prefer_official': True,
                'avoid_live': True,
                'avoid_covers': True
            },
            'organization': {
                'create_playlist_dirs': True,
                'generate_m3u': True,
                'duplicate_handling': 'rename'
            },
            'logging': {
                'level': 'INFO',
                'log_to_file': True,
                'log_file': 'spotify_downloader.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'failed_tracks_log': 'failed_tracks.log'
            },
            'progress': {
                'show_progress': True,
                'show_speed': True,
                'show_eta': True,
                'colored_output': True
            },
            'cache': {
                'enabled': True,
                'directory': '.cache',
                'ttl': 3600
            },
            'rate_limit': {
                'spotify_calls_per_minute': 100,
                'youtube_calls_per_minute': 60,
                'download_rate_limit': 0
            }
        }
    
    def validate_config(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Check Spotify credentials
        if not self.get_spotify_credentials()[0]:
            raise ValueError(
                "Spotify API credentials not found. "
                "Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in .env file."
            )
        
        # Validate audio format
        audio_format = self.get('download.format', 'mp3')
        if audio_format not in ['mp3', 'm4a', 'flac']:
            raise ValueError(f"Invalid audio format: {audio_format}")
        
        # Validate concurrent downloads
        concurrent = self.get('download.concurrent_downloads', 3)
        if not isinstance(concurrent, int) or concurrent < 1 or concurrent > 10:
            raise ValueError(f"Invalid concurrent_downloads: {concurrent}. Must be between 1 and 10.")
        
        logger.info("Configuration validated successfully")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'download.format')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check environment variables first (with priority)
        env_key = key.upper().replace('.', '_')
        if env_key in self.env_vars:
            return self._convert_type(self.env_vars[env_key])
        
        # Navigate through nested dictionary
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _convert_type(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        return value
    
    def get_spotify_credentials(self) -> Tuple[str, str]:
        """
        Get Spotify API credentials.
        
        Returns:
            Tuple of (client_id, client_secret)
        """
        client_id = self.env_vars.get('SPOTIPY_CLIENT_ID', '')
        client_secret = self.env_vars.get('SPOTIPY_CLIENT_SECRET', '')
        return client_id, client_secret
    
    def get_spotify_redirect_uri(self) -> str:
        """Get Spotify redirect URI."""
        return self.env_vars.get('SPOTIPY_REDIRECT_URI', 'http://localhost:8888/callback')
    
    def get_output_dir(self) -> Path:
        """
        Get output directory path.
        
        Returns:
            Path object for output directory
        """
        output_dir = self.env_vars.get('DEFAULT_OUTPUT_DIR') or self.get('download.output_dir', './downloads')
        return Path(output_dir).expanduser().resolve()
    
    def get_download_settings(self) -> Dict[str, Any]:
        """
        Get all download-related settings.
        
        Returns:
            Dictionary of download settings
        """
        return {
            'format': self.env_vars.get('DEFAULT_AUDIO_FORMAT') or self.get('download.format', 'mp3'),
            'quality': int(self.env_vars.get('DEFAULT_AUDIO_QUALITY', 320)),
            'concurrent_downloads': int(self.env_vars.get('MAX_CONCURRENT_DOWNLOADS', 3)),
            'retry_attempts': int(self.env_vars.get('RETRY_ATTEMPTS', 3)),
            'timeout': int(self.env_vars.get('REQUEST_TIMEOUT', 300)),
            'skip_existing': self.get('download.skip_existing', True)
        }
    
    def get_metadata_settings(self) -> Dict[str, Any]:
        """Get metadata-related settings."""
        return {
            'embed_artwork': self.get('metadata.embed_artwork', True),
            'artwork_min_size': self.get('metadata.artwork_min_size', 500),
            'artwork_preferred_size': self.get('metadata.artwork_preferred_size', 1000),
            'normalize_filenames': self.get('metadata.normalize_filenames', True),
            'filename_template': self.get('metadata.filename_template', '{track_number:02d} - {artist} - {title}')
        }
    
    def get_youtube_settings(self) -> Dict[str, Any]:
        """Get YouTube matching settings."""
        return {
            'search_templates': self.get('youtube.search_templates', [
                '{artist} - {title} official audio',
                '{artist} - {title} audio'
            ]),
            'duration_tolerance': self.get('youtube.duration_tolerance', 10),
            'prefer_official': self.get('youtube.prefer_official', True),
            'avoid_live': self.get('youtube.avoid_live', True),
            'avoid_covers': self.get('youtube.avoid_covers', True)
        }
    
    def get_logging_settings(self) -> Dict[str, Any]:
        """Get logging settings."""
        return {
            'level': self.env_vars.get('LOG_LEVEL') or self.get('logging.level', 'INFO'),
            'log_to_file': self.get('logging.log_to_file', True),
            'log_file': self.env_vars.get('LOG_FILE') or self.get('logging.log_file', 'spotify_downloader.log'),
            'format': self.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            'failed_tracks_log': self.get('logging.failed_tracks_log', 'failed_tracks.log')
        }
    
    def get_cache_settings(self) -> Dict[str, Any]:
        """Get cache settings."""
        return {
            'enabled': self.env_vars.get('ENABLE_CACHE', 'true').lower() == 'true',
            'directory': self.get('cache.directory', '.cache'),
            'ttl': int(self.env_vars.get('CACHE_TTL', 3600))
        }
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(spotify_configured={bool(self.get_spotify_credentials()[0])}, format={self.get('download.format')})"

# Made with Bob
