"""
Модели данных для download feature.

Определяет структуры данных для треков, результатов загрузки и метаданных.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class DownloadStatus(Enum):
    """Статус загрузки трека."""
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    EMBEDDING_METADATA = "embedding_metadata"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Track:
    """Модель трека для загрузки."""
    
    # Основная информация
    title: str
    artist: str
    album: Optional[str] = None
    
    # Дополнительная информация
    duration_ms: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    release_date: Optional[str] = None
    isrc: Optional[str] = None
    
    # Spotify данные
    spotify_id: Optional[str] = None
    spotify_url: Optional[str] = None
    
    # Обложка
    album_art_url: Optional[str] = None
    
    # Жанры и метаданные
    genres: List[str] = field(default_factory=list)
    explicit: bool = False
    
    def __post_init__(self):
        """Валидация после инициализации."""
        if not self.title or not self.artist:
            raise ValueError("Title and artist are required")
    
    @property
    def search_query(self) -> str:
        """Поисковый запрос для трека."""
        query = f"{self.artist} - {self.title}"
        if self.album:
            query += f" {self.album}"
        return query
    
    @property
    def filename(self) -> str:
        """Имя файла для сохранения."""
        # Очистка от недопустимых символов
        safe_artist = self._sanitize_filename(self.artist)
        safe_title = self._sanitize_filename(self.title)
        
        if self.track_number:
            return f"{self.track_number:02d} - {safe_artist} - {safe_title}.mp3"
        return f"{safe_artist} - {safe_title}.mp3"
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Очистить имя файла от недопустимых символов."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        return name.strip()


@dataclass
class TrackMetadata:
    """Метаданные трека для встраивания в файл."""
    
    title: str
    artist: str
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    comment: Optional[str] = None
    isrc: Optional[str] = None
    
    # Обложка
    album_art_path: Optional[Path] = None
    album_art_data: Optional[bytes] = None
    
    @classmethod
    def from_track(cls, track: Track) -> "TrackMetadata":
        """Создать метаданные из трека."""
        year = None
        if track.release_date:
            try:
                year = int(track.release_date[:4])
            except (ValueError, IndexError):
                pass
        
        return cls(
            title=track.title,
            artist=track.artist,
            album=track.album,
            track_number=track.track_number,
            disc_number=track.disc_number,
            year=year,
            genre=", ".join(track.genres) if track.genres else None,
            isrc=track.isrc,
        )


@dataclass
class DownloadResult:
    """Результат загрузки трека."""
    
    track: Track
    status: DownloadStatus
    file_path: Optional[Path] = None
    error: Optional[str] = None
    source_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """Успешна ли загрузка."""
        return self.status == DownloadStatus.SUCCESS
    
    @property
    def failed(self) -> bool:
        """Провалилась ли загрузка."""
        return self.status == DownloadStatus.FAILED
    
    def __str__(self) -> str:
        """Строковое представление результата."""
        if self.success:
            return f"✓ {self.track.artist} - {self.track.title}"
        elif self.failed:
            return f"✗ {self.track.artist} - {self.track.title}: {self.error}"
        else:
            return f"⊙ {self.track.artist} - {self.track.title}: {self.status.value}"


@dataclass
class DownloadBatchResult:
    """Результат пакетной загрузки."""
    
    results: List[DownloadResult]
    total_duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def total(self) -> int:
        """Общее количество треков."""
        return len(self.results)
    
    @property
    def successful(self) -> int:
        """Количество успешных загрузок."""
        return sum(1 for r in self.results if r.success)
    
    @property
    def failed(self) -> int:
        """Количество неудачных загрузок."""
        return sum(1 for r in self.results if r.failed)
    
    @property
    def success_rate(self) -> float:
        """Процент успешных загрузок."""
        return (self.successful / self.total * 100) if self.total > 0 else 0.0
    
    @property
    def average_time_per_track(self) -> float:
        """Среднее время на трек в секундах."""
        return self.total_duration_seconds / self.total if self.total > 0 else 0.0
    
    def get_failed_tracks(self) -> List[Track]:
        """Получить список неудачных треков."""
        return [r.track for r in self.results if r.failed]
    
    def __str__(self) -> str:
        """Строковое представление результата."""
        return (
            f"Загрузка завершена: {self.successful}/{self.total} успешно "
            f"({self.success_rate:.1f}%), "
            f"среднее время: {self.average_time_per_track:.2f}с/трек"
        )

# Made with Bob
