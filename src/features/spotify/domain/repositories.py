"""
Repository Pattern для работы с данными Spotify.

Абстрагирует доступ к данным Spotify API.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Playlist:
    """Модель плейлиста."""
    id: str
    name: str
    description: Optional[str]
    owner: str
    total_tracks: int
    public: bool
    collaborative: bool
    url: str
    image_url: Optional[str] = None
    
    @property
    def safe_name(self) -> str:
        """Безопасное имя для файловой системы."""
        invalid_chars = '<>:"/\\|?*'
        safe = self.name
        for char in invalid_chars:
            safe = safe.replace(char, '')
        return safe.strip()


@dataclass
class SpotifyTrack:
    """Модель трека из Spotify."""
    id: str
    name: str
    artists: List[str]
    album: str
    album_artist: Optional[str]
    duration_ms: int
    track_number: int
    disc_number: int
    release_date: str
    isrc: Optional[str]
    explicit: bool
    url: str
    preview_url: Optional[str]
    album_art_url: Optional[str]
    genres: List[str]
    popularity: int
    
    @property
    def artist(self) -> str:
        """Основной исполнитель."""
        return self.artists[0] if self.artists else "Unknown Artist"
    
    @property
    def all_artists(self) -> str:
        """Все исполнители через запятую."""
        return ", ".join(self.artists)


@dataclass
class Album:
    """Модель альбома."""
    id: str
    name: str
    artists: List[str]
    release_date: str
    total_tracks: int
    album_type: str
    url: str
    image_url: Optional[str]
    genres: List[str]


class IPlaylistReader(ABC):
    """
    Интерфейс для чтения информации о плейлисте.
    
    Специализированный интерфейс согласно Interface Segregation Principle.
    Отвечает только за получение информации о плейлисте.
    """
    
    @abstractmethod
    def get_playlist(self, playlist_id: str) -> Playlist:
        """
        Получить информацию о плейлисте.
        
        Args:
            playlist_id: ID плейлиста
            
        Returns:
            Информация о плейлисте
        """
        pass


class ITrackReader(ABC):
    """
    Интерфейс для чтения треков.
    
    Специализированный интерфейс согласно Interface Segregation Principle.
    Отвечает только за получение треков из плейлиста и информации о треках.
    """
    
    @abstractmethod
    def get_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0) -> List[SpotifyTrack]:
        """
        Получить треки плейлиста.
        
        Args:
            playlist_id: ID плейлиста
            limit: Максимальное количество треков (по умолчанию 100)
            offset: Смещение для пагинации (по умолчанию 0)
            
        Returns:
            Список треков
        """
        pass
    
    @abstractmethod
    def get_track(self, track_id: str) -> SpotifyTrack:
        """
        Получить информацию о треке.
        
        Args:
            track_id: ID трека
            
        Returns:
            Информация о треке
        """
        pass


class IUserPlaylistReader(ABC):
    """
    Интерфейс для чтения плейлистов пользователя.
    
    Специализированный интерфейс согласно Interface Segregation Principle.
    Отвечает только за получение списка плейлистов пользователя.
    """
    
    @abstractmethod
    def get_user_playlists(self, username: str = 'me', limit: int = 50) -> List[Playlist]:
        """
        Получить плейлисты пользователя.
        
        Args:
            username: Имя пользователя или 'me' для текущего (по умолчанию 'me')
            limit: Максимальное количество плейлистов (по умолчанию 50)
            
        Returns:
            Список плейлистов
        """
        pass


class IPlaylistRepository(IPlaylistReader, ITrackReader, IUserPlaylistReader):
    """
    Полный интерфейс репозитория плейлистов.
    
    Композиция из специализированных интерфейсов для обратной совместимости.
    Используется в случаях, когда нужен полный доступ ко всем операциям.
    
    Следует принципу Interface Segregation Principle:
    - Клиенты могут зависеть от специализированных интерфейсов
    - Полный интерфейс доступен для случаев, когда нужны все операции
    """
    pass


class ITrackRepository(ABC):
    """Интерфейс репозитория треков."""
    
    @abstractmethod
    def get_track(self, track_id: str) -> SpotifyTrack:
        """
        Получить информацию о треке.
        
        Args:
            track_id: ID трека
            
        Returns:
            Информация о треке
        """
        pass
    
    @abstractmethod
    def get_tracks(self, track_ids: List[str]) -> List[SpotifyTrack]:
        """
        Получить несколько треков.
        
        Args:
            track_ids: Список ID треков
            
        Returns:
            Список треков
        """
        pass
    
    @abstractmethod
    def search_track(self, query: str, limit: int = 10) -> List[SpotifyTrack]:
        """
        Поиск треков.
        
        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            
        Returns:
            Список найденных треков
        """
        pass


class IAlbumRepository(ABC):
    """Интерфейс репозитория альбомов."""
    
    @abstractmethod
    def get_album(self, album_id: str) -> Album:
        """
        Получить информацию об альбоме.
        
        Args:
            album_id: ID альбома
            
        Returns:
            Информация об альбоме
        """
        pass
    
    @abstractmethod
    def get_album_tracks(self, album_id: str) -> List[SpotifyTrack]:
        """
        Получить треки альбома.
        
        Args:
            album_id: ID альбома
            
        Returns:
            Список треков
        """
        pass


class ISpotifyCache(ABC):
    """Интерфейс кеша для Spotify данных."""
    
    @abstractmethod
    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Получить плейлист из кеша."""
        pass
    
    @abstractmethod
    def set_playlist(self, playlist: Playlist, ttl: int = 3600):
        """Сохранить плейлист в кеш."""
        pass
    
    @abstractmethod
    def get_track(self, track_id: str) -> Optional[SpotifyTrack]:
        """Получить трек из кеша."""
        pass
    
    @abstractmethod
    def set_track(self, track: SpotifyTrack, ttl: int = 3600):
        """Сохранить трек в кеш."""
        pass
    
    @abstractmethod
    def clear(self):
        """Очистить кеш."""
        pass


