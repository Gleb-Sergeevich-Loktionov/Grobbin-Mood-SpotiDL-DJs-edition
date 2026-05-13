# Grobbin Mood SpotiDL DJ's edition

CLI-приложение для скачивания Spotify-плейлистов.

## Что важно знать сразу

- Запуск без аргументов не начинает скачивание. Нужно явно указать `--playlist` или `--playlists`.
- В текущей сборке мастер настройки сохраняет выбранную папку в `.env`, но реальная загрузка всё равно идёт в `.\downloads` внутри проекта.
- `python main.py --check` сейчас может показывать ошибку конфигурации, даже если скачивание работает. Причина: команда проверки читает другой конфиг и не подхватывает Spotify-ключи из `.env` так же, как основной запуск.
- Итоговый общий summary после нескольких плейлистов может быть неверным (`0/1`, `0 tracks`). Смотри на summary каждого плейлиста и файл `failed_tracks.log`.
- Не публикуй `.env` и не вставляй реальные Spotify Client Secret в чаты, скриншоты или README. Если секрет уже был показан публично, создай новый Client Secret в Spotify Dashboard.

## Требования

- Windows PowerShell 7 или обычный PowerShell.
- Python 3.8+.
- FFmpeg в `PATH`.
- Spotify Developer app с `Client ID` и `Client Secret`.
- Интернет-доступ к Spotify, YouTube и `googlevideo.com`.

Проверить Python и FFmpeg:

```powershell
python --version
ffmpeg -version
```

## Установка

Перейди в папку проекта:

```powershell
cd C:\Users\Глеб\Music\Spotifydown\app
```

Установи зависимости:

```powershell
python -m pip install -r requirements.txt
```

Если `yt-dlp` начинает сбоить или YouTube меняет формат ответов, обнови его:

```powershell
python main.py --update
```

## Первичная настройка

Запусти мастер настройки:

```powershell
python main.py --setup
```

Мастер проверит:

1. Версию Python.
2. Наличие FFmpeg.
3. Spotify API credentials.
4. Формат, качество и количество параллельных загрузок.
5. Сохранение `.env`.
6. Подключение к Spotify API.

Spotify credentials получить здесь:

```text
https://developer.spotify.com/dashboard
```

В Spotify Dashboard:

1. Войди в аккаунт Spotify.
2. Нажми `Create app`.
3. Заполни имя и описание.
4. Скопируй `Client ID`.
5. Скопируй `Client Secret`.
6. Вставь их в setup wizard.

После настройки появится файл `.env`. Он уже добавлен в `.gitignore`; не коммить его.

## Файл playlists.txt

Для нескольких плейлистов используй `playlists.txt` в корне проекта.

Пример:

```text
https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS
https://open.spotify.com/playlist/1qDQSeWk8pqxIX9VMJiPDy
https://open.spotify.com/playlist/0UGwu4ZdLZkt0Hv5ZpsheT
https://open.spotify.com/playlist/11dGHFHktXtU00aDUtJQig
```

Можно добавлять комментарии через `#`:

```text
# Morning
https://open.spotify.com/playlist/...

# Night
https://open.spotify.com/playlist/...
```

## Как запускать

Скачать все ссылки из `playlists.txt`:

```powershell
python main.py --playlists playlists.txt
```

Скачать один плейлист:

```powershell
python main.py --playlist "https://open.spotify.com/playlist/..."
```

Повторить после обрыва или сетевых ошибок:

```powershell
python main.py --playlists playlists.txt
```

В текущей сборке уже включён пропуск существующих файлов через внутренний конфиг. Флаги `--resume`, `--skip-existing`, `--concurrent`, `--format`, `--quality` есть в `--help`, но фактически не применяются из-за незавершённой обработки CLI overrides.

Посмотреть справку:

```powershell
python main.py --help
```

## Где искать скачанные файлы

В текущей версии файлы появляются здесь:

```text
C:\Users\Глеб\Music\Spotifydown\app\downloads
```

Структура:

```text
downloads\
  Morning\
    01 - Artist - Track.mp3
    02 - Artist - Track.mp3
  Lunch\
    01 - Artist - Track.mp3
  Evening\
  Night\
```

