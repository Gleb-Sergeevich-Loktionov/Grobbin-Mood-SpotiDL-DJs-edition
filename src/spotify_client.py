"""
Spotify API Client for playlist and track metadata retrieval.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

logger = logging.getLogger(__name__)


@dataclass
class PlaylistInfo:
    """Playlist metadata."""
    id: str
    name: str
    description: str
    owner: str
    total_tracks: int
    url: str
    image_url: Optional[str] = None


@dataclass
class Track:
    """Track metadata."""
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
    
    def get_duration_seconds(self) -> int:
        """Get duration in seconds."""
        return self.duration_ms // 1000
    
    def get_primary_artist(self) -> str:
        """Get primary (first) artist."""
        return self.artists[0] if self.artists else "Unknown Artist"
    
    def get_all_artists_string(self) -> str:
        """Get all artists as comma-separated string."""
        return ", ".join(self.artists) if self.artists else "Unknown Artist"


class SpotifyClient:
    """Client for interacting with Spotify Web API."""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Spotify client.
        
        Args:
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp: Optional[spotipy.Spotify] = None
        self._authenticated = False
        
        logger.info("Spotify client initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Spotify API using OAuth.
        This will open a browser for user authorization.
        
        Returns:
            True if authentication successful
        """
        try:
            # Use OAuth with user authorization to access playlists
            scope = "playlist-read-private playlist-read-collaborative"
            
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri="http://127.0.0.1:9900/",
                scope=scope,
                open_browser=True,
                cache_path=".spotify_cache"
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Test authentication
            self.sp.current_user()
            
            self._authenticated = True
            logger.info("Successfully authenticated with Spotify API")
            return True
        
        except Exception as e:
            logger.error(f"Failed to authenticate with Spotify API: {e}")
            self._authenticated = False
            return False
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated."""
        if not self._authenticated or not self.sp:
            raise RuntimeError("Spotify client not authenticated. Call authenticate() first.")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_playlist_info(self, playlist_url: str) -> PlaylistInfo:
        """
        Get playlist metadata.
        
        Args:
            playlist_url: Spotify playlist URL or ID
            
        Returns:
            PlaylistInfo object
        """
        self._ensure_authenticated()
        
        from .utils import extract_playlist_id
        
        # Extract playlist ID from URL
        playlist_id = extract_playlist_id(playlist_url)
        if not playlist_id:
            # Assume it's already an ID
            playlist_id = playlist_url
        
        try:
            playlist = self.sp.playlist(playlist_id)
            
            # Debug: log the structure
            logger.debug(f"Playlist data keys: {playlist.keys() if playlist else 'None'}")
            
            # Extract image URL
            image_url = None
            if playlist.get('images') and len(playlist['images']) > 0:
                image_url = playlist['images'][0]['url']
            
            # Handle different response structures
            tracks_info = playlist.get('tracks', {})
            total_tracks = tracks_info.get('total', 0) if isinstance(tracks_info, dict) else 0
            
            info = PlaylistInfo(
                id=playlist.get('id', playlist_id),
                name=playlist.get('name', 'Unknown Playlist'),
                description=playlist.get('description', ''),
                owner=playlist.get('owner', {}).get('display_name', 'Unknown'),
                total_tracks=total_tracks,
                url=playlist.get('external_urls', {}).get('spotify', ''),
                image_url=image_url
            )
            
            logger.info(f"Retrieved playlist info: {info.name} ({info.total_tracks} tracks)")
            return info
        
        except Exception as e:
            logger.error(f"Failed to get playlist info: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        """
        Get all tracks from a playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of Track objects
        """
        self._ensure_authenticated()
        
        tracks = []
        
        try:
            # Get full playlist with tracks included
            playlist = self.sp.playlist(playlist_id)
            
            # Extract tracks from the 'items' or 'tracks' key
            tracks_data = playlist.get('items') or playlist.get('tracks', {})
            
            if isinstance(tracks_data, dict):
                # If it's a dict, get the items from it
                items = tracks_data.get('items', [])
                next_url = tracks_data.get('next')
            else:
                # If it's already a list
                items = tracks_data if isinstance(tracks_data, list) else []
                next_url = None
            
            # Process first batch of tracks
            for item in items:
                track_data = item.get('item') or item.get('track')
                if not track_data or not track_data.get('id'):
                    continue
                
                track = self._parse_track(track_data)
                if track:
                    tracks.append(track)
            
            # Fetch remaining tracks if there are more pages
            while next_url:
                results = self.sp.next(next_url)
                if not results:
                    break
                
                items = results.get('items', [])
                for item in items:
                    track_data = item.get('item') or item.get('track')
                    if not track_data or not track_data.get('id'):
                        continue
                    
                    track = self._parse_track(track_data)
                    if track:
                        tracks.append(track)
                
                next_url = results.get('next')
            
            logger.info(f"Retrieved {len(tracks)} tracks from playlist {playlist_id}")
            return tracks
        
        except Exception as e:
            logger.error(f"Failed to get playlist tracks: {e}")
            raise
    
    def _parse_track(self, track_data: Dict[str, Any]) -> Optional[Track]:
        """
        Parse track data from Spotify API response.
        
        Args:
            track_data: Track data dictionary
            
        Returns:
            Track object or None if parsing fails
        """
        try:
            # Extract artists
            artists = [artist['name'] for artist in track_data.get('artists', [])]
            
            # Extract album info
            album_data = track_data.get('album', {})
            album_name = album_data.get('name', 'Unknown Album')
            album_artist = album_data.get('artists', [{}])[0].get('name', artists[0] if artists else 'Unknown')
            release_date = album_data.get('release_date', '')
            
            # Extract album image
            album_image_url = None
            if album_data.get('images') and len(album_data['images']) > 0:
                # Get highest resolution image (first in list)
                album_image_url = album_data['images'][0]['url']
            
            # Extract ISRC
            external_ids = track_data.get('external_ids', {})
            isrc = external_ids.get('isrc')
            
            # Note: Spotify API doesn't provide genres at track level
            # Genres would need to be fetched from artist endpoint
            
            track = Track(
                id=track_data['id'],
                name=track_data['name'],
                artists=artists,
                album=album_name,
                album_artist=album_artist,
                duration_ms=track_data.get('duration_ms', 0),
                track_number=track_data.get('track_number', 0),
                disc_number=track_data.get('disc_number', 1),
                release_date=release_date,
                isrc=isrc,
                genres=[],  # Would need separate API call
                popularity=track_data.get('popularity', 0),
                explicit=track_data.get('explicit', False),
                album_image_url=album_image_url
            )
            
            return track
        
        except Exception as e:
            logger.warning(f"Failed to parse track data: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def get_track_metadata(self, track_id: str) -> Optional[Track]:
        """
        Get metadata for a single track.
        
        Args:
            track_id: Spotify track ID
            
        Returns:
            Track object or None if not found
        """
        self._ensure_authenticated()
        
        try:
            track_data = self.sp.track(track_id)
            return self._parse_track(track_data)
        
        except Exception as e:
            logger.error(f"Failed to get track metadata for {track_id}: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SpotifyException)
    )
    def search_track(self, query: str, limit: int = 10) -> List[Track]:
        """
        Search for tracks.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of Track objects
        """
        self._ensure_authenticated()
        
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            tracks = []
            
            for item in results['tracks']['items']:
                track = self._parse_track(item)
                if track:
                    tracks.append(track)
            
            return tracks
        
        except Exception as e:
            logger.error(f"Failed to search tracks: {e}")
            return []
    
    def get_artist_genres(self, artist_id: str) -> List[str]:
        """
        Get genres for an artist.
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            List of genre strings
        """
        self._ensure_authenticated()
        
        try:
            artist = self.sp.artist(artist_id)
            return artist.get('genres', [])
        
        except Exception as e:
            logger.warning(f"Failed to get artist genres: {e}")
            return []
    
    def get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """
        Get album information.
        
        Args:
            album_id: Spotify album ID
            
        Returns:
            Album data dictionary or None
        """
        self._ensure_authenticated()
        
        try:
            return self.sp.album(album_id)
        
        except Exception as e:
            logger.warning(f"Failed to get album info: {e}")
            return None
    
    def validate_playlist_url(self, url: str) -> bool:
        """
        Validate if URL is a valid Spotify playlist.
        
        Args:
            url: Playlist URL to validate
            
        Returns:
            True if valid
        """
        from .utils import extract_playlist_id, validate_url
        
        if not validate_url(url):
            return False
        
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            return False
        
        try:
            self._ensure_authenticated()
            self.sp.playlist(playlist_id, fields='id')
            return True
        
        except Exception:
            return False
    
    def __repr__(self) -> str:
        """String representation."""
        status = "authenticated" if self._authenticated else "not authenticated"
        return f"SpotifyClient({status})"

# Made with Bob