class CachedPlaylistRepository(IPlaylistRepository):
    """
    Репозиторий плейлистов с кешированием.
    
    Использует паттерн Decorator для добавления кеширования.
    Реализует композитный интерфейс IPlaylistRepository.
    """
    
    def __init__(
        self,
        repository: IPlaylistRepository,
        cache: ISpotifyCache
    ):
        """
        Args:
            repository: Базовый репозиторий
            cache: Кеш для данных
        """
        self.repository = repository
        self.cache = cache
    
    def get_playlist(self, playlist_id: str) -> Playlist:
        """Получить плейлист с кешированием."""
        # Проверяем кеш
        cached = self.cache.get_playlist(playlist_id)
        if cached:
            return cached
        
        # Получаем из репозитория
        playlist = self.repository.get_playlist(playlist_id)
        
        # Сохраняем в кеш
        self.cache.set_playlist(playlist)
        
        return playlist
    
    def get_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0) -> List[SpotifyTrack]:
        """Получить треки плейлиста."""
        return self.repository.get_tracks(playlist_id, limit, offset)
    
    def get_track(self, track_id: str) -> SpotifyTrack:
        """Получить информацию о треке с кешированием."""
        # Проверяем кеш
        cached = self.cache.get_track(track_id)
        if cached:
            return cached
        
        # Получаем из репозитория
        track = self.repository.get_track(track_id)
        
        # Сохраняем в кеш
        self.cache.set_track(track)
        
        return track
    
    def get_user_playlists(self, username: str = 'me', limit: int = 50) -> List[Playlist]:
        """Получить плейлисты пользователя."""
        return self.repository.get_user_playlists(username, limit)


class CachedTrackRepository(ITrackRepository):
    """
    Репозиторий треков с кешированием.
    
    Использует паттерн Decorator для добавления кеширования.
    """
    
    def __init__(
        self,
        repository: ITrackRepository,
        cache: ISpotifyCache
    ):
        """
        Args:
            repository: Базовый репозиторий
            cache: Кеш для данных
        """
        self.repository = repository
        self.cache = cache
    
    def get_track(self, track_id: str) -> SpotifyTrack:
        """Получить трек с кешированием."""
        # Проверяем кеш
        cached = self.cache.get_track(track_id)
        if cached:
            return cached
        
        # Получаем из репозитория
        track = self.repository.get_track(track_id)
        
        # Сохраняем в кеш
        self.cache.set_track(track)
        
        return track
    
    def get_tracks(self, track_ids: List[str]) -> List[SpotifyTrack]:
        """Получить несколько треков с кешированием."""
        tracks = []
        uncached_ids = []
        
        # Проверяем кеш для каждого трека
        for track_id in track_ids:
            cached = self.cache.get_track(track_id)
            if cached:
                tracks.append(cached)
            else:
                uncached_ids.append(track_id)
        
        # Получаем некешированные треки
        if uncached_ids:
            new_tracks = self.repository.get_tracks(uncached_ids)
            for track in new_tracks:
                self.cache.set_track(track)
                tracks.append(track)
        
        return tracks
    
    def search_track(self, query: str, limit: int = 10) -> List[SpotifyTrack]:
        """Поиск треков (без кеширования)."""
        return self.repository.search_track(query, limit)

# Made with Bob
