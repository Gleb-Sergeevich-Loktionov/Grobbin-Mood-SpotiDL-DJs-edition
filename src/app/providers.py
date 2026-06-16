"""
Dependency Injection Container.

Централизованное управление зависимостями приложения.
"""

from dependency_injector import containers, providers
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

# Загрузить переменные окружения из .env файла
load_dotenv()


class Container(containers.DeclarativeContainer):
    """Главный DI контейнер приложения."""
    
    # Конфигурация (dict для dependency-injector)
    config = providers.Configuration()
    
    # AppConfig объект (создается из config dict)
    app_config = providers.Singleton(
        "src.app.config.AppConfig",
        spotify=providers.Factory(
            "src.app.config.SpotifyConfig",
            client_id=config.spotify.client_id,
            client_secret=config.spotify.client_secret,
            redirect_uri=config.spotify.redirect_uri
        ),
        download=providers.Factory(
            "src.app.config.DownloadConfig",
            output_dir=config.download.output_dir,
            format=config.download.format,
            quality=config.download.quality,
            max_retries=config.download.max_retries,
            max_concurrent=config.download.max_concurrent,
            skip_existing=config.download.skip_existing,
            create_playlist_file=config.download.create_playlist_file
        ),
        cache=providers.Factory(
            "src.app.config.CacheConfig",
            spotify_dir=config.cache.spotify_dir,
            youtube_dir=config.cache.youtube_dir,
            max_age_days=config.cache.max_age_days,
            enabled=config.cache.enabled
        ),
        search=providers.Factory(
            "src.app.config.SearchConfig",
            max_results=config.search.max_results,
            strategy=config.search.strategy,
            use_isrc=config.search.use_isrc
        ),
        metadata=providers.Factory(
            "src.app.config.MetadataConfig",
            download_artwork=config.metadata.download_artwork,
            embed_lyrics=config.metadata.embed_lyrics,
            preserve_original=config.metadata.preserve_original
        ),
        logging=providers.Factory(
            "src.app.config.LoggingConfig",
            verbose=config.logging.verbose,
            file=config.logging.file,
            level=config.logging.level,
            format=config.logging.format
        )
    )
    
    # ============================================================================
    # SHARED LAYER - Общие компоненты
    # ============================================================================
    
    # Логгер
    logger = providers.Singleton(
        "logging.getLogger",
        name="spotify_downloader"
    )
    
    # Progress Subject для отслеживания прогресса
    progress_subject = providers.Factory(
        "src.shared.lib.observers.ProgressSubject"
    )
    
    # Console Observer
    console_observer = providers.Factory(
        "src.shared.lib.observers.ConsoleObserver",
        verbose=config.logging.verbose
    )
    
    # File Observer для логирования
    file_observer = providers.Factory(
        "src.shared.lib.observers.FileObserver",
        log_file=config.logging.file
    )
    
    # ============================================================================
    # SPOTIFY FEATURE - Работа с Spotify API
    # ============================================================================
    
    # Spotify Client (новая инфраструктура)
    spotify_client = providers.Singleton(
        "src.features.spotify.infrastructure.spotify_client.SpotifyClient",
        client_id=config.spotify.client_id,
        client_secret=config.spotify.client_secret,
        redirect_uri=config.spotify.redirect_uri
    )
    
    # Playlist Repository
    playlist_repository = providers.Factory(
        "src.features.spotify.infrastructure.spotify_client.SpotifyPlaylistRepository",
        client=spotify_client
    )
    
    # Track Repository
    track_repository = providers.Factory(
        "src.features.spotify.infrastructure.spotify_client.SpotifyTrackRepository",
        client=spotify_client
    )
    
    # Legacy Spotify Client для обратной совместимости
    legacy_spotify_client = providers.Singleton(
        "src.legacy.spotify_adapter.SpotifyClient",
        client_id=config.spotify.client_id,
        client_secret=config.spotify.client_secret
    )
    
    # ============================================================================
    # DOWNLOAD FEATURE - Загрузка треков
    # ============================================================================
    
    # YouTube Cache (обновленный путь)
    # Конструктор принимает: cache_dir (str), ttl (int в секундах)
    youtube_cache = providers.Singleton(
        "src.shared.lib.cache.YouTubeCache",
        cache_dir=config.cache.youtube_dir,
        ttl=86400  # 24 часа в секундах (можно сделать config.cache.ttl если нужно)
    )
    
    # Matching Strategy
    matching_strategy = providers.Singleton(
        "src.features.download.domain.strategies.MatchingStrategyFactory"
    )
    
    # File Manager (обновленный путь)
    # Конструктор принимает: base_output_dir (str)
    file_manager = providers.Factory(
        "src.shared.lib.file_manager.FileManager",
        base_output_dir=config.download.output_dir
    )
    
    # Progress Tracker (перемещен сюда, чтобы использовать в download_manager)
    # Конструктор принимает: total_playlists (int), colored_output (bool)
    # Примечание: total_playlists будет передан при создании экземпляра
    progress_tracker = providers.Factory(
        "src.shared.ui.progress.ProgressTracker",
        total_playlists=1,  # Значение по умолчанию, будет переопределено при использовании
        colored_output=True
    )
    
    # YouTube Matcher
    # Конструктор принимает: config (AppConfig)
    youtube_matcher = providers.Singleton(
        "src.features.download.infrastructure.youtube_matcher.YouTubeMatcher",
        config=app_config
    )
    
    # Metadata Handler
    # Конструктор принимает: config (AppConfig)
    metadata_handler = providers.Singleton(
        "src.features.metadata.infrastructure.metadata_handler.MetadataHandler",
        config=app_config
    )
    
    # Download Manager (использует legacy client для совместимости с текущим API)
    download_manager = providers.Factory(
        "src.features.download.infrastructure.download_manager.DownloadManager",
        config=app_config,
        spotify_client=legacy_spotify_client,
        progress_tracker=progress_tracker,
        youtube_matcher=youtube_matcher,
        metadata_handler=metadata_handler,
        file_manager=file_manager
    )
    
    # ============================================================================
    # METADATA FEATURE - Работа с метаданными
    # ============================================================================
    
    # Metadata Service (закомментирован, так как модуль не существует)
    # metadata_service = providers.Factory(
    #     "src.features.metadata.domain.services.MetadataService",
    #     handler=metadata_handler
    # )
    
    # ============================================================================
    # WIDGETS - UI компоненты
    # ============================================================================
    
    # Setup Wizard (обновленный путь)
    # Конструктор не принимает параметров
    setup_wizard = providers.Factory(
        "src.widgets.setup_wizard.wizard.SetupWizard"
    )
    
    # Progress Tracker (дубликат удален, используется определение выше на строке 112)
    
    # CLI Interface (использует новый spotify_client для аутентификации)
    # download_manager внутри использует legacy_spotify_client
    cli = providers.Factory(
        "src.shared.ui.cli.CLI",
        config=app_config,
        spotify_client=spotify_client,
        download_manager=download_manager,
        progress_tracker=progress_tracker,
        legacy_spotify_client=legacy_spotify_client
    )
    
    # ============================================================================
    # APP LAYER - Слой приложения
    # ============================================================================
    
    # Application Service (главный сервис приложения)
    # Закомментирован, так как модуль не существует
    # app_service = providers.Factory(
    #     "src.app.services.ApplicationService",
    #     playlist_repository=playlist_repository,
    #     track_repository=track_repository,
    #     download_manager=download_manager,
    #     progress_subject=progress_subject
    # )


