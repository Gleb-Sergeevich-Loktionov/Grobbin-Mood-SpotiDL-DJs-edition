"""
YouTube track matching and search functionality.
"""

import re
from typing import Optional, List, Dict, Any
import logging
from src.app.config import AppConfig
from src.features.spotify.domain.repositories import SpotifyTrack
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

# Version keywords that make a recording a DIFFERENT track from the original.
# Multi-word / more specific phrases come first so the collapse logic in
# _version_tokens can drop the looser substrings ('mix'/'edit') they imply.
_VERSION_KEYWORDS = (
    'remix', 'radio edit', 'extended mix', 'extended', 'club mix', 'vip',
    'bootleg', 'rework', 'edit', 'live', 'acoustic', 'unplugged',
    'instrumental', 'karaoke', 'cover', 'reprise', 'demo', 'remaster',
    'remastered', 'mono', 'nightcore', 'sped up', 'slowed', 'mix', 'version',
)

# Qualifiers that appear on legitimate ORIGINALS and must NOT count as a version
# difference (so 'Stay (feat. X) [Official Audio]' stays "original").
_NEUTRAL_QUALIFIERS = (
    'feat', 'ft', 'featuring', 'official', 'audio', 'video', 'lyrics', 'lyric',
    'hd', 'hq', '4k', 'explicit', 'clean', 'prod', 'mv', 'mp3',
)


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

        # Gather candidates from ALL queries, then pick the single best. Returning
        # on the first query that yields *anything* (the old behavior) let a weaker
        # early query ('… official audio') win and never reach the plain query that
        # actually surfaces the correct video for niche/remix tracks.
        seen_ids = set()
        all_candidates = []  # (score, video)

        for idx, query in enumerate(queries, 1):
            logger.debug(f"Attempt {idx}/{len(queries)}: Searching with query: '{query}'")
            try:
                results = self._search_results(query)
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue

            for score, video in self._eligible_candidates(results, track):
                vid = video.get('id')
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                all_candidates.append((score, video))

        if not all_candidates:
            logger.error(
                f"✗ No YouTube match found after {len(queries)} attempts for: "
                f"{track.name} by {track.artist}"
            )
            return None

        all_candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_video = all_candidates[0]
        video_url = f"https://www.youtube.com/watch?v={best_video['id']}"
        logger.info(
            f"✓ Best match (score {best_score:.1f}) for '{track.artist} - {track.name}' "
            f"across {len(queries)} queries: '{best_video.get('title', 'Unknown')}' {video_url}"
        )

        if self.cache:
            self.cache.set(track.id, video_url)

        return video_url
    
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

        # IMPORTANT: keep the FULL title, version qualifier included. The old code
        # ran clean_search_query() over the title, which strips '(David Penn Remix)'
        # etc. — so the search never surfaced the right version and HARD GATE 3
        # later rejected everything. We only collapse whitespace, never drop the
        # version. A separate base-title (no parens) query is added below as a
        # fallback for tracks whose YouTube title formats the version differently.
        full_title = re.sub(r'\s+', ' ', title).strip()
        # Drop only a trailing "feat./ft." credit for the artist token; keep title.
        artist_clean = re.sub(r'\s+', ' ',
                              re.sub(r'\b(feat\.|ft\.|featuring)\b.*', '', artist, flags=re.IGNORECASE)).strip()

        # Base title without any parenthetical/bracket qualifier (for the fallback
        # queries only). e.g. 'Infinity - Extended Mix' -> 'Infinity'.
        base_title = re.sub(r'[\(\[].*', '', full_title)
        base_title = re.sub(r'\s*-\s*[^-]*\b(remix|edit|mix|version|dub)\b.*$', '', base_title,
                            flags=re.IGNORECASE).strip() or full_title

        queries = []
        seen = set()

        def add(q: str) -> None:
            q = re.sub(r'\s+', ' ', q).strip()
            if q and q.lower() not in seen:
                seen.add(q.lower())
                queries.append(q)
                logger.debug(f"Generated search query: {q}")

        # Plain 'artist title' first — the probe showed it is the single most
        # reliable query for niche tracks. 'official audio' is appended LAST because
        # it pushes niche/Topic uploads out of the top results.
        add(f'{artist_clean} {full_title}')
        add(f'{artist_clean} - {full_title}')
        add(f'{full_title} {artist_clean}')
        add(f'"{artist_clean}" "{full_title}"')
        # Fallbacks using the base title (helps when YouTube splits the version off
        # the title or formats it differently than Spotify).
        if base_title.lower() != full_title.lower():
            add(f'{artist_clean} {base_title}')
            add(f'{base_title} {artist_clean}')
        # Lower-priority decorated queries last.
        add(f'{artist_clean} - {full_title} audio')
        add(f'{artist_clean} - {full_title} official audio')

        return queries
    
    def _search_results(self, query: str) -> List[Dict[str, Any]]:
        """Run one YouTube search and return the raw result entries.

        A failure on a single entry (e.g. an age-gated video that needs cookies)
        must not abort the whole search — yt-dlp already skips such entries, and
        we still get the rest. Returns [] on a hard error.
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
            # Keep going if one entry in the search fails to extract.
            'ignoreerrors': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(f"ytsearch{self.settings['max_results']}:{query}", download=False)
            if not search_results or 'entries' not in search_results:
                return []
            return [e for e in (search_results.get('entries') or []) if e]
        except Exception as e:
            logger.error(f"yt-dlp search error: {e}")
            return []

    def _eligible_candidates(self, results: List[Dict[str, Any]], track: SpotifyTrack) -> List[tuple]:
        """Apply the three hard gates and return [(score, video), …] survivors.

        Gates (correctness over recall — skip beats wrong track):
          1. duration close to the Spotify track (when known);
          2. title/artist relevance;
          3. version equality (original vs remix/live/edit/…).
        """
        if not results:
            return []

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

            # HARD GATE 1 — duration must be verifiable and close.
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

            # HARD GATE 2 — the title must actually reference this track.
            uploader = video.get('uploader') or video.get('channel') or ''
            if not self._has_text_relevance(title, track, uploader):
                rejected += 1
                logger.debug(f"  reject #{idx + 1} (title unrelated): '{title}'")
                continue

            # HARD GATE 3 — the VERSION must match (original vs remix/live/edit/…).
            if not self._version_matches(title, track):
                rejected += 1
                logger.debug(f"  reject #{idx + 1} (version mismatch): '{title}'")
                continue

            score = self._calculate_match_score(video, track)
            eligible.append((score, video))
            logger.debug(f"  candidate #{idx + 1} score={score:.1f} duration={duration}s: '{title}'")

        if not eligible:
            logger.debug(
                f"No track-correct match in this result set for "
                f"'{track.artist} - {track.name}': {len(results)} results, {rejected} rejected"
            )
        return eligible

    def _find_best_match(self, results: List[Dict[str, Any]], track: SpotifyTrack) -> Optional[Dict[str, Any]]:
        """
        Find best matching video from search results.
        
        Args:
            results: List of video results
            track: Track object for comparison
            
        Returns:
            Best matching video dict or None
        """
        eligible = self._eligible_candidates(results, track)
        if not eligible:
            logger.warning(
                f"No track-correct match for '{track.artist} - {track.name}' "
                f"among {len(results)} results"
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

    @classmethod
    def _version_tokens(cls, text: str) -> frozenset:
        """Return the set of version keywords present in `text`.

        An empty set means "original recording". Neutral qualifiers
        (feat/official/audio/explicit/…) are never version tokens, so
        'Stay (feat. X) [Official Audio]' is still treated as the original.
        """
        folded = unidecode(text or '').lower()
        found = set()
        for kw in _VERSION_KEYWORDS:
            # Whole-word / phrase match (not substring), so 'mix' does not fire on
            # 'remix' and 'edit' does not fire inside unrelated words.
            if re.search(r'\b' + re.escape(kw) + r'\b', folded):
                found.add(kw)
        # 'Original Mix' / 'Original Version' / 'Album Version' etc. ARE the
        # original recording, not an alternate version. When the loose 'mix' /
        # 'version' / 'edit' / 'extended' tokens are qualified by 'original' or
        # 'album', drop them so the track reads as the original. A genuine alternate
        # (remix/club mix/radio edit/…) keeps its specific keyword and is unaffected.
        if re.search(r'\b(original|album)\b', folded):
            found.discard('mix')
            found.discard('version')
            found.discard('edit')
            found.discard('extended')
        # Collapse looser keywords implied by a more specific one already present,
        # so 'remix'/'radio edit'/'extended mix' don't also register as 'mix'/'edit'.
        if 'remix' in found:
            found.discard('mix')
            found.discard('edit')
        if 'radio edit' in found or 'extended mix' in found or 'club mix' in found:
            found.discard('mix')
            found.discard('edit')
            found.discard('extended')
        return frozenset(found)

    def _version_matches(self, candidate_title: str, track: SpotifyTrack) -> bool:
        """True only if the candidate is the SAME version as the Spotify track.

        Hard rule, both directions:
          * track is original  -> candidate must carry NO version keyword;
          * track is a version -> candidate must carry the SAME primary version keyword.
        This is what guarantees 'Officer John - Stay' never downloads
        'Officer John - Stay (... Remix)' and vice versa.
        """
        track_v = self._version_tokens(track.name)
        cand_v = self._version_tokens(candidate_title)

        if not track_v:
            # Original wanted: reject anything carrying a version keyword.
            return not cand_v

        # Specific version wanted: candidate must share at least the primary keyword.
        return bool(track_v & cand_v)

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

        # Artist fallback: some uploads (label channels, '… - Topic' auto-uploads,
        # reposts) carry neither the artist in the visible title nor a matching
        # channel name. Relax the artist check ONLY when the title is distinctive
        # enough that a same-length collision is implausible: the FULL track title
        # is present AND it is either long (3+ words) or carries a version qualifier
        # (remix/edit/…). A short generic title like 'Instant Crush' still requires
        # the artist. The duration + version gates remain in force either way.
        if not artist_present and title_hits == len(title_words):
            full_title_present = title_hits == len(title_words)
            distinctive = len(title_words) >= 3 or bool(self._version_tokens(track.name))
            if full_title_present and distinctive:
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

        # Tie-break among same-version remix candidates: prefer the one whose title
        # also carries the remixer name. The version gate already guarantees both
        # are remixes; this just nudges the right remixer ahead. Ranking-only.
        if track_is_remix and '(' in track.name:
            paren = track.name[track.name.find('(') + 1:]
            paren = paren.split(')')[0] if ')' in paren else paren
            remixer_words = [
                w for w in self._word_list(paren, min_len=3)
                if w not in {'remix', 'edit', 'mix', 'version', 'extended', 'radio', 'club'}
            ]
            if remixer_words and any(w in title for w in remixer_words):
                score += 8.0

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
