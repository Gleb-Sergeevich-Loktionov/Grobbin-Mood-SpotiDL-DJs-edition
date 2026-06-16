"""
Interactive setup wizard for Spotify Playlist Downloader.
Helps users configure the application step-by-step.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple
from colorama import Fore, Style, init

# Initialize colorama for Windows support
init(autoreset=True)


class SetupWizard:
    """Interactive setup wizard for first-time configuration."""
    
    def __init__(self):
        """Initialize setup wizard."""
        self.root_dir = Path(__file__).resolve().parents[3]
        self.env_file = self.root_dir / ".env"
        self.env_example = self.root_dir / ".env.example"
        self.config = {}
    
    def run(self) -> bool:
        """
        Run the complete setup wizard.
        
        Returns:
            True if setup completed successfully
        """
        self._print_banner()
        
        print(f"\n{Fore.CYAN}Добро пожаловать в мастер настройки Spotify Playlist Downloader!{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Этот мастер поможет вам настроить приложение за несколько шагов.{Style.RESET_ALL}\n")
        
        # Step 1: Check Python version
        if not self._check_python_version():
            return False
        
        # Step 2: Check FFmpeg
        if not self._check_ffmpeg():
            if not self._offer_ffmpeg_installation():
                print(f"\n{Fore.YELLOW}Предупреждение: FFmpeg не установлен. Некоторые функции могут не работать.{Style.RESET_ALL}")
                if not self._confirm("Продолжить без FFmpeg?"):
                    return False
        
        # Step 3: Configure Spotify API
        if not self._configure_spotify_api():
            return False
        
        # Step 4: Configure download settings
        self._configure_download_settings()
        
        # Step 5: Save configuration
        if not self._save_configuration():
            return False
        
        # Step 6: Test connection
        if self._confirm("\nПроверить подключение к Spotify API?"):
            self._test_spotify_connection()
        
        # Success!
        self._print_success()
        return True
    
    def _print_banner(self) -> None:
        """Print ASCII art banner."""
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ♪  Spotify Playlist Downloader - Setup Wizard  ♪       ║
║                                                           ║
║   Загрузка плейлистов Spotify в высоком качестве         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
        print(banner)
    
    def _check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        print(f"\n{Fore.CYAN}[Шаг 1/6] Проверка версии Python...{Style.RESET_ALL}")
        
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major >= 3 and version.minor >= 8:
            print(f"{Fore.GREEN}✓ Python {version_str} - OK{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Python {version_str} - Требуется Python 3.8 или выше{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Скачайте Python с https://www.python.org/downloads/{Style.RESET_ALL}")
            return False
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed."""
        print(f"\n{Fore.CYAN}[Шаг 2/6] Проверка FFmpeg...{Style.RESET_ALL}")
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version from output
                version_line = result.stdout.split('\n')[0]
                print(f"{Fore.GREEN}✓ FFmpeg установлен: {version_line}{Style.RESET_ALL}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        print(f"{Fore.YELLOW}✗ FFmpeg не найден{Style.RESET_ALL}")
        return False
    
    def _offer_ffmpeg_installation(self) -> bool:
        """Offer to install FFmpeg automatically."""
        system = platform.system()
        
        print(f"\n{Fore.CYAN}FFmpeg необходим для конвертации аудио.{Style.RESET_ALL}")
        
        if system == "Windows":
            print(f"\n{Fore.WHITE}Варианты установки для Windows:{Style.RESET_ALL}")
            print(f"  1. Автоматическая установка через Chocolatey (рекомендуется)")
            print(f"  2. Скачать вручную с https://ffmpeg.org/download.html")
            print(f"  3. Пропустить (не рекомендуется)")
            
            choice = self._input_choice("\nВыберите вариант", ["1", "2", "3"], "1")
            
            if choice == "1":
                return self._install_ffmpeg_chocolatey()
            elif choice == "2":
                print(f"\n{Fore.CYAN}Инструкция по установке FFmpeg вручную:{Style.RESET_ALL}")
                print(f"  1. Скачайте FFmpeg: https://ffmpeg.org/download.html")
                print(f"  2. Распакуйте архив")
                print(f"  3. Добавьте путь к ffmpeg.exe в PATH")
                print(f"  4. Перезапустите терминал")
                print(f"  5. Запустите setup wizard снова")
                return False
            else:
                return False
        
        elif system == "Linux":
            print(f"\n{Fore.WHITE}Установите FFmpeg командой:{Style.RESET_ALL}")
            print(f"  sudo apt-get update && sudo apt-get install ffmpeg")
            print(f"\n{Fore.WHITE}Или для других дистрибутивов:{Style.RESET_ALL}")
            print(f"  sudo yum install ffmpeg  (CentOS/RHEL)")
            print(f"  sudo pacman -S ffmpeg   (Arch Linux)")
            return False
        
        elif system == "Darwin":  # macOS
            print(f"\n{Fore.WHITE}Установите FFmpeg через Homebrew:{Style.RESET_ALL}")
            print(f"  brew install ffmpeg")
            return False
        
        return False
    
    def _install_ffmpeg_chocolatey(self) -> bool:
        """Install FFmpeg using Chocolatey on Windows."""
        print(f"\n{Fore.CYAN}Проверка Chocolatey...{Style.RESET_ALL}")
        
        # Check if Chocolatey is installed
        try:
            result = subprocess.run(
                ["choco", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                raise FileNotFoundError
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            print(f"{Fore.YELLOW}✗ Chocolatey не установлен{Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}Установите Chocolatey:{Style.RESET_ALL}")
            print(f"  1. Откройте PowerShell от имени администратора")
            print(f"  2. Выполните команду с https://chocolatey.org/install")
            print(f"  3. Запустите setup wizard снова")
            return False
        
        print(f"{Fore.GREEN}✓ Chocolatey установлен{Style.RESET_ALL}")
        
        if not self._confirm("\nУстановить FFmpeg через Chocolatey? (требуются права администратора)"):
            return False
        
        print(f"\n{Fore.CYAN}Установка FFmpeg...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Это может занять несколько минут...{Style.RESET_ALL}")
        
        try:
            result = subprocess.run(
                ["choco", "install", "ffmpeg", "-y"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}✓ FFmpeg успешно установлен!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Перезапустите терминал для применения изменений.{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}✗ Ошибка установки FFmpeg{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Вывод: {result.stderr}{Style.RESET_ALL}")
                return False
        except subprocess.TimeoutExpired:
            print(f"{Fore.RED}✗ Превышено время ожидания установки{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
            return False
    
    def _configure_spotify_api(self) -> bool:
        """Configure Spotify API credentials."""
        print(f"\n{Fore.CYAN}[Шаг 3/6] Настройка Spotify API{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}Для работы приложения нужны Spotify API credentials.{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Получите их на: {Fore.CYAN}https://developer.spotify.com/dashboard{Style.RESET_ALL}\n")
        
        print(f"{Fore.YELLOW}Инструкция:{Style.RESET_ALL}")
        print(f"  1. Войдите в Spotify Dashboard")
        print(f"  2. Нажмите 'Create an App'")
        print(f"  3. Заполните название и описание")
        print(f"  4. Скопируйте Client ID и Client Secret")
        
        if not self._confirm("\nУ вас есть Spotify API credentials?"):
            print(f"\n{Fore.YELLOW}Получите credentials и запустите setup wizard снова.{Style.RESET_ALL}")
            return False
        
        # Input Client ID
        while True:
            client_id = self._input_text("\nВведите Spotify Client ID")
            if client_id and len(client_id) == 32:
                self.config['SPOTIPY_CLIENT_ID'] = client_id
                break
            print(f"{Fore.RED}Неверный формат. Client ID должен содержать 32 символа.{Style.RESET_ALL}")
        
        # Input Client Secret
        while True:
            client_secret = self._input_text("Введите Spotify Client Secret")
            if client_secret and len(client_secret) == 32:
                self.config['SPOTIPY_CLIENT_SECRET'] = client_secret
                break
            print(f"{Fore.RED}Неверный формат. Client Secret должен содержать 32 символа.{Style.RESET_ALL}")
        
        # Redirect URI (default)
        self.config['SPOTIPY_REDIRECT_URI'] = 'http://localhost:8888/callback'
        
        print(f"{Fore.GREEN}✓ Spotify API credentials сохранены{Style.RESET_ALL}")
        return True
    
    def _configure_download_settings(self) -> None:
        """Configure download settings."""
        print(f"\n{Fore.CYAN}[Шаг 4/6] Настройка параметров загрузки{Style.RESET_ALL}")
        
        # Output directory
        default_output = str(self.root_dir / "downloads")
        output_dir = self._input_text(
            f"\nДиректория для загрузок (Enter для '{default_output}')",
            default=default_output
        )
        self.config['DEFAULT_OUTPUT_DIR'] = output_dir
        
        # Audio format
        print(f"\n{Fore.WHITE}Выберите аудио формат:{Style.RESET_ALL}")
        print(f"  1. MP3 (рекомендуется, совместим со всеми устройствами)")
        print(f"  2. M4A (AAC, хорошее качество)")
        print(f"  3. FLAC (lossless, большой размер)")
        
        format_choice = self._input_choice("Формат", ["1", "2", "3"], "1")
        format_map = {"1": "mp3", "2": "m4a", "3": "flac"}
        self.config['DEFAULT_AUDIO_FORMAT'] = format_map[format_choice]
        
        # Audio quality
        if format_map[format_choice] == "flac":
            self.config['DEFAULT_AUDIO_QUALITY'] = "lossless"
        else:
            print(f"\n{Fore.WHITE}Выберите качество аудио:{Style.RESET_ALL}")
            print(f"  1. 320 kbps (максимальное качество, рекомендуется)")
            print(f"  2. 256 kbps (высокое качество)")
            print(f"  3. 192 kbps (среднее качество)")
            print(f"  4. 128 kbps (низкое качество, меньший размер)")
            
            quality_choice = self._input_choice("Качество", ["1", "2", "3", "4"], "1")
            quality_map = {"1": "320", "2": "256", "3": "192", "4": "128"}
            self.config['DEFAULT_AUDIO_QUALITY'] = quality_map[quality_choice]
        
        # Concurrent downloads
        print(f"\n{Fore.WHITE}Количество одновременных загрузок (1-10):{Style.RESET_ALL}")
        print(f"  Рекомендуется: 3 (баланс скорости и стабильности)")
        
        while True:
            concurrent = self._input_text("Одновременных загрузок", default="3")
            try:
                concurrent_int = int(concurrent)
                if 1 <= concurrent_int <= 10:
                    self.config['MAX_CONCURRENT_DOWNLOADS'] = str(concurrent_int)
                    break
                print(f"{Fore.RED}Введите число от 1 до 10{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Введите корректное число{Style.RESET_ALL}")
        
        # Logging
        self.config['LOG_LEVEL'] = 'INFO'
        self.config['LOG_FILE'] = 'spotify_downloader.log'
        
        # Advanced settings
        self.config['RETRY_ATTEMPTS'] = '3'
        self.config['REQUEST_TIMEOUT'] = '300'
        self.config['ENABLE_CACHE'] = 'true'
        self.config['CACHE_TTL'] = '3600'
        
        print(f"{Fore.GREEN}✓ Параметры загрузки настроены{Style.RESET_ALL}")
    
    def _save_configuration(self) -> bool:
        """Save configuration to .env file."""
        print(f"\n{Fore.CYAN}[Шаг 5/6] Сохранение конфигурации...{Style.RESET_ALL}")
        
        # Check if .env already exists
        if self.env_file.exists():
            if not self._confirm(f"\nФайл .env уже существует. Перезаписать?"):
                print(f"{Fore.YELLOW}Конфигурация не сохранена.{Style.RESET_ALL}")
                return False
            
            # Backup existing .env
            backup_file = self.env_file.with_suffix('.env.backup')
            try:
                self.env_file.rename(backup_file)
                print(f"{Fore.GREEN}✓ Создана резервная копия: {backup_file.name}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Предупреждение: не удалось создать резервную копию: {e}{Style.RESET_ALL}")
        
        # Write .env file
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# Spotify Playlist Downloader Configuration\n")
                f.write("# Generated by Setup Wizard\n\n")
                
                f.write("# Spotify API Credentials\n")
                f.write(f"SPOTIPY_CLIENT_ID={self.config['SPOTIPY_CLIENT_ID']}\n")
                f.write(f"SPOTIPY_CLIENT_SECRET={self.config['SPOTIPY_CLIENT_SECRET']}\n")
                f.write(f"SPOTIPY_REDIRECT_URI={self.config['SPOTIPY_REDIRECT_URI']}\n\n")
                
                f.write("# Download Settings\n")
                f.write(f"DEFAULT_OUTPUT_DIR={self.config['DEFAULT_OUTPUT_DIR']}\n")
                f.write(f"DEFAULT_AUDIO_FORMAT={self.config['DEFAULT_AUDIO_FORMAT']}\n")
                f.write(f"DEFAULT_AUDIO_QUALITY={self.config['DEFAULT_AUDIO_QUALITY']}\n")
                f.write(f"MAX_CONCURRENT_DOWNLOADS={self.config['MAX_CONCURRENT_DOWNLOADS']}\n\n")
                
                f.write("# Logging\n")
                f.write(f"LOG_LEVEL={self.config['LOG_LEVEL']}\n")
                f.write(f"LOG_FILE={self.config['LOG_FILE']}\n\n")
                
                f.write("# Advanced Settings\n")
                f.write(f"RETRY_ATTEMPTS={self.config['RETRY_ATTEMPTS']}\n")
                f.write(f"REQUEST_TIMEOUT={self.config['REQUEST_TIMEOUT']}\n")
                f.write(f"ENABLE_CACHE={self.config['ENABLE_CACHE']}\n")
                f.write(f"CACHE_TTL={self.config['CACHE_TTL']}\n")
            
            print(f"{Fore.GREEN}✓ Конфигурация сохранена в .env{Style.RESET_ALL}")
            return True
        
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка сохранения конфигурации: {e}{Style.RESET_ALL}")
            return False
    
    def _test_spotify_connection(self) -> None:
        """Test Spotify API connection."""
        print(f"\n{Fore.CYAN}[Шаг 6/6] Проверка подключения к Spotify API...{Style.RESET_ALL}")
        
        try:
            # Import here to avoid circular dependencies
            from src.features.spotify.infrastructure.spotify_client import SpotifyClient
            
            client = SpotifyClient(
                self.config['SPOTIPY_CLIENT_ID'],
                self.config['SPOTIPY_CLIENT_SECRET']
            )
            
            if client.authenticate():
                print(f"{Fore.GREEN}✓ Подключение к Spotify API успешно!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Не удалось подключиться к Spotify API{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Проверьте ваши credentials и попробуйте снова.{Style.RESET_ALL}")
        
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка проверки подключения: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Вы можете проверить подключение позже командой: python main.py --check{Style.RESET_ALL}")
    
    def _print_success(self) -> None:
        """Print success message."""
        print(f"\n{Fore.GREEN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}✓ Настройка завершена успешно!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}Что дальше?{Style.RESET_ALL}\n")
        print(f"{Fore.WHITE}1. Создайте файл playlists.txt со ссылками на плейлисты{Style.RESET_ALL}")
        print(f"   Пример: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M\n")
        
        print(f"{Fore.WHITE}2. Запустите загрузку:{Style.RESET_ALL}")
        print(f"   python main.py --playlists playlists.txt\n")
        
        print(f"{Fore.WHITE}3. Или загрузите один плейлист:{Style.RESET_ALL}")
        print(f"   python main.py --playlist <URL>\n")
        
        print(f"{Fore.CYAN}Полезные команды:{Style.RESET_ALL}")
        print(f"  python main.py --help     - Справка по всем командам")
        print(f"  python main.py --check    - Проверить конфигурацию")
        print(f"  python main.py --setup    - Запустить мастер настройки снова\n")
        
        print(f"{Fore.GREEN}Удачных загрузок! ♪{Style.RESET_ALL}\n")
    
    def _input_text(self, prompt: str, default: str = "") -> str:
        """
        Get text input from user.
        
        Args:
            prompt: Input prompt
            default: Default value
            
        Returns:
            User input or default
        """
        if default:
            prompt_text = f"{Fore.WHITE}{prompt} [{Fore.CYAN}{default}{Fore.WHITE}]: {Style.RESET_ALL}"
        else:
            prompt_text = f"{Fore.WHITE}{prompt}: {Style.RESET_ALL}"
        
        value = input(prompt_text).strip()
        return value if value else default
    
    def _input_choice(self, prompt: str, choices: list, default: str = "") -> str:
        """
        Get choice input from user.
        
        Args:
            prompt: Input prompt
            choices: List of valid choices
            default: Default choice
            
        Returns:
            User choice
        """
        while True:
            value = self._input_text(prompt, default)
            if value in choices:
                return value
            print(f"{Fore.RED}Неверный выбор. Выберите из: {', '.join(choices)}{Style.RESET_ALL}")
    
    def _confirm(self, prompt: str) -> bool:
        """
        Get yes/no confirmation from user.
        
        Args:
            prompt: Confirmation prompt
            
        Returns:
            True if user confirmed
        """
        response = self._input_text(f"{prompt} (y/n)", "y").lower()
        return response in ['y', 'yes', 'д', 'да']


def main():
    """Main entry point for setup wizard."""
    wizard = SetupWizard()
    success = wizard.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


# Made with Bob