#!/usr/bin/env python3
"""
Automatic dependency installation script for Spotify Playlist Downloader.
Checks and installs all required dependencies.
"""

import sys
import subprocess
import platform
import os
from pathlib import Path
from typing import Tuple

# Color codes for terminal output
if platform.system() == "Windows":
    # Enable ANSI colors on Windows
    os.system("")

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}{text}{RESET}")
    print(f"{CYAN}{BOLD}{'='*60}{RESET}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{CYAN}ℹ {text}{RESET}")


def check_python_version() -> bool:
    """
    Check if Python version is compatible.
    
    Returns:
        True if version is compatible
    """
    print_header("Проверка версии Python")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    print(f"Текущая версия: Python {version_str}")
    
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version_str} совместим")
        return True
    else:
        print_error(f"Python {version_str} не поддерживается")
        print_warning("Требуется Python 3.8 или выше")
        print_info("Скачайте Python с https://www.python.org/downloads/")
        return False


def check_pip() -> bool:
    """
    Check if pip is installed.
    
    Returns:
        True if pip is available
    """
    print_header("Проверка pip")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print_success(f"pip установлен: {result.stdout.strip()}")
            return True
        else:
            print_error("pip не найден")
            return False
    except Exception as e:
        print_error(f"Ошибка проверки pip: {e}")
        return False


