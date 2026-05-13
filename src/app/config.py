"""
Глобальная конфигурация приложения.

Управление настройками и параметрами приложения.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os
import yaml


@dataclass
class SpotifyConfig:
    """Конфигурация Spotify API."""
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8888/callback"


@dataclass
class DownloadConfig:
    """Конфигурация загрузки."""
    output_dir: Path = Path("downloads")
    format: str = "mp3"
    quality: str = "320"
    max_retries: int = 3
    max_concurrent: int = 3
    skip_existing: bool = True
    create_playlist_file: bool = True


@dataclass
class CacheConfig:
    """Конфигурация кеширования."""
    spotify_dir: Path = Path(".spotify_cache")
    youtube_dir: Path = Path(".youtube_cache")
    max_age_days: int = 30
    enabled: bool = True


@dataclass
class SearchConfig:
    """Конфигурация поиска."""
    max_results: int = 5
    strategy: str = "default"  # default, fast, thorough
    use_isrc: bool = True


@dataclass
class MetadataConfig:
    """Конфигурация метаданных."""
    download_artwork: bool = True
    embed_lyrics: bool = False
    preserve_original: bool = False


@dataclass
class YoutubeConfig:
    """Конфигурация YouTube."""
    cookiesfrombrowser: Optional[str] = None


@dataclass
class LoggingConfig:
    """Конфигурация логирования."""
    verbose: bool = False
    file: Path = Path("spotify_downloader.log")
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class AppConfig:
    """Главная конфигурация приложения."""
    spotify: SpotifyConfig
    download: DownloadConfig = field(default_factory=DownloadConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    youtube: YoutubeConfig = field(default_factory=YoutubeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "AppConfig":
        """
        Загрузить конфигурацию из YAML файла.
        
        Args:
            config_path: Путь к файлу конфигурации
            
        Returns:
            Объект конфигурации
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(
            spotify=SpotifyConfig(**data.get('spotify', {})),
            download=DownloadConfig(**data.get('download', {})),
            cache=CacheConfig(**data.get('cache', {})),
            search=SearchConfig(**data.get('search', {})),
            metadata=MetadataConfig(**data.get('metadata', {})),
            youtube=YoutubeConfig(**data.get('youtube', {})),
            logging=LoggingConfig(**data.get('logging', {}))
        )
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Загрузить конфигурацию из переменных окружения.
        
        Returns:
            Объект конфигурации
        """
        return cls(
            spotify=SpotifyConfig(
                client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
                redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
            ),
            download=DownloadConfig(
                output_dir=Path(os.getenv("DOWNLOAD_DIR", "downloads")),
                format=os.getenv("AUDIO_FORMAT", "mp3"),
                quality=os.getenv("AUDIO_QUALITY", "320"),
                max_concurrent=int(os.getenv("MAX_CONCURRENT", "3"))
            )
        )
    
    def to_yaml(self, config_path: Path):
        """
        Сохранить конфигурацию в YAML файл.
        
        Args:
            config_path: Путь для сохранения
        """
        data = {
            'spotify': {
                'client_id': self.spotify.client_id,
                'client_secret': self.spotify.client_secret,
                'redirect_uri': self.spotify.redirect_uri
            },
            'download': {
                'output_dir': str(self.download.output_dir),
                'format': self.download.format,
                'quality': self.download.quality,
                'max_retries': self.download.max_retries,
                'max_concurrent': self.download.max_concurrent,
                'skip_existing': self.download.skip_existing,
                'create_playlist_file': self.download.create_playlist_file
            },
            'cache': {
                'spotify_dir': str(self.cache.spotify_dir),
                'youtube_dir': str(self.cache.youtube_dir),
                'max_age_days': self.cache.max_age_days,
                'enabled': self.cache.enabled
            },
            'search': {
                'max_results': self.search.max_results,
                'strategy': self.search.strategy,
                'use_isrc': self.search.use_isrc
            },
            'metadata': {
                'download_artwork': self.metadata.download_artwork,
                'embed_lyrics': self.metadata.embed_lyrics,
                'preserve_original': self.metadata.preserve_original
            },
            'logging': {
                'verbose': self.logging.verbose,
                'file': str(self.logging.file),
                'level': self.logging.level,
                'format': self.logging.format
            }
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def validate(self) -> bool:
        """
        Валидировать конфигурацию.
        
        Returns:
            True если конфигурация валидна
            
        Raises:
            ValueError: Если конфигурация невалидна
        """
        if not self.spotify.client_id or not self.spotify.client_secret:
            raise ValueError("Spotify credentials are required")
        
        if self.download.quality not in ["128", "192", "256", "320"]:
            raise ValueError(f"Invalid quality: {self.download.quality}")
        
        if self.download.format not in ["mp3", "flac", "m4a"]:
            raise ValueError(f"Invalid format: {self.download.format}")
        
        if self.download.max_concurrent < 1 or self.download.max_concurrent > 10:
            raise ValueError("max_concurrent must be between 1 and 10")
        
        return True


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Загрузить конфигурацию из файла или переменных окружения.
    
    Args:
        config_path: Путь к файлу конфигурации (опционально)
        
    Returns:
        Объект конфигурации
    """
    if config_path and config_path.exists():
        return AppConfig.from_yaml(config_path)
    
    # Пробуем загрузить из стандартных мест
    default_paths = [
        Path("config/default_config.yaml"),
        Path("config.yaml"),
        Path(".config/spotify_downloader.yaml")
    ]
    
    for path in default_paths:
        if path.exists():
            return AppConfig.from_yaml(path)
    
    # Загружаем из переменных окружения
    return AppConfig.from_env()

# Made with Bob
