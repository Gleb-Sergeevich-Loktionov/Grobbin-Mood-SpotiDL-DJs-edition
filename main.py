#!/usr/bin/env python3
"""
Spotify Playlist Downloader - Main Entry Point
Download Spotify playlists as high-quality audio files.
"""

import sys
from pathlib import Path
from src.app.providers import create_container


def main():
    """
    Главная точка входа приложения.
    Использует DI контейнер для управления зависимостями.
    """
    try:
        # Создать DI контейнер
        container = create_container()
        
        # Получить CLI из контейнера
        cli = container.cli()
        
        # Запустить CLI
        return cli.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        return 130
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
