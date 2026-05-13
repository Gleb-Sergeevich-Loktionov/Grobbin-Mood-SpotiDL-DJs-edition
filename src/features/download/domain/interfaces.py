"""
Интерфейсы для download feature.

Определяет контракты для всех компонентов загрузки.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List
from .models import Track, DownloadResult, TrackMetadata


class IDownloader(ABC):
    """Интерфейс для загрузчика треков."""
    
    @abstractmethod
    async def download(self, track: Track, output_path: Path) -> DownloadResult:
        """
        Загрузить трек.
        
        Args:
            track: Информация о треке
            output_path: Путь для сохранения
            
        Returns:
            Результат загрузки
        """
        pass
    
    @abstractmethod
    async def download_batch(
        self, 
        tracks: List[Track], 
        output_dir: Path,
        max_concurrent: int = 3
    ) -> List[DownloadResult]:
        """
        Загрузить несколько треков параллельно.
        
        Args:
            tracks: Список треков
            output_dir: Директория для сохранения
            max_concurrent: Максимум параллельных загрузок
            
        Returns:
            Список результатов загрузки
        """
        pass


class IMatcher(ABC):
    """Интерфейс для поиска треков на платформах."""
    
    @abstractmethod
    def find_match(self, track: Track) -> Optional[str]:
        """
        Найти трек на платформе.
        
        Args:
            track: Информация о треке
            
        Returns:
            URL найденного трека или None
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[dict]:
        """
        Поиск по запросу.
        
        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            
        Returns:
            Список найденных треков
        """
        pass


class IMetadataHandler(ABC):
    """Интерфейс для работы с метаданными."""
    
    @abstractmethod
    def embed_metadata(self, file_path: Path, metadata: TrackMetadata) -> bool:
        """
        Встроить метаданные в файл.
        
        Args:
            file_path: Путь к аудио файлу
            metadata: Метаданные трека
            
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: Path) -> Optional[TrackMetadata]:
        """
        Извлечь метаданные из файла.
        
        Args:
            file_path: Путь к аудио файлу
            
        Returns:
            Метаданные или None
        """
        pass
    
    @abstractmethod
    def download_cover(self, url: str, output_path: Path) -> bool:
        """
        Скачать обложку альбома.
        
        Args:
            url: URL обложки
            output_path: Путь для сохранения
            
        Returns:
            True если успешно
        """
        pass


class ICache(ABC):
    """Интерфейс для кеширования."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Получить значение из кеша."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Сохранить значение в кеш."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Удалить значение из кеша."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Очистить весь кеш."""
        pass


class IProgressObserver(ABC):
    """Интерфейс для наблюдателя за прогрессом."""
    
    @abstractmethod
    def on_start(self, total: int):
        """Вызывается при начале процесса."""
        pass
    
    @abstractmethod
    def on_progress(self, current: int, total: int, message: str = ""):
        """Вызывается при обновлении прогресса."""
        pass
    
    @abstractmethod
    def on_complete(self, success: int, failed: int):
        """Вызывается при завершении процесса."""
        pass
    
    @abstractmethod
    def on_error(self, error: Exception):
        """Вызывается при ошибке."""
        pass

# Made with Bob
