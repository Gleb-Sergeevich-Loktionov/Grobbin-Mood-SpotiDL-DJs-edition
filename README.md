<div align="center">

# 🎧 Grobbin Mood SpotiDL — DJ's Edition

### Download Spotify playlists to MP3 with **correct-track** matching that actually downloads the song you named — not a remix, not a live cut, not a cover.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-success.svg)](LICENSE)
[![yt-dlp](https://img.shields.io/badge/uses-yt--dlp-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![spotipy](https://img.shields.io/badge/uses-spotipy-1DB954.svg)](https://spotipy.readthedocs.io/)

**Original never substitutes for remix. Remix never substitutes for original. Live, acoustic, cover, and alternate edits are rejected by a hard version-equality gate.**

</div>

---

A Python CLI that reads a Spotify playlist, finds each track on YouTube, downloads the audio, and embeds full ID3 metadata + album art. The headline feature is a rigorous matching engine: if a playlist says `Officer John - Stay`, you get exactly `Stay` — never `Stay (Morgan Buckley Remix)`. And symmetrically, if the playlist *is* the remix, you get the remix — never the original.

> Built for **DJs, music collectors, and anyone who's been burned by "Spotify downloaders" that grab the wrong version of half the tracks.**

---

## Table of contents

- [Why this one](#why-this-one)
- [Features](#features)
- [The problem it solves](#the-problem-it-solves)
- [Requirements](#requirements)
- [Installation — complete, from scratch](#installation--complete-from-scratch)
  - [Step 1 — Install Python 3.8+](#step-1--install-python-38)
  - [Step 2 — Install FFmpeg](#step-2--install-ffmpeg)
  - [Step 3 — Get the project](#step-3--get-the-project)
  - [Step 4 — (Recommended) Create a virtual environment](#step-4--recommended-create-a-virtual-environment)
  - [Step 5 — Install Python dependencies](#step-5--install-python-dependencies)
- [Getting your Spotify API credentials](#getting-your-spotify-api-credentials)
  - [Create the Spotify app](#create-the-spotify-app)
  - [Copy Client ID and Client Secret](#copy-client-id-and-client-secret)
  - [Set the Redirect URI](#set-the-redirect-uri)
- [First-time setup](#first-time-setup)
- [Verify your installation](#verify-your-installation)
- [Usage](#usage)
- [Where files land](#where-files-land)
- [Understanding the output](#understanding-the-output)
- [How matching works (in detail)](#how-matching-works-in-detail)
- [FAQ / troubleshooting](#faq--troubleshooting)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Why this one

Most Spotify-to-MP3 tools search YouTube and take the first hit. That produces a predictable mess: the original is replaced by a random remix, a live recording sneaks in where the studio cut should be, an acoustic cover overwrites the real track, and niche/underground tracks simply fail because the search query was malformed. This project exists to fix exactly that.

The matcher runs **three hard gates** on every YouTube candidate before it is accepted, and **skips** (rather than downloads the wrong thing) when nothing qualifies:

1. **Duration gate** — the candidate's length must be within a few seconds of the Spotify track. A different song is almost always a different length.
2. **Title/artist relevance gate** — the video title must actually reference the track, and the artist must appear in the title or channel (with a fallback for label/"Topic" auto-uploads). Whole-word, ASCII-transliterated matching so Cyrillic/Greek/etc. names match their Latin-transliterated YouTube titles.
3. **Version-equality gate** — the *version* of the candidate must equal the version of the Spotify track. `Original` rejects `Remix`/`Live`/`Acoustic`/`Club Mix`/`Radio Edit`/…; a remix track rejects the plain original. `Original Mix` / `Album Version` are correctly recognized *as* the original, not as an alternate version.

On top of the gates, the search step **gathers candidates from every query variation and picks the single best match globally** — it never stops at the first query that returns anything, which is the bug that made niche tracks fail in simpler matchers.

A post-download duration check on the final audio file catches any wrong-track download that slipped past the search-time gate, so a mismatched file is discarded rather than kept.

---

## Features

- **Exact-track matching** — original vs. remix/live/acoustic/edit is enforced as a hard rule, both directions.
- **Full playlist support** — single playlist via URL or a `playlists.txt` with many (comments with `#` supported).
- **High-quality audio** — MP3 (default) / FLAC / M4A, up to 320 kbps, extracted via `yt-dlp` + FFmpeg.
- **Full metadata embedding** — artist, title, album, track number, release date, album art (via mutagen).
- **Resume / skip-existing** — re-run the same command after a network drop; finished tracks are skipped.
- **Per-track correctness logging** — every rejection (`duration`, `title unrelated`, `version mismatch`) is logged so you can see *why* a track was skipped instead of guessing.
- **Unicode-safe** — non-Latin artist/title names match their transliterated YouTube counterparts; file names are sanitized for Windows.
- **ISRC-aware** — falls back to ISRC lookup where available.
- **Configurable concurrency** — parallel downloads with an adaptive concurrency option.

---

## The problem it solves

If you have ever run a Spotify downloader and then listened through your folder only to find that:

- the radio edit replaced the full-length original (or vice versa),
- a bedroom DJ's remix replaced the official release,
- a "live at ..." bootleg replaced the studio master,
- an 8-bit / nightcore / "sped up" re-render overwrote the real song,
- half an underground playlist failed to download at all,

…then this is the tool for you. It prioritizes **correctness over recall**: when it cannot confidently identify the exact track and version, it skips and logs the track rather than downloading something wrong. You always know that what is in your `downloads/` folder is what the playlist said it should be.

---

## Requirements

| Requirement | Why | Notes |
|---|---|---|
| **Python 3.8+** | Runs the CLI | Tested on 3.14 |
| **FFmpeg** in `PATH` | Audio extraction / conversion | Required by `yt-dlp` |
| **Spotify Developer app** | Free `Client ID` + `Client Secret` | See [Getting your Spotify API credentials](#getting-your-spotify-api-credentials) |
| Internet access | Reaches Spotify, YouTube, `googlevideo.com` | — |

Quick environment check (run in PowerShell / your shell):

```powershell
python --version
ffmpeg -version
```

Both should print a version number. If either is missing, follow the install steps below.

---

## Installation — complete, from scratch

> Everything below is shown in **PowerShell** on Windows (the primary target). On Linux/macOS use the same Python commands; package installs use your package manager instead of `winget`.

### Step 1 — Install Python 3.8+

**Windows (winget):**

```powershell
winget install Python.Python.3.12
```

**Windows (manual):** download the installer from <https://www.python.org/downloads/>, run it, and **check "Add python.exe to PATH"** in the installer before clicking *Install*.

**macOS (Homebrew):**

```bash
brew install python@3.12
```

**Linux (Debian/Ubuntu):**

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
```

Verify:

```powershell
python --version
# Python 3.12.x  (or higher)
```

> If `python` is not recognized on Windows but `py` is, use `py` in place of `python` throughout this guide (e.g. `py -m pip install -r requirements.txt`).

### Step 2 — Install FFmpeg

FFmpeg does the actual audio extraction/conversion. `yt-dlp` needs it.

**Windows (winget) — easiest:**

```powershell
winget install Gyan.FFmpeg
```

**Windows (manual):**

1. Download a build from <https://www.gyan.dev/ffmpeg/builds/> → `ffmpeg-release-full.7z`.
2. Extract it somewhere permanent, e.g. `C:\ffmpeg`.
3. Add `C:\ffmpeg\bin` to your **PATH**:
   - Win + R → `sysdm.cpl` → *Advanced* → *Environment Variables*.
   - Under *User variables*, edit `Path` → *New* → paste `C:\ffmpeg\bin` → OK.
4. **Open a new terminal** (PATH changes don't apply to already-open terminals).

**macOS:**

```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**

```bash
sudo apt install -y ffmpeg
```

Verify (in a **new** terminal):

```powershell
ffmpeg -version
# ffmpeg version 7.x ...
```

### Step 3 — Get the project

**From a release (recommended):** download and unzip the latest release from the [Releases page](https://github.com/Gleb-Sergeevich-Loktionov/Grobbin-Mood-SpotiDL-DJs-edition/releases).

**From git (for contributors):**

```powershell
git clone https://github.com/Gleb-Sergeevich-Loktionov/Grobbin-Mood-SpotiDL-DJs-edition.git
cd Grobbin-Mood-SpotiDL-DJs-edition
```

### Step 4 — (Recommended) Create a virtual environment

Keeps this project's dependencies isolated from your system Python.

**Windows:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, allow it once for this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

You should now see `(venv)` at the start of your prompt. **Re-activate it every time you open a new terminal** to run the tool.

> No virtual environment? That's fine too — just skip this step and install into your user/site packages. The commands below are identical.

### Step 5 — Install Python dependencies

From the project root (the folder containing `main.py`):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

What gets installed (and why):

| Package | Purpose |
|---|---|
| `spotipy` | Spotify Web API client (metadata, playlist tracks, ISRC) |
| `yt-dlp` | YouTube search + audio download |
| `mutagen` | ID3 metadata + album-art embedding |
| `Pillow` | Album-art image handling (≥11.3 needed for Python 3.13/3.14) |
| `Unidecode` | Transliterate Cyrillic/Greek/etc. for matching |
| `requests` | HTTP |
| `python-dotenv` | Loads `.env` |
| `PyYAML` | Config files |
| `tqdm` / `colorama` | Progress bars + colored output |
| `tenacity` / `ratelimit` | Retry + rate limiting |
| `dependency-injector` | DI container |

For development (tests, linting), optionally also:

```powershell
python -m pip install -r requirements-dev.txt
```

> **If `yt-dlp` ever starts failing** (YouTube changes its response format periodically), update just that package:
>
> ```powershell
> python main.py --update
> ```
>
> …or manually: `python -m pip install -U yt-dlp`.

At this point Python, FFmpeg, and all dependencies are ready. The only thing left is your **Spotify API key**.

---

## Getting your Spotify API credentials

This is free and takes ~3 minutes. You only do it once. You need **any** Spotify account (free or Premium — the API key is independent of your subscription).

> 💡 The Spotify API provides **metadata only** (track name, artist, duration, ISRC, album art). Audio comes from YouTube. The API key lets the tool read your playlists' track lists.

### Create the Spotify app

1. Go to the **Spotify Developer Dashboard**: <https://developer.spotify.com/dashboard>
2. Log in with your Spotify account. (First visit may ask you to accept the developer terms — accept them.)
3. Click **Create app**.
4. Fill in the form:
   - **App name:** anything, e.g. `Grobbin Downloader`
   - **App description:** anything, e.g. `personal playlist backup`
   - **Website:** leave blank (optional)
   - **Redirect URI:** enter exactly `http://localhost:8888/callback` (then click **Add**). See [Set the Redirect URI](#set-the-redirect-uri) if you prefer a different one.
   - **Which API/SDKs are you planning to use?** — check *Web API* (the rest don't matter).
5. Accept the terms and click **Save**.

### Copy Client ID and Client Secret

1. On the dashboard, open the app you just created.
2. Click **Settings** (top right).
3. You'll see:
   - **Client ID** — copy it.
   - **Client secret** — click **View client secret**, then copy it.
4. Keep both values handy for the setup wizard.

> ⚠️ **Treat the Client Secret like a password.** Never paste it into chats, screenshots, issues, or commit it to git. If it ever leaks, regenerate it in this same Settings page.

### Set the Redirect URI

The Redirect URI is where Spotify sends you back after the one-time browser login. It must **exactly match** what's in your `.env`.

- In the dashboard **Settings → Redirect URIs**, add one URI. The default the tool expects is:
  ```
  http://localhost:8888/callback
  ```
- If you already used a different one (e.g. `http://127.0.0.1:9900/`), that's fine — just enter the **same** value when the setup wizard asks, or set it directly in `.env` as `SPOTIPY_REDIRECT_URI`.
- The URI does **not** need to be a real running server for the client-credentials/playlist flow used here; it just has to match between Spotify and your `.env`.

---

## First-time setup

Once you have your Client ID, Client Secret, and Redirect URI, run the built-in wizard from the project root:

```powershell
python main.py --setup
```

The wizard will:

1. ✅ Check your **Python version**.
2. ✅ Check that **FFmpeg** is installed and on `PATH`.
3. ✏️ Ask for your **Spotify Client ID** and **Client Secret**.
4. ✏️ Ask for the **Redirect URI** (defaults to `http://localhost:8888/callback`).
5. ✏️ Let you pick **audio format** (`mp3` / `flac` / `m4a`), **quality** (e.g. `320`), and **concurrent downloads** (e.g. `3`).
6. 💾 Write everything to a local **`.env`** file.
7. 🔌 Test the **Spotify API connection** (this opens your browser once for the one-time login; after you approve, paste the URL you're redirected to back into the wizard if prompted).

When you see `Successfully authenticated with Spotify API`, setup is complete.

### The `.env` file (reference)

The wizard creates `.env` for you. If you'd rather create/edit it by hand, use `.env.example` as a template:

```env
# Spotify API Credentials
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# Download Settings
DEFAULT_OUTPUT_DIR=./downloads
DEFAULT_AUDIO_FORMAT=mp3
DEFAULT_AUDIO_QUALITY=320
MAX_CONCURRENT_DOWNLOADS=3

# Logging
LOG_LEVEL=INFO
LOG_FILE=spotify_downloader.log

# Advanced (optional)
RETRY_ATTEMPTS=3
REQUEST_TIMEOUT=300
ENABLE_CACHE=true
CACHE_TTL=3600
```

`.env` is already in `.gitignore` — it will never be committed. Don't share it.

---

## Verify your installation

```powershell
python main.py --check
```

You should see green checkmarks for Python, FFmpeg, and your Spotify credentials. If `--check` reports a config issue but `--setup` succeeded and downloads start (below), your setup is fine — `--check` reads a slightly different config path in some edge cases and is known to over-report.

A real end-to-end smoke test — download one playlist:

```powershell
python main.py --playlist "https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS"
```

Expected: `Successfully authenticated with Spotify API`, then per-track progress, then `Playlist completed: …` and a `downloads/<PlaylistName>/` folder full of `.mp3` files.

---

## Usage

Download every link in `playlists.txt`:

```powershell
python main.py --playlists playlists.txt
```

Download a single playlist:

```powershell
python main.py --playlist "https://open.spotify.com/playlist/..."
```

Example `playlists.txt` (comments with `#`):

```text
# Morning
https://open.spotify.com/playlist/7ooZ1OdYCD6wibrLAfrgXS

# Night
https://open.spotify.com/playlist/1qDQSeWk8pqxIX9VMJiPDy
```

Retry after a drop or network error — finished tracks are skipped automatically:

```powershell
python main.py --playlists playlists.txt
```

Optional per-run overrides:

```powershell
python main.py --playlists playlists.txt --format flac --quality lossless --concurrent 5
```

Show help:

```powershell
python main.py --help
```

---

## Where files land

By default, audio is written to `downloads/` inside the project, organized by playlist name:

```text
downloads/
  Morning/
    01 - Artist - Track.mp3
    02 - Artist - Track.mp3
  Night/
    01 - Artist - Track.mp3
```

---

## Understanding the output

A healthy run looks like:

```text
Found 4 playlist(s) to download
Successfully authenticated with Spotify API
Processing playlist 1/4: ...
Playlist completed: Morning.
Downloaded: 33/33
```

Warnings you may see (most are non-fatal):

- `Low confidence match` — a candidate was found with a weaker score; worth a quick listen.
- `No acceptable match found` / `No track-correct match` — the matcher is trying the next query variation.
- `Failed to download artwork` — the album art request failed; the audio itself may still be fine.
- `Connection timed out` / `googlevideo.com timed out` — a transient YouTube/CDN network error; re-run.
- `version mismatch` / `duration` / `title unrelated` — a YouTube result was rejected by a hard gate (this is the matcher protecting you from the wrong track).
- `Failed: N` in a playlist summary — some tracks did not download; see `failed_tracks.log`.

### When a track is skipped

A skipped track is **correct behavior**, not a bug. It means: *no YouTube result could be proven to be the exact track and version you asked for*. Re-running may help if the cause was a transient network error, but if the right upload genuinely isn't on YouTube (or is age-gated/region-locked without browser cookies), the track stays skipped. That is preferable to silently saving the wrong song.

---

## How matching works (in detail)

For each Spotify track the matcher:

1. Builds several search queries — the plain `artist title` first, then `artist - title`, quoted forms, a base-title fallback (without the parenthetical version), and `… official audio` last. The plain query is first because it is the most reliable for niche and auto-generated "Topic" uploads; `official audio` is pushed to the end because it often crowds those uploads out of the top results.
2. Runs each query via `yt-dlp` (`ytsearchN`, `extract_flat=False` so duration and view count are available) and **collects every candidate across all queries**, de-duplicated by video ID.
3. Passes each candidate through the three hard gates (duration → title/artist relevance → version equality).
4. Scores the survivors (duration closeness, official/audio presence, artist/title presence, view count, with penalties for live/cover/instrumental/alternate re-recordings) and picks the global best.
5. Downloads the best match, then re-verifies the downloaded audio's duration against the Spotify track as a final guard — a mismatched file is deleted, not kept.

If no candidate passes all gates across all queries, the track is skipped and recorded in `failed_tracks.log`.

### Version keywords the gate understands

Treated as **alternate versions** (rejected when the track is the original, required to match when the track is that version): `remix`, `radio edit`, `extended mix`, `extended`, `club mix`, `vip`, `bootleg`, `rework`, `edit`, `live`, `acoustic`, `unplugged`, `instrumental`, `karaoke`, `cover`, `reprise`, `demo`, `remaster`/`remastered`, `mono`, `nightcore`, `sped up`, `slowed`, `mix`, `version`.

Treated as **neutral** (do *not* count as a version difference): `feat`/`ft`/`featuring`, `official`, `audio`, `video`, `lyrics`, `hd`, `hq`, `4k`, `explicit`, `clean`, `mv`, and a bare year.

`Original Mix` / `Original Version` / `Album Version` are recognized as the **original recording**, not an alternate version.

---

## FAQ / troubleshooting

<details>
<summary><b>A track I know is on YouTube was skipped. Why?</b></summary>

Most often the available upload was the wrong version (the gate correctly rejected it), or the upload was unavailable/age-gated (`This video is not available` / `Sign in to confirm your age`). For age-gated videos, configure browser cookies in the YouTube section of your config so `yt-dlp` can authenticate. Rarely, the search queries didn't surface the right video; re-running or checking `failed_tracks.log` will tell you which gate rejected it.
</details>

<details>
<summary><b><code>python</code> is not recognized on Windows</b></summary>

Use the `py` launcher instead (`py -m pip install -r requirements.txt`), or reinstall Python from <https://www.python.org/downloads/> making sure to check **"Add python.exe to PATH"**. Then open a **new** terminal.
</details>

<details>
<summary><b><code>ffmpeg</code> is not recognized</b></summary>

FFmpeg isn't on your `PATH`. Easiest fix: `winget install Gyan.FFmpeg`, then open a new terminal. If you installed it manually, add its `bin` folder to your user `PATH` (see [Step 2](#step-2--install-ffmpeg)) and open a new terminal.
</details>

<details>
<summary><b>Spotify authentication fails / <code>Failed to authenticate with Spotify API</code></b></summary>

- Check that `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` in `.env` are correct (no trailing spaces, no quotes).
- Check that the **Redirect URI** in `.env` exactly matches the one added in the Spotify Dashboard app settings.
- Re-run `python main.py --setup` to re-enter credentials.
- A one-off `Read timed out` is a transient network error — just re-run the command.
</details>

<details>
<summary><b>yt-dlp errors / downloads suddenly stop working</b></summary>

YouTube periodically changes its response format. Update yt-dlp:

```powershell
python main.py --update
```

If that doesn't fix it, check <https://github.com/yt-dlp/yt-dlp/releases> for a newer release and `pip install -U yt-dlp`.
</details>

<details>
<summary><b>Can it download the wrong version on purpose?</b></summary>

No — correctness is the point. If you want a specific alternate version, put that version in the playlist (Spotify lists remixes as distinct tracks), and the matcher will require it.
</details>

<details>
<summary><b>Does it download audio from Spotify directly?</b></summary>

No. Spotify's API provides the track metadata (name, artist, duration, ISRC, album art). Audio is sourced from YouTube and matched back to the Spotify metadata. This is why the matching engine is the core of the project.
</details>

<details>
<summary><b><code>python main.py --check</code> shows a config error but downloads work</b></summary>

The check command reads a different config path than the main run in some setups. If `--setup` succeeded and `--playlists` starts downloading, your configuration is working.
</details>

---

## Security

- Keep `.env` local. It is in `.gitignore`; do not commit it.
- Never share your Spotify Client Secret in chats, screenshots, or issues. If it is exposed, **regenerate it** in the Spotify Dashboard → your app → *Settings* → *View client secret* → regenerate.
- Do not add `downloads/`, `.spotify_cache`, `.youtube_cache`, or `*.log` to git.

---

## Contributing

PRs welcome. The matcher is the highest-leverage area: if you find a real-world track that is wrongly rejected (or wrongly accepted), the fix usually belongs in `_version_tokens` (the version-keyword list) or `_has_text_relevance` (the artist fallback) in `src/features/download/infrastructure/youtube_matcher.py`, and should come with an offline regression test in `tests/test_youtube_matching.py` following the existing `types.SimpleNamespace`-based pattern (no network needed).

Run the test suite before submitting:

```powershell
python -m pytest -q
```

---

## License

See [LICENSE](LICENSE).

---

<div align="center">

**Repository:** [Gleb-Sergeevich-Loktionov/Grobbin-Mood-SpotiDL-DJs-edition](https://github.com/Gleb-Sergeevich-Loktionov/Grobbin-Mood-SpotiDL-DJs-edition)

Made for people who care that the file in their library is the track the playlist said it was.

</div>

---

<details>
<summary><strong>Keywords / search terms</strong></summary>

Spotify playlist downloader, download Spotify to MP3, Spotify to MP3 converter, YouTube track matching, correct track matching, no wrong version downloads, remix vs original matching, ISRC matching, yt-dlp Spotify, spotipy downloader, batch Spotify download, DJ track downloader, underground music downloader, FLAC MP3 M4A, embed ID3 metadata album art, resume downloads, skip existing, Windows PowerShell, Python CLI.

</details>