class TestContainer(containers.DeclarativeContainer):
    """DI контейнер для тестов с моками."""
    
    config = providers.Configuration()
    
    # Mock Spotify Client
    spotify_client = providers.Singleton(
        "unittest.mock.Mock"
    )
    
    # Mock YouTube Matcher
    youtube_matcher = providers.Factory(
        "unittest.mock.Mock"
    )
    
    # Mock Downloader
    downloader = providers.Factory(
        "unittest.mock.Mock"
    )
    
    # Mock Progress Subject
    progress_subject = providers.Factory(
        "unittest.mock.Mock"
    )


def create_container(config_path: Optional[str] = None) -> Container:
    """
    Создать и настроить DI контейнер.
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        Настроенный контейнер
    """
    container = Container()
    
    # Загрузка конфигурации
    if config_path and os.path.exists(config_path):
        container.config.from_yaml(config_path)
    else:
        # Конфигурация по умолчанию
        container.config.from_dict({
            "spotify": {
                "client_id": os.getenv("SPOTIPY_CLIENT_ID", ""),
                "client_secret": os.getenv("SPOTIPY_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
            },
            "download": {
                "output_dir": os.getenv("DEFAULT_OUTPUT_DIR", "downloads"),
                "format": os.getenv("DEFAULT_AUDIO_FORMAT", "mp3"),
                "quality": os.getenv("DEFAULT_AUDIO_QUALITY", "320"),
                "max_retries": int(os.getenv("RETRY_ATTEMPTS", "3")),
                "max_concurrent": int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
            },
            "cache": {
                "spotify_dir": ".spotify_cache",
                "youtube_dir": ".youtube_cache",
                "max_age_days": 30
            },
            "search": {
                "max_results": 5
            },
            "metadata": {
                "download_artwork": True
            },
            "logging": {
                "verbose": False,
                "file": "spotify_downloader.log"
            },
            "paths": {
                "config_file": "config/default_config.yaml"
            }
        })
    
    return container


def create_test_container() -> TestContainer:
    """
    Создать тестовый контейнер с моками.
    
    Returns:
        Тестовый контейнер
    """
    container = TestContainer()
    container.config.from_dict({
        "test": True
    })
    return container


# Глобальный экземпляр контейнера (ленивая инициализация)
_container: Optional[Container] = None


def get_container() -> Container:
    """
    Получить глобальный экземпляр контейнера.
    
    Returns:
        DI контейнер
    """
    global _container
    if _container is None:
        _container = create_container()
    return _container


def reset_container():
    """Сбросить глобальный контейнер (для тестов)."""
    global _container
    _container = None

# Made with Bob
