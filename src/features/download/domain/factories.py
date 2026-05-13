"""
Factory Pattern для создания объектов загрузки.

Предоставляет фабрики для создания загрузчиков, матчеров и других компонентов.
"""

from typing import Dict, Type, Optional
from .interfaces import IDownloader, IMatcher, ICache


class DownloaderFactory:
    """Фабрика для создания загрузчиков разных типов."""
    
    _downloaders: Dict[str, Type[IDownloader]] = {}
    
    @classmethod
    def register(cls, source: str, downloader_class: Type[IDownloader]):
        """
        Зарегистрировать новый тип загрузчика.
        
        Args:
            source: Название источника (youtube, soundcloud, etc.)
            downloader_class: Класс загрузчика
        """
        cls._downloaders[source.lower()] = downloader_class
    
    @classmethod
    def create(cls, source: str, **kwargs) -> IDownloader:
        """
        Создать загрузчик для указанного источника.
        
        Args:
            source: Название источника
            **kwargs: Параметры для конструктора загрузчика
            
        Returns:
            Экземпляр загрузчика
            
        Raises:
            ValueError: Если источник не зарегистрирован
        """
        source = source.lower()
        if source not in cls._downloaders:
            raise ValueError(
                f"Unknown source: {source}. "
                f"Available sources: {', '.join(cls._downloaders.keys())}"
            )
        
        downloader_class = cls._downloaders[source]
        return downloader_class(**kwargs)
    
    @classmethod
    def get_available_sources(cls) -> list[str]:
        """Получить список доступных источников."""
        return list(cls._downloaders.keys())


class MatcherFactory:
    """Фабрика для создания матчеров разных платформ."""
    
    _matchers: Dict[str, Type[IMatcher]] = {}
    
    @classmethod
    def register(cls, platform: str, matcher_class: Type[IMatcher]):
        """
        Зарегистрировать новый тип матчера.
        
        Args:
            platform: Название платформы (youtube, soundcloud, etc.)
            matcher_class: Класс матчера
        """
        cls._matchers[platform.lower()] = matcher_class
    
    @classmethod
    def create(cls, platform: str, **kwargs) -> IMatcher:
        """
        Создать матчер для указанной платформы.
        
        Args:
            platform: Название платформы
            **kwargs: Параметры для конструктора матчера
            
        Returns:
            Экземпляр матчера
            
        Raises:
            ValueError: Если платформа не зарегистрирована
        """
        platform = platform.lower()
        if platform not in cls._matchers:
            raise ValueError(
                f"Unknown platform: {platform}. "
                f"Available platforms: {', '.join(cls._matchers.keys())}"
            )
        
        matcher_class = cls._matchers[platform]
        return matcher_class(**kwargs)
    
    @classmethod
    def get_available_platforms(cls) -> list[str]:
        """Получить список доступных платформ."""
        return list(cls._matchers.keys())


class CacheFactory:
    """Фабрика для создания кеша разных типов."""
    
    _caches: Dict[str, Type[ICache]] = {}
    
    @classmethod
    def register(cls, cache_type: str, cache_class: Type[ICache]):
        """
        Зарегистрировать новый тип кеша.
        
        Args:
            cache_type: Тип кеша (memory, file, redis, etc.)
            cache_class: Класс кеша
        """
        cls._caches[cache_type.lower()] = cache_class
    
    @classmethod
    def create(cls, cache_type: str, **kwargs) -> ICache:
        """
        Создать кеш указанного типа.
        
        Args:
            cache_type: Тип кеша
            **kwargs: Параметры для конструктора кеша
            
        Returns:
            Экземпляр кеша
            
        Raises:
            ValueError: Если тип кеша не зарегистрирован
        """
        cache_type = cache_type.lower()
        if cache_type not in cls._caches:
            raise ValueError(
                f"Unknown cache type: {cache_type}. "
                f"Available types: {', '.join(cls._caches.keys())}"
            )
        
        cache_class = cls._caches[cache_type]
        return cache_class(**kwargs)
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """Получить список доступных типов кеша."""
        return list(cls._caches.keys())


class ComponentFactory:
    """
    Универсальная фабрика для создания компонентов.
    
    Использует паттерн Abstract Factory для создания семейств связанных объектов.
    """
    
    def __init__(
        self,
        downloader_source: str = "youtube",
        matcher_platform: str = "youtube",
        cache_type: str = "file",
        **config
    ):
        """
        Инициализация фабрики компонентов.
        
        Args:
            downloader_source: Источник для загрузки
            matcher_platform: Платформа для поиска
            cache_type: Тип кеша
            **config: Дополнительная конфигурация
        """
        self.downloader_source = downloader_source
        self.matcher_platform = matcher_platform
        self.cache_type = cache_type
        self.config = config
    
    def create_downloader(self, **kwargs) -> IDownloader:
        """Создать загрузчик с текущей конфигурацией."""
        params = {**self.config, **kwargs}
        return DownloaderFactory.create(self.downloader_source, **params)
    
    def create_matcher(self, **kwargs) -> IMatcher:
        """Создать матчер с текущей конфигурацией."""
        params = {**self.config, **kwargs}
        return MatcherFactory.create(self.matcher_platform, **params)
    
    def create_cache(self, **kwargs) -> ICache:
        """Создать кеш с текущей конфигурацией."""
        params = {**self.config, **kwargs}
        return CacheFactory.create(self.cache_type, **params)
    
    def create_all(self) -> tuple[IDownloader, IMatcher, ICache]:
        """
        Создать все компоненты.
        
        Returns:
            Кортеж (downloader, matcher, cache)
        """
        return (
            self.create_downloader(),
            self.create_matcher(),
            self.create_cache()
        )

# Made with Bob
