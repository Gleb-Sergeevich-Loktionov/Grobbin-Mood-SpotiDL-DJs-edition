# 🎵 Spotify Playlist Downloader

Скачивайте ваши любимые плейлисты из Spotify в высоком качестве с полными метаданными и обложками альбомов.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 💡 Как это работает?

1. **Настройте Spotify API** - получите бесплатные ключи на developer.spotify.com
2. **Добавьте ссылки** - вставьте ссылки на плейлисты в файл `playlists.txt`
3. **Запустите** - выполните `python main.py` и всё!

Программа автоматически:
- 🔍 Найдёт все треки из ваших плейлистов
- 🎵 Скачает их в высоком качестве (MP3 320kbps / FLAC)
- 🎨 Добавит обложки альбомов и метаданные
- 📁 Организует по папкам с названиями плейлистов

**Никаких сложных настроек - просто вставьте ссылки и запустите!**

## ✨ Features

- 🎯 **Spotify Integration** - Direct playlist access via Spotify Web API
- 🎵 **High-Quality Audio** - Download in MP3 (320kbps), M4A (256kbps), or FLAC (lossless)
- 🎨 **Complete Metadata** - Embedded ID3v2 tags with title, artist, album, year, and more
- 🖼️ **Album Artwork** - High-resolution cover art (up to 1000x1000px)
- 📁 **Smart Organization** - Automatic directory creation by playlist name
- ⚡ **Concurrent Downloads** - Multi-threaded downloading (3-5 simultaneous)
- 🔄 **Resume Support** - Continue interrupted downloads
- 📊 **Real-time Progress** - Beautiful progress bars with speed and ETA
- 🛡️ **Error Handling** - Robust retry logic and graceful failure recovery
- 🎛️ **Configurable** - Extensive configuration via YAML and environment variables

## 📋 Requirements

- Python 3.8 or higher
- FFmpeg (for audio conversion)
- Spotify Developer Account (for API credentials)

## 🚀 Quick Start (3 простых шага!)

### Шаг 1: Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/yourusername/spotify-playlist-downloader.git
cd spotify-playlist-downloader

# Установите зависимости
pip install -r requirements.txt

# Установите FFmpeg (если ещё не установлен)
# Windows (через Chocolatey):
choco install ffmpeg

# macOS (через Homebrew):
brew install ffmpeg

# Linux (Ubuntu/Debian):
sudo apt-get install ffmpeg
```

### Шаг 2: Настройка Spotify API

1. Перейдите на [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Войдите с вашим Spotify аккаунтом
3. Нажмите "Create an App"
4. Заполните название и описание приложения
5. Скопируйте **Client ID** и **Client Secret**
6. Создайте файл `.env` и добавьте ваши ключи:

```bash
# Скопируйте пример
cp .env.example .env

# Откройте .env и вставьте ваши ключи:
SPOTIPY_CLIENT_ID=ваш_client_id
SPOTIPY_CLIENT_SECRET=ваш_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

### Шаг 3: Добавьте плейлисты и запустите!

1. Откройте файл `playlists.txt`
2. Добавьте ссылки на ваши плейлисты (по одной на строку):

```text
https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS
https://open.spotify.com/playlist/1qDQSeWk8pqxIX9VMJiPDy
```

3. Запустите программу:

```bash
python main.py
```

**Вот и всё!** 🎉 Программа скачает все треки из ваших плейлистов в папку `downloads/`.

---

### Продвинутое использование (опционально)

Если нужны дополнительные настройки, используйте параметры командной строки:

```bash
# Скачать один плейлист
python main.py --playlist "https://open.spotify.com/playlist/..."

# Указать папку для сохранения
python main.py --output ~/Music/Spotify

# Выбрать формат и качество
python main.py --format flac --quality lossless

# Увеличить скорость (больше одновременных загрузок)
python main.py --concurrent 5
```

## 📖 Usage

### Basic Commands

```bash
# Simple: Download from playlists.txt file
python main.py

# Download from specific playlists file
python main.py --playlists playlists.txt

# Download single playlist
python main.py --playlist "https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS"

# Specify output directory
python main.py --playlists playlists.txt --output ~/Music/Spotify

# Choose audio format and quality
python main.py --playlist "..." --format mp3 --quality 320
python main.py --playlist "..." --format flac --quality lossless

# Concurrent downloads
python main.py --playlists playlists.txt --concurrent 5

# Resume interrupted download
python main.py --playlists playlists.txt --resume

# Skip existing files
python main.py --playlists playlists.txt --skip-existing

# Verbose output
python main.py --playlist "..." --verbose

# Quiet mode
python main.py --playlists playlists.txt --quiet
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--playlist URL` | Single Spotify playlist URL | - |
| `--playlists FILE` | File with playlist URLs (one per line) | - |
| `--output DIR` | Output directory | `./downloads` |
| `--format FORMAT` | Audio format: mp3, m4a, flac | `mp3` |
| `--quality QUALITY` | Audio quality (kbps or "lossless") | `320` |
| `--concurrent N` | Number of concurrent downloads | `3` |
| `--resume` | Resume interrupted downloads | `false` |
| `--skip-existing` | Skip already downloaded tracks | `false` |
| `--config FILE` | Custom config file path | - |
| `--env FILE` | Custom .env file path | - |
| `--verbose` | Enable verbose logging | `false` |
| `--quiet` | Minimal output | `false` |
| `--version` | Show version information | - |
| `--help` | Show help message | - |

