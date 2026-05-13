"""
Strategy Pattern для алгоритмов поиска и обработки.

Предоставляет различные стратегии для поиска треков и обработки результатов.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .models import Track
from .interfaces import IMatcher


class IMatchingStrategy(ABC):
    """Интерфейс стратегии поиска треков."""
    
    @abstractmethod
    def match(self, track: Track) -> Optional[str]:
        """
        Найти трек используя данную стратегию.
        
        Args:
            track: Информация о треке
            
        Returns:
            URL найденного трека или None
        """
        pass
    
    @abstractmethod
    def get_confidence_score(self, track: Track, result: Dict[str, Any]) -> float:
        """
        Оценить уверенность в совпадении (0.0 - 1.0).
        
        Args:
            track: Исходный трек
            result: Результат поиска
            
        Returns:
            Оценка уверенности от 0.0 до 1.0
        """
        pass


class ExactMatchStrategy(IMatchingStrategy):
    """Стратегия точного совпадения по названию и исполнителю."""
    
    def __init__(self, matcher: IMatcher, min_confidence: float = 0.9):
        """
        Args:
            matcher: Матчер для поиска
            min_confidence: Минимальная уверенность для принятия результата
        """
        self.matcher = matcher
        self.min_confidence = min_confidence
    
    def match(self, track: Track) -> Optional[str]:
        """Поиск с точным совпадением."""
        results = self.matcher.search(track.search_query, limit=5)
        
        for result in results:
            confidence = self.get_confidence_score(track, result)
            if confidence >= self.min_confidence:
                return result.get('url')
        
        return None
    
    def get_confidence_score(self, track: Track, result: Dict[str, Any]) -> float:
        """Оценка на основе точного совпадения строк."""
        result_title = result.get('title', '').lower()
        result_artist = result.get('artist', '').lower()
        
        track_title = track.title.lower()
        track_artist = track.artist.lower()
        
        # Точное совпадение
        title_match = track_title in result_title or result_title in track_title
        artist_match = track_artist in result_artist or result_artist in track_artist
        
        if title_match and artist_match:
            return 1.0
        elif title_match or artist_match:
            return 0.5
        return 0.0


class FuzzyMatchStrategy(IMatchingStrategy):
    """Стратегия нечеткого поиска с использованием алгоритмов схожести."""
    
    def __init__(self, matcher: IMatcher, min_confidence: float = 0.7):
        """
        Args:
            matcher: Матчер для поиска
            min_confidence: Минимальная уверенность для принятия результата
        """
        self.matcher = matcher
        self.min_confidence = min_confidence
    
    def match(self, track: Track) -> Optional[str]:
        """Поиск с нечетким совпадением."""
        results = self.matcher.search(track.search_query, limit=10)
        
        best_match = None
        best_score = 0.0
        
        for result in results:
            confidence = self.get_confidence_score(track, result)
            if confidence > best_score:
                best_score = confidence
                best_match = result.get('url')
        
        if best_score >= self.min_confidence:
            return best_match
        
        return None
    
    def get_confidence_score(self, track: Track, result: Dict[str, Any]) -> float:
        """Оценка на основе алгоритма Левенштейна."""
        result_title = result.get('title', '').lower()
        result_artist = result.get('artist', '').lower()
        
        track_title = track.title.lower()
        track_artist = track.artist.lower()
        
        # Используем простую метрику схожести
        title_similarity = self._similarity(track_title, result_title)
        artist_similarity = self._similarity(track_artist, result_artist)
        
        # Взвешенная оценка (название важнее)
        return 0.6 * title_similarity + 0.4 * artist_similarity
    
    @staticmethod
    def _similarity(s1: str, s2: str) -> float:
        """Вычислить схожесть двух строк (0.0 - 1.0)."""
        if not s1 or not s2:
            return 0.0
        
        # Простая метрика на основе общих слов
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


class ISRCMatchStrategy(IMatchingStrategy):
    """Стратегия поиска по ISRC коду (наиболее точная)."""
    
    def __init__(self, matcher: IMatcher):
        """
        Args:
            matcher: Матчер для поиска
        """
        self.matcher = matcher
    
    def match(self, track: Track) -> Optional[str]:
        """Поиск по ISRC коду."""
        if not track.isrc:
            return None
        
        # Поиск по ISRC
        results = self.matcher.search(f"isrc:{track.isrc}", limit=1)
        
        if results:
            return results[0].get('url')
        
        return None
    
    def get_confidence_score(self, track: Track, result: Dict[str, Any]) -> float:
        """ISRC дает 100% уверенность при совпадении."""
        result_isrc = result.get('isrc', '')
        if track.isrc and result_isrc == track.isrc:
            return 1.0
        return 0.0


class CompositeMatchStrategy(IMatchingStrategy):
    """
    Композитная стратегия, пробующая несколько стратегий по очереди.
    
    Использует паттерн Chain of Responsibility.
    """
    
    def __init__(self, strategies: List[IMatchingStrategy]):
        """
        Args:
            strategies: Список стратегий в порядке приоритета
        """
        self.strategies = strategies
    
    def match(self, track: Track) -> Optional[str]:
        """Пробует стратегии по очереди до первого успеха."""
        for strategy in self.strategies:
            result = strategy.match(track)
            if result:
                return result
        
        return None
    
    def get_confidence_score(self, track: Track, result: Dict[str, Any]) -> float:
        """Возвращает максимальную оценку среди всех стратегий."""
        scores = [
            strategy.get_confidence_score(track, result)
            for strategy in self.strategies
        ]
        return max(scores) if scores else 0.0


class MatchingStrategyFactory:
    """Фабрика для создания стратегий поиска."""
    
    @staticmethod
    def create_default_strategy(matcher: IMatcher) -> IMatchingStrategy:
        """
        Создать стратегию по умолчанию.
        
        Использует композитную стратегию с приоритетом:
        1. ISRC (самый точный)
        2. Точное совпадение
        3. Нечеткое совпадение
        
        Args:
            matcher: Матчер для поиска
            
        Returns:
            Композитная стратегия
        """
        return CompositeMatchStrategy([
            ISRCMatchStrategy(matcher),
            ExactMatchStrategy(matcher, min_confidence=0.9),
            FuzzyMatchStrategy(matcher, min_confidence=0.7),
        ])
    
    @staticmethod
    def create_fast_strategy(matcher: IMatcher) -> IMatchingStrategy:
        """
        Создать быструю стратегию (только точное совпадение).
        
        Args:
            matcher: Матчер для поиска
            
        Returns:
            Стратегия точного совпадения
        """
        return ExactMatchStrategy(matcher, min_confidence=0.8)
    
    @staticmethod
    def create_thorough_strategy(matcher: IMatcher) -> IMatchingStrategy:
        """
        Создать тщательную стратегию (все методы с низким порогом).
        
        Args:
            matcher: Матчер для поиска
            
        Returns:
            Композитная стратегия с низкими порогами
        """
        return CompositeMatchStrategy([
            ISRCMatchStrategy(matcher),
            ExactMatchStrategy(matcher, min_confidence=0.7),
            FuzzyMatchStrategy(matcher, min_confidence=0.5),
        ])

# Made with Bob
