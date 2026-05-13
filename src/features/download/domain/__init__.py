"""
Download domain layer - бизнес-логика загрузки.

Содержит:
- Модели данных (Track, DownloadResult)
- Интерфейсы (IDownloader, IMatcher, IMetadataHandler)
- Сервисы бизнес-логики
- Фабрики и стратегии
"""

from .interfaces import IDownloader, IMatcher, IMetadataHandler
from .models import Track, DownloadResult, DownloadStatus

__all__ = [
    "IDownloader",
    "IMatcher", 
    "IMetadataHandler",
    "Track",
    "DownloadResult",
    "DownloadStatus",
]

# Made with Bob
