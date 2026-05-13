"""
Legacy Adapter для Spotify Client.

Обеспечивает обратную совместимость со старым API.
"""

from typing import List, Optional
from dataclasses import dataclass

from src.features.spotify.infrastructure.spotify_client import (
    SpotifyClient as NewSpotifyClient,
    SpotifyPlaylistRepository,
    SpotifyTrackRepository
)
from src.features.spotify.domain.repositories import SpotifyTrack as NewTrack


@dataclass
class PlaylistInfo:
    """Legacy модель плейлиста для обратной совместимости."""
    id: str
    name: str
    description: str
    owner: str
    total_tracks: int
    url: str
    image_url: Optional[str] = None


@dataclass
class Track:
    """Legacy модель трека для обратной совместимости."""
    id: str
    name: str
    artists: List[str]
    album: str
    album_artist: str
    duration_ms: int
    track_number: int
    disc_number: int
    release_date: str
    isrc: Optional[str]
    genres: List[str]
    popularity: int
    explicit: bool
    album_image_url: Optional[str] = None
    
    @property
    def artist(self) -> str:
        """Получить основного исполнителя (для обратной совместимости)."""
        return self.get_primary_artist()
    
    @property
    def album_art_url(self) -> Optional[str]:
        """Алиас для album_image_url (для обратной совместимости)."""
        return self.album_image_url
    
    def get_duration_seconds(self) -> int:
        """Получить длительность в секундах."""
        return self.duration_ms // 1000
    
    def get_primary_artist(self) -> str:
        """Получить основного исполнителя."""
        return self.artists[0] if self.artists else "Unknown Artist"
    
    def get_all_artists_string(self) -> str:
        """Получить всех исполнителей строкой."""
        return ", ".join(self.artists) if self.artists else "Unknown Artist"


class SpotifyClient:
    """
    Legacy Spotify Client для обратной совместимости.
    
    Адаптирует новый API к старому интерфейсу.
    """
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Инициализация клиента.
        
        Args:
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
        """
        self._client = NewSpotifyClient(client_id, client_secret)
        self._playlist_repo: Optional[SpotifyPlaylistRepository] = None
        self._track_repo: Optional[SpotifyTrackRepository] = None
    
    def authenticate(self) -> bool:
        """Аутентификация с Spotify API."""
        success = self._client.authenticate()
        
        if success:
            # Создаем репозитории после успешной аутентификации
            self._playlist_repo = SpotifyPlaylistRepository(self._client)
            self._track_repo = SpotifyTrackRepository(self._client)
        
        return success
    
    def get_playlist_info(self, playlist_url: str) -> PlaylistInfo:
        """
        Получить информацию о плейлисте.
        
        Args:
            playlist_url: URL или ID плейлиста
            
        Returns:
            PlaylistInfo объект
        """
        if not self._playlist_repo:
            raise RuntimeError("Client not authenticated")
        
        # Извлечь ID из URL если нужно
        from src.shared.lib.utils import extract_playlist_id
        playlist_id = extract_playlist_id(playlist_url) or playlist_url
        
        playlist = self._playlist_repo.get_playlist(playlist_id)
        
        return PlaylistInfo(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description or "",
            owner=playlist.owner,
            total_tracks=playlist.total_tracks,
            url=playlist.url,
            image_url=playlist.image_url
        )
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        """
        Получить треки плейлиста.
        
        Args:
            playlist_id: ID плейлиста
            
        Returns:
            Список Track объектов
        """
        if not self._playlist_repo:
            raise RuntimeError("Client not authenticated")
        
        new_tracks = self._playlist_repo.get_tracks(playlist_id)
        
        return [self._convert_track(t) for t in new_tracks]
    
    def get_track_metadata(self, track_id: str) -> Optional[Track]:
        """
        Получить метаданные трека.
        
        Args:
            track_id: ID трека
            
        Returns:
            Track объект или None
        """
        if not self._track_repo:
            raise RuntimeError("Client not authenticated")
        
        try:
            new_track = self._track_repo.get_track(track_id)
            return self._convert_track(new_track)
        except Exception:
            return None
    
    def search_track(self, query: str, limit: int = 10) -> List[Track]:
        """
        Поиск треков.
        
        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            
        Returns:
            Список Track объектов
        """
        if not self._track_repo:
            raise RuntimeError("Client not authenticated")
        
        new_tracks = self._track_repo.search_track(query, limit)
        
        return [self._convert_track(t) for t in new_tracks]
    
    def validate_playlist_url(self, url: str) -> bool:
        """
        Проверить валидность URL плейлиста.
        
        Args:
            url: URL для проверки
            
        Returns:
            True если валидный
        """
        from src.shared.lib.utils import validate_url, extract_playlist_id
        
        if not validate_url(url):
            return False
        
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            return False
        
        try:
            if self._playlist_repo:
                self._playlist_repo.get_playlist(playlist_id)
                return True
        except Exception:
            pass
        
        return False
    
    def _convert_track(self, new_track: NewTrack) -> Track:
        """Конвертировать новую модель трека в legacy."""
        return Track(
            id=new_track.id,
            name=new_track.name,
            artists=new_track.artists,
            album=new_track.album,
            album_artist=new_track.album_artist or new_track.artist,
            duration_ms=new_track.duration_ms,
            track_number=new_track.track_number,
            disc_number=new_track.disc_number,
            release_date=new_track.release_date,
            isrc=new_track.isrc,
            genres=new_track.genres,
            popularity=new_track.popularity,
            explicit=new_track.explicit,
            album_image_url=new_track.album_art_url
        )
    
    def __repr__(self) -> str:
        """Строковое представление."""
        return repr(self._client)


# Made with Bob