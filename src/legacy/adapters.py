"""
Legacy Adapters - адаптеры для обратной совместимости.

Предоставляет старый API для существующего кода, используя новую архитектуру.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import warnings

from src.app.providers import get_container
from src.features.download.domain.models import Track, DownloadResult


def _show_deprecation_warning(old_func: str, new_func: str):
    """Показать предупреждение об устаревшей функции."""
    warnings.warn(
        f"{old_func} is deprecated and will be removed in future versions. "
        f"Use {new_func} instead.",
        DeprecationWarning,
        stacklevel=3
    )


def download_playlist(
    playlist_url: str,
    output_dir: str = "downloads",
    format: str = "mp3",
    quality: str = "320",
    skip_existing: bool = True,
    max_retries: int = 3,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Загрузить плейлист (legacy API).
    
    DEPRECATED: Используйте новый API через DI контейнер.
    
    Args:
        playlist_url: URL плейлиста Spotify
        output_dir: Директория для сохранения
        format: Формат аудио (mp3, flac, m4a)
        quality: Качество (128, 192, 256, 320)
        skip_existing: Пропускать существующие файлы
        max_retries: Максимум попыток при ошибке
        verbose: Подробный вывод
        
    Returns:
        Словарь с результатами загрузки
    """
    _show_deprecation_warning(
        "download_playlist()",
        "container.app_service().download_playlist()"
    )
    
    # Получаем контейнер
    container = get_container()
    
    # Обновляем конфигурацию
    container.config.download.output_dir.override(output_dir)
    container.config.download.format.override(format)
    container.config.download.quality.override(quality)
    container.config.download.max_retries.override(max_retries)
    container.config.logging.verbose.override(verbose)
    
    # Получаем сервис
    app_service = container.app_service()
    
    # Загружаем плейлист
    results = app_service.download_playlist(playlist_url)
    
    # Конвертируем в старый формат
    return {
        "total": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if r.failed),
        "results": [
            {
                "track": f"{r.track.artist} - {r.track.title}",
                "status": r.status.value,
                "file": str(r.file_path) if r.file_path else None,
                "error": r.error
            }
            for r in results
        ]
    }


def download_track(
    track_url: str,
    output_dir: str = "downloads",
    format: str = "mp3",
    quality: str = "320",
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Загрузить один трек (legacy API).
    
    DEPRECATED: Используйте новый API через DI контейнер.
    
    Args:
        track_url: URL трека Spotify
        output_dir: Директория для сохранения
        format: Формат аудио
        quality: Качество
        verbose: Подробный вывод
        
    Returns:
        Словарь с результатом загрузки
    """
    _show_deprecation_warning(
        "download_track()",
        "container.app_service().download_track()"
    )
    
    container = get_container()
    
    # Обновляем конфигурацию
    container.config.download.output_dir.override(output_dir)
    container.config.download.format.override(format)
    container.config.download.quality.override(quality)
    container.config.logging.verbose.override(verbose)
    
    app_service = container.app_service()
    result = app_service.download_track(track_url)
    
    return {
        "track": f"{result.track.artist} - {result.track.title}",
        "status": result.status.value,
        "file": str(result.file_path) if result.file_path else None,
        "error": result.error
    }


def search_and_download(
    artist: str,
    title: str,
    output_dir: str = "downloads",
    format: str = "mp3",
    quality: str = "320"
) -> Dict[str, Any]:
    """
    Найти и загрузить трек по исполнителю и названию (legacy API).
    
    DEPRECATED: Используйте новый API через DI контейнер.
    
    Args:
        artist: Исполнитель
        title: Название трека
        output_dir: Директория для сохранения
        format: Формат аудио
        quality: Качество
        
    Returns:
        Словарь с результатом загрузки
    """
    _show_deprecation_warning(
        "search_and_download()",
        "container.app_service().search_and_download()"
    )
    
    container = get_container()
    
    # Обновляем конфигурацию
    container.config.download.output_dir.override(output_dir)
    container.config.download.format.override(format)
    container.config.download.quality.override(quality)
    
    app_service = container.app_service()
    result = app_service.search_and_download(artist, title)
    
    return {
        "track": f"{result.track.artist} - {result.track.title}",
        "status": result.status.value,
        "file": str(result.file_path) if result.file_path else None,
        "error": result.error
    }


def get_playlist_info(playlist_url: str) -> Dict[str, Any]:
    """
    Получить информацию о плейлисте (legacy API).
    
    DEPRECATED: Используйте новый API через DI контейнер.
    
    Args:
        playlist_url: URL плейлиста
        
    Returns:
        Словарь с информацией о плейлисте
    """
    _show_deprecation_warning(
        "get_playlist_info()",
        "container.playlist_repository().get_playlist()"
    )
    
    container = get_container()
    app_service = container.app_service()
    
    playlist = app_service.get_playlist_info(playlist_url)
    
    return {
        "id": playlist.id,
        "name": playlist.name,
        "description": playlist.description,
        "owner": playlist.owner,
        "total_tracks": playlist.total_tracks,
        "url": playlist.url
    }


def clear_cache(cache_type: str = "all"):
    """
    Очистить кеш (legacy API).
    
    DEPRECATED: Используйте новый API через DI контейнер.
    
    Args:
        cache_type: Тип кеша (all, spotify, youtube)
    """
    _show_deprecation_warning(
        "clear_cache()",
        "container.youtube_cache().clear() or container.spotify_cache().clear()"
    )
    
    container = get_container()
    
    if cache_type in ("all", "youtube"):
        container.youtube_cache().clear()
    
    if cache_type in ("all", "spotify"):
        container.spotify_cache().clear()


# Алиасы для совместимости
download = download_track
download_from_url = download_track
get_info = get_playlist_info


class LegacyDownloader:
    """
    Legacy класс Downloader для обратной совместимости.
    
    DEPRECATED: Используйте новую архитектуру через DI контейнер.
    """
    
    def __init__(
        self,
        output_dir: str = "downloads",
        format: str = "mp3",
        quality: str = "320",
        verbose: bool = False
    ):
        """
        Инициализация legacy downloader.
        
        Args:
            output_dir: Директория для сохранения
            format: Формат аудио
            quality: Качество
            verbose: Подробный вывод
        """
        _show_deprecation_warning(
            "LegacyDownloader",
            "DI Container with app_service"
        )
        
        self.output_dir = output_dir
        self.format = format
        self.quality = quality
        self.verbose = verbose
        
        # Получаем контейнер
        self.container = get_container()
        
        # Настраиваем конфигурацию
        self.container.config.download.output_dir.override(output_dir)
        self.container.config.download.format.override(format)
        self.container.config.download.quality.override(quality)
        self.container.config.logging.verbose.override(verbose)
    
    def download_playlist(self, playlist_url: str) -> Dict[str, Any]:
        """Загрузить плейлист."""
        app_service = self.container.app_service()
        results = app_service.download_playlist(playlist_url)
        
        return {
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if r.failed),
            "results": results
        }
    
    def download_track(self, track_url: str) -> DownloadResult:
        """Загрузить трек."""
        app_service = self.container.app_service()
        return app_service.download_track(track_url)
    
    def search_and_download(self, artist: str, title: str) -> DownloadResult:
        """Найти и загрузить трек."""
        app_service = self.container.app_service()
        return app_service.search_and_download(artist, title)

# Made with Bob
