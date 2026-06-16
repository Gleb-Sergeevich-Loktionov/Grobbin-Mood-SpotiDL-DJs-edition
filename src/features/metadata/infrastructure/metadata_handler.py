"""
Metadata handling for audio files.
Embeds ID3v2 tags and album artwork.
"""

from __future__ import annotations

import requests
from pathlib import Path
from typing import Optional
from io import BytesIO
import logging
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TRCK, TDRC, TCON, APIC

from src.features.spotify.domain.repositories import SpotifyTrack
from src.app.config import AppConfig

logger = logging.getLogger(__name__)


class MetadataHandler:
    """Handles embedding metadata into audio files."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize metadata handler.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.settings = {
            'download_artwork': config.metadata.download_artwork,
            'embed_lyrics': config.metadata.embed_lyrics,
            'preserve_original': config.metadata.preserve_original
        }
        
        logger.info("Metadata handler initialized")
    
    def embed_metadata(
        self,
        file_path: Path,
        track: SpotifyTrack,
        artwork_url: Optional[str] = None
    ) -> bool:
        """
        Embed metadata into audio file.
        
        Args:
            file_path: Path to audio file
            track: Track metadata
            artwork_url: URL to album artwork
            
        Returns:
            True if successful
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            # Download artwork if enabled
            artwork_data = None
            if self.settings.get('embed_artwork', True) and artwork_url:
                artwork_data = self.download_artwork(artwork_url)
            
            # Determine file format and embed metadata
            suffix = file_path.suffix.lower()
            
            if suffix == '.mp3':
                return self._embed_mp3_metadata(file_path, track, artwork_data)
            elif suffix == '.m4a':
                return self._embed_m4a_metadata(file_path, track, artwork_data)
            elif suffix == '.flac':
                return self._embed_flac_metadata(file_path, track, artwork_data)
            else:
                logger.warning(f"Unsupported file format: {suffix}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to embed metadata: {e}")
            return False
    
    def _embed_mp3_metadata(
        self,
        file_path: Path,
        track: SpotifyTrack,
        artwork_data: Optional[bytes]
    ) -> bool:
        """Embed metadata into MP3 file."""
        try:
            audio = MP3(str(file_path), ID3=ID3)
            
            # Add ID3 tag if it doesn't exist
            try:
                audio.add_tags()
            except Exception:
                pass  # Tags already exist
            
            # Set text frames
            audio.tags.add(TIT2(encoding=3, text=track.name))
            audio.tags.add(TPE1(encoding=3, text=track.get_all_artists_string()))
            audio.tags.add(TALB(encoding=3, text=track.album))
            audio.tags.add(TPE2(encoding=3, text=track.album_artist))
            audio.tags.add(TRCK(encoding=3, text=str(track.track_number)))
            
            # Add year if available
            if track.release_date:
                year = track.release_date.split('-')[0]
                audio.tags.add(TDRC(encoding=3, text=year))
            
            # Add genres if available
            if track.genres:
                audio.tags.add(TCON(encoding=3, text=', '.join(track.genres)))
            
            # Add artwork
            if artwork_data:
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=artwork_data
                    )
                )
            
            audio.save()
            logger.debug(f"Embedded MP3 metadata: {file_path.name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to embed MP3 metadata: {e}")
            return False
    
    def _embed_m4a_metadata(
        self,
        file_path: Path,
        track: SpotifyTrack,
        artwork_data: Optional[bytes]
    ) -> bool:
        """Embed metadata into M4A file."""
        try:
            audio = MP4(str(file_path))
            
            # Set tags
            audio.tags['\xa9nam'] = track.name
            audio.tags['\xa9ART'] = track.get_all_artists_string()
            audio.tags['\xa9alb'] = track.album
            audio.tags['aART'] = track.album_artist
            audio.tags['trkn'] = [(track.track_number, 0)]
            
            # Add year if available
            if track.release_date:
                year = track.release_date.split('-')[0]
                audio.tags['\xa9day'] = year
            
            # Add genres if available
            if track.genres:
                audio.tags['\xa9gen'] = ', '.join(track.genres)
            
            # Add artwork
            if artwork_data:
                audio.tags['covr'] = [MP4.MP4Cover(artwork_data, imageformat=MP4.MP4Cover.FORMAT_JPEG)]
            
            audio.save()
            logger.debug(f"Embedded M4A metadata: {file_path.name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to embed M4A metadata: {e}")
            return False
    
    def _embed_flac_metadata(
        self,
        file_path: Path,
        track: SpotifyTrack,
        artwork_data: Optional[bytes]
    ) -> bool:
        """Embed metadata into FLAC file."""
        try:
            audio = FLAC(str(file_path))
            
            # Set tags
            audio['title'] = track.name
            audio['artist'] = track.get_all_artists_string()
            audio['album'] = track.album
            audio['albumartist'] = track.album_artist
            audio['tracknumber'] = str(track.track_number)
            
            # Add year if available
            if track.release_date:
                year = track.release_date.split('-')[0]
                audio['date'] = year
            
            # Add genres if available
            if track.genres:
                audio['genre'] = ', '.join(track.genres)
            
            # Add artwork
            if artwork_data:
                from mutagen.flac import Picture
                
                picture = Picture()
                picture.type = 3  # Cover (front)
                picture.mime = 'image/jpeg'
                picture.desc = 'Cover'
                picture.data = artwork_data
                
                audio.add_picture(picture)
            
            audio.save()
            logger.debug(f"Embedded FLAC metadata: {file_path.name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to embed FLAC metadata: {e}")
            return False
    
    def download_artwork(self, url: str) -> Optional[bytes]:
        """
        Download and process album artwork.
        
        Args:
            url: URL to artwork image
            
        Returns:
            Image data as bytes or None
        """
        try:
            # Download image
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            
            # Process image
            min_size = self.settings.get('artwork_min_size', 500)
            preferred_size = self.settings.get('artwork_preferred_size', 1000)
            
            processed_data = self.resize_artwork(image_data, min_size, preferred_size)
            
            logger.debug(f"Downloaded artwork from {url}")
            return processed_data
        
        except Exception as e:
            logger.warning(f"Failed to download artwork: {e}")
            return None
    
    def resize_artwork(
        self,
        image_data: bytes,
        min_size: int = 500,
        target_size: int = 1000
    ) -> bytes:
        """
        Resize artwork to target size.
        
        Args:
            image_data: Original image data
            min_size: Minimum acceptable size
            target_size: Target size for resizing
            
        Returns:
            Processed image data
        """
        try:
            # Open image
            image = Image.open(BytesIO(image_data))
            
            # Check if image is too small
            width, height = image.size
            if width < min_size or height < min_size:
                logger.warning(f"Artwork too small: {width}x{height}")
                # Return original if too small
                return image_data
            
            # Resize if larger than target
            if width > target_size or height > target_size:
                # Maintain aspect ratio
                image.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = BytesIO()
                image.save(output, format='JPEG', quality=95)
                return output.getvalue()
            
            # Return original if size is acceptable
            return image_data
        
        except Exception as e:
            logger.warning(f"Failed to resize artwork: {e}")
            return image_data
    
    def sanitize_metadata(self, text: str) -> str:
        """
        Sanitize metadata text.
        
        Args:
            text: Original text
            
        Returns:
            Sanitized text
        """
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit length
        max_length = 255
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def validate_metadata(self, file_path: Path) -> bool:
        """
        Validate that metadata was embedded correctly.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if metadata is present
        """
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.mp3':
                audio = MP3(str(file_path), ID3=ID3)
                return bool(audio.tags)
            
            elif suffix == '.m4a':
                audio = MP4(str(file_path))
                return bool(audio.tags)
            
            elif suffix == '.flac':
                audio = FLAC(str(file_path))
                return bool(audio.tags)
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to validate metadata: {e}")
            return False
    
    def get_metadata(self, file_path: Path) -> Optional[dict]:
        """
        Get metadata from audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary of metadata or None
        """
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.mp3':
                audio = MP3(str(file_path), ID3=ID3)
                if not audio.tags:
                    return None
                
                return {
                    'title': str(audio.tags.get('TIT2', '')),
                    'artist': str(audio.tags.get('TPE1', '')),
                    'album': str(audio.tags.get('TALB', '')),
                    'album_artist': str(audio.tags.get('TPE2', '')),
                    'track_number': str(audio.tags.get('TRCK', '')),
                    'year': str(audio.tags.get('TDRC', '')),
                    'genre': str(audio.tags.get('TCON', ''))
                }
            
            elif suffix == '.m4a':
                audio = MP4(str(file_path))
                if not audio.tags:
                    return None
                
                return {
                    'title': audio.tags.get('\xa9nam', [''])[0],
                    'artist': audio.tags.get('\xa9ART', [''])[0],
                    'album': audio.tags.get('\xa9alb', [''])[0],
                    'album_artist': audio.tags.get('aART', [''])[0],
                    'track_number': str(audio.tags.get('trkn', [(0, 0)])[0][0]),
                    'year': audio.tags.get('\xa9day', [''])[0],
                    'genre': audio.tags.get('\xa9gen', [''])[0]
                }
            
            elif suffix == '.flac':
                audio = FLAC(str(file_path))
                if not audio.tags:
                    return None
                
                return {
                    'title': audio.get('title', [''])[0],
                    'artist': audio.get('artist', [''])[0],
                    'album': audio.get('album', [''])[0],
                    'album_artist': audio.get('albumartist', [''])[0],
                    'track_number': audio.get('tracknumber', [''])[0],
                    'year': audio.get('date', [''])[0],
                    'genre': audio.get('genre', [''])[0]
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MetadataHandler(embed_artwork={self.settings.get('embed_artwork')})"

# Made with Bob