Важно: во время setup можно выбрать, например:

```text
C:\Users\Глеб\Music\Playlists
```

Но текущий DI-контейнер приложения жёстко использует `downloads`, поэтому выбранный путь пока не влияет на реальную загрузку. Это известная ошибка текущей сборки, а не ошибка пользователя.

## Проверка настройки

Команда существует:

```powershell
python main.py --check
```

Но сейчас она может вывести:

```text
Ошибка загрузки конфигурации: SpotifyConfig.__init__() missing 2 required positional arguments: 'client_id' and 'client_secret'
```

Это известная ошибка проверки: `.env` создан правильно, но `--check` сначала читает `config/default_config.yaml`, где нет секции `spotify`. Если `--setup` успешно проверил Spotify API и `--playlists` начинает загрузку, настройка фактически рабочая.

## Как понимать вывод

Нормальный успешный старт выглядит так:

```text
Found 4 playlist(s) to download
Successfully authenticated with Spotify API
Processing playlist 1/4: ...
Playlist completed: Morning.
Downloaded: 33/33
```

Предупреждения, которые не всегда означают полный провал:

- `Low confidence match` - найден трек с низкой уверенностью, результат стоит проверить на слух.
- `No acceptable match found` - приложение пробует другие варианты запроса.
- `Failed to download artwork` - не скачалась обложка, сам трек может быть скачан.
- `Connection timed out` / `googlevideo.com timed out` - сетевой сбой YouTube/CDN; обычно помогает повторный запуск с `--resume --skip-existing`.
- `Failed: N` в summary плейлиста - часть треков не скачалась, смотри `failed_tracks.log`.

## Известные ошибки текущей версии

1. `python main.py` без аргументов завершится ошибкой:

```text
Ошибка: Требуется --playlist или --playlists
```

Правильный запуск:

```powershell
python main.py --playlists playlists.txt
```

2. Выбранная в setup папка загрузки сохраняется в `.env`, но игнорируется при скачивании. Фактический путь: `.\downloads`.

3. `--output`, `--format`, `--quality`, `--concurrent`, `--resume` и `--skip-existing` объявлены в help, но сейчас не применяются как CLI overrides, потому что `apply_cli_overrides()` пустой, а зависимости создаются до обработки аргументов. Фактические значения текущей сборки: `downloads`, `mp3`, `320`, `3`.

4. `--check` может показывать ошибку `SpotifyConfig.__init__()...`, хотя основной запуск работает.

5. Финальный общий summary после batch-загрузки может показывать неверные totals. Доверяй per-playlist блокам:

```text
Playlist completed: Lunch.
Downloaded: 34/35
Failed: 1
```

6. В консоли иногда ломается отображение Unicode-символов (`Nil?fer`, `?????`), особенно в прогресс-барах. Это проблема вывода в терминал, а не обязательно имени файла.

7. В обычном `INFO` выводе много строк `[DEBUG]`. Это шум логирования текущей версии.

## Что делать при неудачных треках

1. Дождись завершения текущего запуска.
2. Открой `failed_tracks.log`.
3. Повтори загрузку той же командой:

```powershell
python main.py --playlists playlists.txt
```

Если конкретный трек скачался не той версией, его нужно проверить вручную: приложение ищет совпадение на YouTube, а не скачивает аудио напрямую из Spotify.

## Безопасность

- `.env` должен оставаться локальным.
- Не добавляй `.env`, `.spotify_cache`, `.youtube_cache`, `downloads`, `*.log` в git.
- Если Client Secret был случайно опубликован или отправлен в чат, зайди в Spotify Developer Dashboard и пересоздай secret.

## GitHub

Репозиторий:

```text
https://github.com/Gleb-Sergeevich-Loktionov/Grobbin-Mood-SpotiDL-DJs-edition
```

Текущая ветка:

```text
main
```

## Короткий рабочий сценарий

```powershell
cd C:\Users\Глеб\Music\Spotifydown\app
python -m pip install -r requirements.txt
python main.py --setup
notepad playlists.txt
python main.py --playlists playlists.txt
```

Повтор после обрывов:

```powershell
python main.py --playlists playlists.txt
```