def install_requirements() -> bool:
    """
    Install Python dependencies from requirements.txt.
    
    Returns:
        True if installation successful
    """
    print_header("Установка Python зависимостей")
    
    root_dir = Path(__file__).parent.parent
    requirements_file = root_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print_error(f"Файл requirements.txt не найден: {requirements_file}")
        return False
    
    print_info(f"Установка зависимостей из {requirements_file.name}...")
    print_warning("Это может занять несколько минут...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print_success("Все зависимости успешно установлены")
            
            # Show installed packages
            if result.stdout:
                print(f"\n{CYAN}Установленные пакеты:{RESET}")
                for line in result.stdout.split('\n'):
                    if 'Successfully installed' in line or 'Requirement already satisfied' in line:
                        print(f"  {line}")
            
            return True
        else:
            print_error("Ошибка установки зависимостей")
            if result.stderr:
                print(f"\n{RED}Ошибка:{RESET}\n{result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        print_error("Превышено время ожидания установки")
        return False
    except Exception as e:
        print_error(f"Ошибка: {e}")
        return False


def check_ffmpeg() -> Tuple[bool, str]:
    """
    Check if FFmpeg is installed.
    
    Returns:
        Tuple of (is_installed, version_info)
    """
    print_header("Проверка FFmpeg")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print_success(f"FFmpeg установлен: {version_line}")
            return True, version_line
        else:
            return False, ""
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        print_warning("FFmpeg не найден")
        return False, ""


def provide_ffmpeg_instructions() -> None:
    """Provide FFmpeg installation instructions based on OS."""
    system = platform.system()
    
    print(f"\n{CYAN}Инструкции по установке FFmpeg:{RESET}\n")
    
    if system == "Windows":
        print(f"{BOLD}Вариант 1: Chocolatey (рекомендуется){RESET}")
        print("  1. Установите Chocolatey: https://chocolatey.org/install")
        print("  2. Откройте PowerShell от имени администратора")
        print("  3. Выполните: choco install ffmpeg")
        print()
        print(f"{BOLD}Вариант 2: Вручную{RESET}")
        print("  1. Скачайте FFmpeg: https://ffmpeg.org/download.html")
        print("  2. Распакуйте архив")
        print("  3. Добавьте путь к ffmpeg.exe в PATH")
        print("  4. Перезапустите терминал")
    
    elif system == "Linux":
        print(f"{BOLD}Ubuntu/Debian:{RESET}")
        print("  sudo apt-get update && sudo apt-get install ffmpeg")
        print()
        print(f"{BOLD}CentOS/RHEL:{RESET}")
        print("  sudo yum install ffmpeg")
        print()
        print(f"{BOLD}Arch Linux:{RESET}")
        print("  sudo pacman -S ffmpeg")
    
    elif system == "Darwin":  # macOS
        print(f"{BOLD}Homebrew:{RESET}")
        print("  brew install ffmpeg")
        print()
        print(f"{BOLD}MacPorts:{RESET}")
        print("  sudo port install ffmpeg")
    
    print(f"\n{YELLOW}После установки FFmpeg запустите этот скрипт снова.{RESET}")


def create_env_file() -> bool:
    """
    Create .env file from .env.example if it doesn't exist.
    
    Returns:
        True if .env file exists or was created
    """
    print_header("Проверка файла конфигурации")
    
    root_dir = Path(__file__).parent.parent
    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"
    
    if env_file.exists():
        print_success("Файл .env уже существует")
        return True
    
    if not env_example.exists():
        print_error("Файл .env.example не найден")
        return False
    
    try:
        # Copy .env.example to .env
        with open(env_example, 'r', encoding='utf-8') as src:
            content = src.read()
        
        with open(env_file, 'w', encoding='utf-8') as dst:
            dst.write(content)
        
        print_success("Создан файл .env из .env.example")
        print_warning("Необходимо настроить Spotify API credentials в .env")
        print_info("Запустите: python main.py --setup")
        return True
    
    except Exception as e:
        print_error(f"Ошибка создания .env файла: {e}")
        return False


def check_yt_dlp() -> bool:
    """
    Check if yt-dlp is up to date.
    
    Returns:
        True if yt-dlp is installed
    """
    print_header("Проверка yt-dlp")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Extract version
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':')[1].strip()
                    print_success(f"yt-dlp установлен: версия {version}")
                    break
            
            print_info("Рекомендуется регулярно обновлять yt-dlp")
            print_info("Команда обновления: python main.py --update")
            return True
        else:
            print_warning("yt-dlp не найден (будет установлен из requirements.txt)")
            return False
    
    except Exception as e:
        print_warning(f"Не удалось проверить yt-dlp: {e}")
        return False


def print_summary(success: bool) -> None:
    """Print installation summary."""
    print_header("Итоги установки")
    
    if success:
        print(f"{GREEN}{BOLD}✓ Установка завершена успешно!{RESET}\n")
        
        print(f"{CYAN}Следующие шаги:{RESET}\n")
        print("1. Настройте приложение:")
        print(f"   {BOLD}python main.py --setup{RESET}")
        print()
        print("2. Или вручную отредактируйте .env файл:")
        print("   - Добавьте Spotify API credentials")
        print("   - Настройте параметры загрузки")
        print()
        print("3. Начните загрузку:")
        print(f"   {BOLD}python main.py --playlist <URL>{RESET}")
        print(f"   {BOLD}python main.py --playlists playlists.txt{RESET}")
        print()
        print(f"{GREEN}Готово к использованию! ♪{RESET}\n")
    else:
        print(f"{RED}{BOLD}✗ Установка завершена с ошибками{RESET}\n")
        print(f"{YELLOW}Исправьте ошибки выше и запустите скрипт снова.{RESET}\n")


def main() -> int:
    """
    Main installation function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"""
{CYAN}{BOLD}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   Spotify Playlist Downloader - Установка зависимостей   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{RESET}
""")
    
    all_success = True
    
    # Step 1: Check Python version
    if not check_python_version():
        return 1
    
    # Step 2: Check pip
    if not check_pip():
        print_error("pip необходим для установки зависимостей")
        return 1
    
    # Step 3: Install Python dependencies
    if not install_requirements():
        all_success = False
    
    # Step 4: Check FFmpeg
    ffmpeg_installed, _ = check_ffmpeg()
    if not ffmpeg_installed:
        provide_ffmpeg_instructions()
        all_success = False
    
    # Step 5: Check yt-dlp (informational)
    check_yt_dlp()
    
    # Step 6: Create .env file
    if not create_env_file():
        all_success = False
    
    # Print summary
    print_summary(all_success)
    
    return 0 if all_success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Установка прервана пользователем{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Критическая ошибка: {e}{RESET}")
        sys.exit(1)

# Made with Bob
