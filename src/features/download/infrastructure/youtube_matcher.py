"""
YouTube track matching and search functionality.
"""

import re
from typing import Optional, List, Dict, Any
import logging
from src.app.config import AppConfig
from src.features.spotify.domain.repositories import SpotifyTrack
from src.shared.lib.utils import clean_search_query
from src.shared.lib.cache import YouTubeCache

try:
    from unidecode import unidecode
except Exception:  # pragma: no cover - graceful fallback if dep missing
    def unidecode(text: str) -> str:
        return text

logger = logging.getLogger(__name__)

# A YouTube result we cannot length-verify, or whose length differs from the
# Spotify track by more than this many seconds, is treated as a different track
# and rejected. Correctness over recall: better to skip than grab the wrong song.
DURATION_GATE_SECONDS = 15


class YouTubeMatcher:
    """Matches Spotify tracks to YouTube videos."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize YouTube matcher.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.settings = {
            'max_results': config.search.max_results,
            'use_isrc': config.search.use_isrc
        }
        
        # Initialize cache
        cache_enabled = config.cache.enabled
        cache_dir = str(config.cache.youtube_dir)
        cache_ttl = config.cache.max_age_days * 86400  # Convert days to seconds
        
        self.cache = YouTubeCache(cache_dir, cache_ttl) if cache_enabled else None
        
        if self.cache:
            logger.info(f"YouTube matcher initialized with cache (TTL: {cache_ttl}s)")
        else:
            logger.info("YouTube matcher initialized without cache")
    
    def search_track(self, track: SpotifyTrack) -> Optional[str]:
        """
        Search for track on YouTube and return best match URL.
        Uses cache to avoid redundant searches.
        
        Args:
            track: Track object with metadata
            
        Returns:
            YouTube video URL or None if not found
        """
        # Check cache first
        if self.cache:
            cached_url = self.cache.get(track.id)
            if cached_url:
                logger.debug(f"Cache hit for track '{track.name}': {cached_url}")
                return cached_url
        
        # Build search queries using templates
        queries = self.build_search_queries(track)
        
        logger.info(f"Starting search for '{track.artist} - {track.name}' with {len(queries)} query variations")
        
        for idx, query in enumerate(queries, 1):
            logger.debug(f"Attempt {idx}/{len(queries)}: Searching with query: '{query}'")
            
            try:
                # Use yt-dlp to search
                video_url = self._search_with_ytdlp(query, track)
                
                if video_url:
                    logger.info(f"✓ Found YouTube match for '{track.name}' on attempt {idx}: {video_url}")
                    
                    # Cache the result
                    if self.cache:
                        self.cache.set(track.id, video_url)
                    
                    return video_url
                else:
                    logger.debug(f"  No acceptable match found with this query")
            
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue
        
        logger.error(f"✗ No YouTube match found after {len(queries)} attempts for: {track.name} by {track.artist}")
        return None
    
    def build_search_queries(self, track: SpotifyTrack) -> List[str]:
        """
        Build search queries from track metadata using templates.
        
        Args:
            track: Track object
            
        Returns:
            List of search query strings
        """
        artist = track.artist
        title = track.name
        
        # Clean up artist and title
        artist_clean = clean_search_query(artist)
        title_clean = clean_search_query(title)
        
        queries = []
        # Расширенный список поисковых шаблонов для лучшего нахождения редких треков
        templates = self.settings.get('search_templates', [
            '{artist} - {title} official audio',
            '{artist} - {title} audio',
            '{artist} {title} lyrics',
            '{title} {artist}',
            # НОВЫЕ ШАБЛОНЫ для редких треков и ремиксов:
            '{artist} {title}',  # Без дефиса
            '"{artist}" "{title}"',  # С кавычками для точного поиска
            '{title} {artist} official',
            '{artist} - {title}',  # Простой формат
        ])
        
        for template in templates:
            try:
                query = template.format(artist=artist_clean, title=title_clean)
                queries.append(query)
                logger.debug(f"Generated search query: {query}")
            except KeyError as e:
                logger.warning(f"Invalid search template: {template} - {e}")
        
        # Специальная обработка для ремиксов и edits
        if '(' in title and ')' in title:
            # Извлечь базовое название без скобок
            base_title = title.split('(')[0].strip()
            remix_info = title.split('(')[1].split(')')[0]
            
            base_title_clean = clean_search_query(base_title)
            remix_info_clean = clean_search_query(remix_info)
            
            # Добавить альтернативные поиски для ремиксов
            remix_queries = [
                f'{artist_clean} {base_title_clean}',
                f'{artist_clean} {base_title_clean} {remix_info_clean}',
                f'{base_title_clean} {artist_clean}',
                f'{artist_clean} - {base_title_clean} {remix_info_clean}',
            ]
            
            for query in remix_queries:
                queries.append(query)
                logger.debug(f"Generated remix search query: {query}")
        
        return queries
    
    def _search_with_ytdlp(self, query: str, track: SpotifyTrack) -> Optional[str]:
        """
        Search YouTube using yt-dlp.
        
        Args:
            query: Search query
            track: Track object for validation
            
        Returns:
            Video URL or None
        """
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            # extract_flat MUST stay False: flat search results omit 'duration'
            # and 'view_count', the exact fields needed to verify a result is the
            # right track. With them missing every result scored ~0 and an
            # unrelated video was accepted — the root cause of wrong downloads.
            'extract_flat': False,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for videos
                search_results = ydl.extract_info(f"ytsearch5:{query}", download=False)
                
                if not search_results or 'entries' not in search_results:
                    return None
                
                # Filter and rank results
                best_match = self._find_best_match(search_results['entries'], track)
                
                if best_match:
                    return f"https://www.youtube.com/watch?v={best_match['id']}"
        
        except Exception as e:
            logger.error(f"yt-dlp search error: {e}")
        
        return None
    
    def _find_best_match(self, results: List[Dict[str, Any]], track: SpotifyTrack) -> Optional[Dict[str, Any]]:
        """
        Find best matching video from search results.
        
        Args:
            results: List of video results
            track: Track object for comparison
            
        Returns:
            Best matching video dict or None
        """
        if not results:
            return None

        track_duration = (track.duration_ms or 0) / 1000.0
        tolerance = self.settings.get('duration_tolerance', DURATION_GATE_SECONDS)

        if track_duration <= 0:
            logger.warning(
                f"No Spotify duration for '{track.artist} - {track.name}'; "
                f"duration gate disabled, relying on title+artist gate only"
            )

        eligible = []
        rejected = 0
        logger.debug(
            f"Analyzing {len(results)} results for '{track.artist} - {track.name}' "
            f"(expected {track_duration:.0f}s)"
        )

        for idx, video in enumerate(results):
            if not video:
                continue

            title = video.get('title') or ''
            duration = video.get('duration') or 0

            # HARD GATE 1 — duration must be verifiable and close. Spotify always
            # provides duration_ms; a result we cannot length-check, or whose
            # length is off, is almost certainly a different track.
            if track_duration > 0:
                if not duration:
                    rejected += 1
                    logger.debug(f"  reject #{idx + 1} (no duration): '{title}'")
                    continue
                if abs(duration - track_duration) > tolerance:
                    rejected += 1
                    logger.debug(
                        f"  reject #{idx + 1} (duration {duration}s vs {track_duration:.0f}s): '{title}'"
                    )
                    continue

            # HARD GATE 2 — the title must actually reference this track, so a
            # coincidentally same-length but unrelated video is never accepted.
            uploader = video.get('uploader') or video.get('channel') or ''
            if not self._has_text_relevance(title, track, uploader):
                rejected += 1
                logger.debug(f"  reject #{idx + 1} (title unrelated): '{title}'")
                continue

            score = self._calculate_match_score(video, track)
            eligible.append((score, video))
            logger.debug(f"  candidate #{idx + 1} score={score:.1f} duration={duration}s: '{title}'")

        if not eligible:
            logger.warning(
                f"No track-correct match for '{track.artist} - {track.name}': "
                f"{len(results)} results, {rejected} rejected by duration/title gates"
            )
            return None

        # Rank the eligible (already track-correct) candidates by quality score.
        eligible.sort(key=lambda x: x[0], reverse=True)
        best_score, best_video = eligible[0]
        logger.info(
            f"Match (score {best_score:.1f}) for '{track.artist} - {track.name}': "
            f"'{best_video.get('title', 'Unknown')}'"
        )
        return best_video

    @staticmethod
    def _word_set(text: str) -> set:
        """Whole-word token set, transliterated to ASCII and lowercased."""
        return set(re.findall(r'\w+', unidecode(text or '').lower()))

    @staticmethod
    def _word_list(text: str, min_len: int) -> List[str]:
        """Ordered whole-word tokens of at least `min_len` chars (ASCII, lower)."""
        return [w for w in re.findall(r'\w+', unidecode(text or '').lower()) if len(w) >= min_len]

    def _has_text_relevance(self, title: str, track: SpotifyTrack, uploader: str = '') -> bool:
        """Return True if the video plausibly refers to this track.

        Two requirements, both transliterated to ASCII (so Cyrillic/Greek/etc.
        track names match Latin-transliterated YouTube titles) and matched on
        whole words (so 'in' does not match inside 'living'):
          1. at least 60% of the track-title words appear in the video title;
          2. the primary artist appears in the video title OR the uploader/channel
             (the latter covers auto-generated "Topic" uploads whose visible title
             omits the artist).
        """
        title_set = self._word_set(title)
        uploader_set = self._word_set(uploader)

        title_words = self._word_list(track.name, min_len=2) or self._word_list(track.name, min_len=1)
        artist_words = self._word_list(track.artist, min_len=2) or self._word_list(track.artist, min_len=1)

        if not title_words:
            return False

        title_hits = sum(1 for w in title_words if w in title_set)
        title_ratio = title_hits / len(title_words)

        if artist_words:
            artist_present = any(w in title_set or w in uploader_set for w in artist_words)
        else:
            artist_present = True

        return title_ratio >= 0.6 and artist_present

    def _calculate_match_score(self, video: Dict[str, Any], track: SpotifyTrack) -> float:
        """
        Calculate match score for a video.
        
        Args:
            video: Video metadata dict
            track: Track object
            
        Returns:
            Match score (higher is better)
        """
        score = 0.0
        
        title = video.get('title', '').lower()
        duration = video.get('duration', 0)
        
        # Check duration match (most important)
        if duration and track.duration_ms:
            track_duration = track.duration_ms / 1000  # Convert ms to seconds
            duration_diff = abs(duration - track_duration)
            tolerance = self.settings.get('duration_tolerance', DURATION_GATE_SECONDS)
            
            if duration_diff <= tolerance:
                # Perfect match
                score += 50.0
            elif duration_diff <= tolerance * 2:
                # Close match
                score += 25.0
            else:
                # Duration too different, penalize heavily
                score -= 30.0
        
        # Check for "official" in title
        if self.settings.get('prefer_official', True):
            if 'official' in title:
                score += 20.0
            if 'official audio' in title or 'official video' in title:
                score += 10.0
        
        # Check for artist name in title
        artist = track.artist.lower()
        if artist in title:
            score += 15.0
        
        # Check for track name in title
        track_name = track.name.lower()
        if track_name in title:
            score += 15.0
        
        # Penalize live performances
        if self.settings.get('avoid_live', True):
            if any(word in title for word in ['live', 'concert', 'tour']):
                score -= 20.0
        
        # Penalize covers and remixes (но не если трек сам является ремиксом)
        track_is_remix = any(word in track.name.lower() for word in ['remix', 'edit', 'mix', 'version'])
        
        if self.settings.get('avoid_covers', True):
            if 'cover' in title or 'karaoke' in title:
                score -= 15.0
            # Не штрафуем за remix/edit если исходный трек сам является ремиксом
            if not track_is_remix:
                if 'remix' in title or 'edit' in title:
                    score -= 10.0
            if 'instrumental' in title and 'instrumental' not in track.name.lower():
                score -= 15.0

        # Prefer the original studio recording over alternate renditions, unless
        # the track itself is that kind of version. Ranking-only: every candidate
        # here already passed the duration + title gates (same song), so this just
        # nudges the original ahead of piano/acoustic/8-bit/etc. re-recordings.
        alt_version_markers = [
            'piano', 'pianoforte', 'acoustic', 'orchestral', 'symphonic',
            '8 bit', '8-bit', 'nightcore', 'sped up', 'slowed', 'reverb',
            'metal version', 'cover version',
        ]
        track_lower = track.name.lower()
        for marker in alt_version_markers:
            if marker in title and marker not in track_lower:
                score -= 15.0
                break
        
        # Prefer videos with "audio" in title
        if 'audio' in title:
            score += 10.0
        
        # Prefer videos with "lyrics" if no official audio found
        if 'lyrics' in title and 'official' not in title:
            score += 5.0
        
        # Check view count (higher is often more reliable)
        view_count = video.get('view_count', 0)
        if view_count:
            if view_count > 10_000_000:
                score += 10.0
            elif view_count > 1_000_000:
                score += 5.0
            elif view_count < 10_000:
                score -= 5.0
        
        return score
    
    def verify_duration(self, video_duration: int, track_duration: int) -> bool:
        """
        Verify if video duration matches track duration.
        
        Args:
            video_duration: Video duration in seconds
            track_duration: Track duration in seconds
            
        Returns:
            True if durations match within tolerance
        """
        tolerance = self.settings.get('duration_tolerance', 10)
        diff = abs(video_duration - track_duration)
        return diff <= tolerance
    
    def get_video_info(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information from URL.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Video info dict or None
        """
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info
        
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
    
    def validate_video_url(self, url: str) -> bool:
        """
        Validate if URL is a valid YouTube video.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid YouTube URL
        """
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        ]
        
        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    def __repr__(self) -> str:
        """String representation."""
        return f"YouTubeMatcher(prefer_official={self.settings.get('prefer_official')})"

# Made with Bob
