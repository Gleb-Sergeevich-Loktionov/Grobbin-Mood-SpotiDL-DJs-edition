"""
Spotify API Client - Infrastructure Layer.

Реализация клиента для работы с Spotify Web API.
Интегрирован с Repository Pattern.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

from ..domain.repositories import (
    IPlaylistRepository,
    ITrackRepository,
    Playlist,
    SpotifyTrack
)

logger = logging.getLogger(__name__)


class SpotifyClient:
    """
    Клиент для взаимодействия с Spotify Web API.
    
    Базовый клиент, который используется репозиториями.
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:9900/"):
        """
        Инициализация Spotify клиента.
        
        Args:
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
            redirect_uri: URI для OAuth редиректа
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.sp: Optional[spotipy.Spotify] = None
        self._authenticated = False
        
        logger.info("Spotify client initialized")
    
    def authenticate(self) -> bool:
        """
        Аутентификация с Spotify API через OAuth.
        Откроет браузер для авторизации пользователя.
        
        Returns:
            True если аутентификация успешна
        """
        try:
            scope = "playlist-read-private playlist-read-collaborative"
            
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=scope,
                open_browser=True,
                cache_path=".spotify_cache"
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Тест аутентификации
            self.sp.current_user()
            
            self._authenticated = True
            logger.info("Successfully authenticated with Spotify API")
            return True
        
        except Exception as e:
            logger.error(f"Failed to authenticate with Spotify API: {e}")
            self._authenticated = False
            return False
    
    def _ensure_authenticated(self) -> None:
        """Проверка аутентификации."""
        if not self._authenticated or not self.sp:
            raise RuntimeError("Spotify client not authenticated. Call authenticate() first.")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_playlist_raw(self, playlist_id: str) -> Dict[str, Any]:
        """
        Получить сырые данные плейлиста из API.
        
        Args:
            playlist_id: ID плейлиста
            
        Returns:
            Словарь с данными плейлиста
        """
        self._ensure_authenticated()
        return self.sp.playlist(playlist_id)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_playlist_tracks_raw(self, playlist_id: str) -> List[Dict[str, Any]]:
        """
        Получить сырые данные треков плейлиста.
        
        Args:
            playlist_id: ID плейлиста
            
        Returns:
            Список словарей с данными треков
        """
        self._ensure_authenticated()
        
        tracks = []
        results = self.sp.playlist_tracks(playlist_id)
        
        tracks.extend(results['items'])
        
        # Пагинация
        while results['next']:
            results = self.sp.next(results)
            tracks.extend(results['items'])
        
        return tracks
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_track_raw(self, track_id: str) -> Dict[str, Any]:
        """
        Получить сырые данные трека.
        
        Args:
            track_id: ID трека
            
        Returns:
            Словарь с данными трека
        """
        self._ensure_authenticated()
        return self.sp.track(track_id)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_tracks_raw(self, track_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Получить сырые данные нескольких треков.
        
        Args:
            track_ids: Список ID треков (до 50)
            
        Returns:
            Список словарей с данными треков
        """
        self._ensure_authenticated()
        
        # API позволяет получить до 50 треков за раз
        if len(track_ids) > 50:
            logger.warning(f"Requesting {len(track_ids)} tracks, but API limit is 50. Splitting request.")
            all_tracks = []
            for i in range(0, len(track_ids), 50):
                batch = track_ids[i:i+50]
                results = self.sp.tracks(batch)
                all_tracks.extend(results['tracks'])
            return all_tracks
        
        results = self.sp.tracks(track_ids)
        return results['tracks']
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def search_tracks_raw(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск треков.
        
        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            
        Returns:
            Список словарей с данными треков
        """
        self._ensure_authenticated()
        results = self.sp.search(q=query, type='track', limit=limit)
        return results['tracks']['items']
    
    def __repr__(self) -> str:
        """Строковое представление."""
        status = "authenticated" if self._authenticated else "not authenticated"
        return f"SpotifyClient({status})"


class SpotifyPlaylistRepository(IPlaylistRepository):
    """
    Репозиторий для работы с плейлистами Spotify.
    
    Реализует IPlaylistRepository (композитный интерфейс) используя SpotifyClient.
    Поддерживает все три специализированных интерфейса:
    - IPlaylistReader: чтение информации о плейлисте
    - ITrackReader: чтение треков
    - IUserPlaylistReader: чтение плейлистов пользователя
    """
    
    def __init__(self, client: SpotifyClient):
        """
        Args:
            client: Аутентифицированный Spotify клиент
        """
        self.client = client
    
    def get_playlist(self, playlist_id: str) -> Playlist:
        """Получить информацию о плейлисте."""
        raw_data = self.client.get_playlist_raw(playlist_id)
        return self._parse_playlist(raw_data)
    
    def get_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0) -> List[SpotifyTrack]:
        """
        Получить треки плейлиста.
        
        Args:
            playlist_id: ID плейлиста
            limit: Максимальное количество треков (не используется, получаем все)
            offset: Смещение для пагинации (не используется, получаем все)
        
        Note:
            Текущая реализация получает все треки плейлиста независимо от limit/offset.
            Параметры добавлены для соответствия интерфейсу ITrackReader.
        """
        raw_tracks = self.client.get_playlist_tracks_raw(playlist_id)
        
        tracks = []
        for i, item in enumerate(raw_tracks):
            # Spotify API может возвращать 'track' или 'item' в зависимости от версии
            track_data = item.get('track') or item.get('item')
            if not track_data:
                logger.debug(f"Track {i}: No track data")
                continue
            if not track_data.get('id'):
                logger.debug(f"Track {i}: No track ID")
                continue
            
            track = self._parse_track(track_data)
            if track:
                tracks.append(track)
            else:
                logger.debug(f"Track {i}: Failed to parse")
        
        logger.info(f"Retrieved {len(tracks)} tracks from playlist {playlist_id}")
        
        # Применяем limit и offset если указаны
        if offset > 0 or limit < len(tracks):
            tracks = tracks[offset:offset + limit]
        
        return tracks
    
    def get_track(self, track_id: str) -> SpotifyTrack:
        """
        Получить информацию о треке.
        
        Args:
            track_id: ID трека
            
        Returns:
            Информация о треке
        """
        raw_data = self.client.get_track_raw(track_id)
        track = self._parse_track(raw_data)
        
        if not track:
            raise ValueError(f"Failed to parse track {track_id}")
        
        return track
    
    def get_user_playlists(self, username: str = 'me', limit: int = 50) -> List[Playlist]:
        """
        Получить плейлисты пользователя.
        
        Args:
            username: Имя пользователя или 'me' для текущего
            limit: Максимальное количество плейлистов
        """
        # TODO: Реализовать когда понадобится
        raise NotImplementedError("User playlists not implemented yet")
    
    def _parse_playlist(self, data: Dict[str, Any]) -> Playlist:
        """Парсинг данных плейлиста."""
        image_url = None
        if data.get('images') and len(data['images']) > 0:
            image_url = data['images'][0]['url']
        
        tracks_info = data.get('tracks', {})
        total_tracks = tracks_info.get('total', 0) if isinstance(tracks_info, dict) else 0
        
        return Playlist(
            id=data['id'],
            name=data.get('name', 'Unknown Playlist'),
            description=data.get('description', ''),
            owner=data.get('owner', {}).get('display_name', 'Unknown'),
            total_tracks=total_tracks,
            public=data.get('public', False),
            collaborative=data.get('collaborative', False),
            url=data.get('external_urls', {}).get('spotify', ''),
            image_url=image_url
        )
    
    def _parse_track(self, data: Dict[str, Any]) -> Optional[SpotifyTrack]:
        """Парсинг данных трека."""
        try:
            artists = [artist['name'] for artist in data.get('artists', [])]
            
            album_data = data.get('album', {})
            album_name = album_data.get('name', 'Unknown Album')
            album_artist = album_data.get('artists', [{}])[0].get('name', artists[0] if artists else 'Unknown')
            
            album_art_url = None
            if album_data.get('images') and len(album_data['images']) > 0:
                album_art_url = album_data['images'][0]['url']
            
            external_ids = data.get('external_ids', {})
            isrc = external_ids.get('isrc')
            
            return SpotifyTrack(
                id=data['id'],
                name=data['name'],
                artists=artists,
                album=album_name,
                album_artist=album_artist,
                duration_ms=data.get('duration_ms', 0),
                track_number=data.get('track_number', 0),
                disc_number=data.get('disc_number', 1),
                release_date=album_data.get('release_date', ''),
                isrc=isrc,
                explicit=data.get('explicit', False),
                url=data.get('external_urls', {}).get('spotify', ''),
                preview_url=data.get('preview_url'),
                album_art_url=album_art_url,
                genres=[],  # Требует отдельный API вызов
                popularity=data.get('popularity', 0)
            )
        
        except Exception as e:
            logger.warning(f"Failed to parse track data: {e}")
            return None


class SpotifyTrackRepository(ITrackRepository):
    """
    Репозиторий для работы с треками Spotify.
    
    Реализует ITrackRepository используя SpotifyClient.
    """
    
    def __init__(self, client: SpotifyClient):
        """
        Args:
            client: Аутентифицированный Spotify клиент
        """
        self.client = client
    
    def get_track(self, track_id: str) -> SpotifyTrack:
        """Получить информацию о треке."""
        raw_data = self.client.get_track_raw(track_id)
        track = self._parse_track(raw_data)
        
        if not track:
            raise ValueError(f"Failed to parse track {track_id}")
        
        return track
    
    def get_tracks(self, track_ids: List[str]) -> List[SpotifyTrack]:
        """Получить несколько треков."""
        raw_tracks = self.client.get_tracks_raw(track_ids)
        
        tracks = []
        for data in raw_tracks:
            if data:
                track = self._parse_track(data)
                if track:
                    tracks.append(track)
        
        return tracks
    
    def search_track(self, query: str, limit: int = 10) -> List[SpotifyTrack]:
        """Поиск треков."""
        raw_tracks = self.client.search_tracks_raw(query, limit)
        
        tracks = []
        for data in raw_tracks:
            track = self._parse_track(data)
            if track:
                tracks.append(track)
        
        return tracks
    
    def _parse_track(self, data: Dict[str, Any]) -> Optional[SpotifyTrack]:
        """Парсинг данных трека."""
        try:
            artists = [artist['name'] for artist in data.get('artists', [])]
            
            album_data = data.get('album', {})
            album_name = album_data.get('name', 'Unknown Album')
            album_artist = album_data.get('artists', [{}])[0].get('name', artists[0] if artists else 'Unknown')
            
            album_art_url = None
            if album_data.get('images') and len(album_data['images']) > 0:
                album_art_url = album_data['images'][0]['url']
            
            external_ids = data.get('external_ids', {})
            isrc = external_ids.get('isrc')
            
            return SpotifyTrack(
                id=data['id'],
                name=data['name'],
                artists=artists,
                album=album_name,
                album_artist=album_artist,
                duration_ms=data.get('duration_ms', 0),
                track_number=data.get('track_number', 0),
                disc_number=data.get('disc_number', 1),
                release_date=album_data.get('release_date', ''),
                isrc=isrc,
                explicit=data.get('explicit', False),
                url=data.get('external_urls', {}).get('spotify', ''),
                preview_url=data.get('preview_url'),
                album_art_url=album_art_url,
                genres=[],
                popularity=data.get('popularity', 0)
            )
        
        except Exception as e:
            logger.warning(f"Failed to parse track data: {e}")
            return None


# Made with Bob