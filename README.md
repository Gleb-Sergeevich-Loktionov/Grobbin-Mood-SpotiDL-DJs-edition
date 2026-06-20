# Grobbin Mood SpotiDL — DJ's Edition

**Download Spotify playlists to MP3 with *correct-track* matching that actually downloads the song you named — not a remix, not a live cut, not a cover.**

A Python CLI that reads a Spotify playlist, finds each track on YouTube, downloads the audio, and embeds full ID3 metadata + album art. The headline feature is a rigorous matching engine: if a playlist says `Officer John - Stay`, you get exactly `Stay` — never `Stay (Morgan Buckley Remix)`. And symmetrically, if the playlist *is* the remix, you get the remix — never the original.

> Built for DJs, music collectors, and anyone who's been burned by "Spotify downloaders" that grab the wrong version of half the tracks.

---

## Why this one

Most Spotify-to-MP3 tools search YouTube and take the first hit. That produces a predictable mess: the original is replaced by a random remix, a live recording sneaks in where the studio cut should be, an acoustic cover overwrites the real track, and niche/underground tracks simply fail because the search query was malformed. This project exists to fix exactly that.

The matcher runs **three hard gates** on every YouTube candidate before it is accepted, and skips (rather than downloads the wrong thing) when nothing qualifies:

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

- **Python 3.8+** (tested on 3.14).
- **FFmpeg** in your `PATH` (for audio extraction/conversion).
- **Spotify Developer app** — free `Client ID` and `Client Secret` from <https://developer.spotify.com/dashboard>.
- Internet access to Spotify, YouTube, and `googlevideo.com`.

Check your environment:

```powershell
python --version
ffmpeg -version
```

---

## Installation

```powershell
cd path\to\Grobbin-Mood-SpotiDL-DJs-edition
python -m pip install -r requirements.txt
```

If `yt-dlp` starts failing (YouTube changes its response format periodically), update it:

```powershell
python main.py --update
```

---

## First-time setup

Run the setup wizard:

```powershell
python main.py --setup
```

The wizard verifies Python and FFmpeg, collects your Spotify API credentials, picks format/quality/concurrency, writes `.env`, and tests the Spotify connection.

### Getting Spotify credentials

1. Go to <https://developer.spotify.com/dashboard> and log in with any Spotify account.
2. Click **Create app**. Fill in a name and description.
3. Set a **Redirect URI** (e.g. `http://localhost:8888/callback` or `http://127.0.0.1:9900/`).
4. Accept the terms and save.
5. Open the app → **Settings** → copy the **Client ID** and **View client secret** → copy the **Client Secret**.
6. Paste both into the setup wizard when prompted.

`.env` is created locally and is already in `.gitignore` — never commit it, and never paste your secret into chats or screenshots. If a secret is ever exposed, regenerate it in the Spotify Dashboard.

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

**A track I know is on YouTube was skipped. Why?**
Most often the available upload was the wrong version (the gate correctly rejected it), or the upload was unavailable/age-gated (`This video is not available` / `Sign in to confirm your age`). For age-gated videos, configure browser cookies in the YouTube section of your config so `yt-dlp` can authenticate. Rarely, the search queries didn't surface the right video; re-running or checking `failed_tracks.log` will tell you which gate rejected it.

**Can it download the wrong version on purpose?**
No — correctness is the point. If you want a specific alternate version, put that version in the playlist (Spotify lists remixes as distinct tracks), and the matcher will require it.

**Does it download from Spotify directly?**
No. Spotify's API provides the track metadata (name, artist, duration, ISRC, album art). Audio is sourced from YouTube and matched back to the Spotify metadata. This is why the matching engine is the core of the project.

**`python main.py --check` shows a config error but downloads work.**
The check command reads a different config path than the main run in some setups. If `--setup` succeeded and `--playlists` starts downloading, your configuration is working.

---

## Security

- Keep `.env` local. It is in `.gitignore`; do not commit it.
- Never share your Spotify Client Secret in chats, screenshots, or issues. If it is exposed, regenerate it in the Spotify Dashboard.
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

## GitHub

Repository: <https://github.com/Gleb-Sergeevich-Loktionov/Grobbin-Mood-SpotiDL-DJs-edition>

---

<details>
<summary><strong>Keywords / search terms</strong></summary>

Spotify playlist downloader, download Spotify to MP3, Spotify to MP3 converter, YouTube track matching, correct track matching, no wrong version downloads, remix vs original matching, ISRC matching, yt-dlp Spotify, spotipy downloader, batch Spotify download, DJ track downloader, underground music downloader, FLAC MP3 M4A, embed ID3 metadata album art, resume downloads, skip existing, Windows PowerShell, Python CLI.

</details>