### Playlist File Format

Create a `playlists.txt` file with one URL per line:

```text
# My Favorite Playlists
https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS
https://open.spotify.com/playlist/1qDQSeWk8pqxIX9VMJiPDy

# More playlists
https://open.spotify.com/playlist/0UGwu4ZdLZkt0Hv5ZpsheT
https://open.spotify.com/playlist/11dGHFHktXtU00aDUtJQig
```

Lines starting with `#` are treated as comments.

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Spotify API Credentials (Required)
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# Download Settings
DEFAULT_OUTPUT_DIR=./downloads
DEFAULT_AUDIO_FORMAT=mp3
DEFAULT_AUDIO_QUALITY=320
MAX_CONCURRENT_DOWNLOADS=3

# Logging
LOG_LEVEL=INFO
LOG_FILE=spotify_downloader.log
```

### YAML Configuration (config/default_config.yaml)

The application uses a comprehensive YAML configuration file. You can customize:

- Download settings (format, quality, concurrency)
- Metadata settings (artwork size, filename template)
- YouTube matching algorithm
- File organization
- Logging configuration
- Progress display
- Cache settings
- Rate limiting

See `config/default_config.yaml` for all available options.

## 📁 Output Structure

```
downloads/
├── Playlist Name 1/
│   ├── 01 - Artist - Track Name.mp3
│   ├── 02 - Artist - Track Name.mp3
│   ├── ...
│   └── Playlist Name 1.m3u
├── Playlist Name 2/
│   ├── 01 - Artist - Track Name.mp3
│   └── ...
└── .resume_state/
    ├── playlist_1_state.json
    └── playlist_2_state.json
```

## 🎯 Features in Detail

### Metadata Embedding

Each downloaded track includes:
- **Title** - Track name
- **Artist** - All artists (comma-separated)
- **Album** - Album name
- **Album Artist** - Primary album artist
- **Track Number** - Position in playlist
- **Year** - Release year
- **Genre** - Music genres (if available)
- **Album Artwork** - High-resolution cover art

### YouTube Matching Algorithm

The application uses an intelligent matching algorithm:

1. **Multiple Search Strategies** - Tries various query formats
2. **Duration Verification** - Matches track length (±10 seconds tolerance)
3. **Quality Scoring** - Prefers official audio, avoids live/covers
4. **View Count Analysis** - Higher views = more reliable
5. **Title Analysis** - Checks for artist and track name

### Resume Capability

Interrupted downloads can be resumed:
- State saved every 5 tracks
- Tracks already downloaded are skipped
- Failed tracks are logged for retry
- Resume with `--resume` flag

### Error Handling

- **Network Errors** - Automatic retry with exponential backoff (3 attempts)
- **API Rate Limits** - Automatic waiting and retry
- **Invalid Tracks** - Logged and skipped
- **Corrupted Downloads** - Validated and re-downloaded
- **Graceful Shutdown** - CTRL+C completes current downloads

## 🔧 Troubleshooting

### Common Issues

**1. "Failed to authenticate with Spotify API"**
- Check your Client ID and Client Secret in `.env`
- Ensure credentials are correct (no extra spaces)
- Verify your Spotify Developer app is active

**2. "No YouTube match found"**
- Some tracks may not be available on YouTube
- Check `failed_tracks.log` for details
- Try adjusting YouTube matching settings in config

**3. "FFmpeg not found"**
- Install FFmpeg: `choco install ffmpeg` (Windows) or `brew install ffmpeg` (macOS)
- Ensure FFmpeg is in your system PATH

**4. "Permission denied" errors**
- Check write permissions for output directory
- Run with appropriate permissions
- Try a different output directory

**5. Downloads are slow**
- Increase concurrent downloads: `--concurrent 5`
- Check your internet connection
- Some videos may have slower download speeds

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python main.py --playlists playlists.txt --verbose
```

Check log files:
- `spotify_downloader.log` - Main application log
- `failed_tracks.log` - Failed track details

## 📊 Performance

- **Download Speed** - Typically 1-5 MB/s per track
- **Memory Usage** - ~200-500 MB for 100 tracks
- **CPU Usage** - ~30-50% average (depends on concurrent downloads)
- **Success Rate** - ~90-95% for popular tracks

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for personal use only. Please respect copyright laws and Spotify's Terms of Service. Only download music you have the right to access. The developers are not responsible for any misuse of this software.

## 🙏 Acknowledgments

This project incorporates best practices from:
- [SpotiFlyer](https://github.com/Shabinder/SpotiFlyer) - UI/UX patterns
- [spotify-downloader (spotDL)](https://github.com/spotDL/spotify-downloader) - Spotify API integration
- [spotify-dl](https://github.com/SwapnilSoni1999/spotify-dl) - Metadata handling
- [musicdl](https://github.com/CharlesPikachu/musicdl) - Multi-source strategies

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

## 🗺️ Roadmap

Future enhancements:
- [ ] GUI interface
- [ ] Lyrics integration
- [ ] Playlist synchronization
- [ ] Multiple audio sources (SoundCloud, etc.)
- [ ] Batch playlist management
- [ ] Docker support
- [ ] Web interface

---

**Made with ❤️ for music lovers**