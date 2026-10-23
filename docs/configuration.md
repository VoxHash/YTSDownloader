# Configuration

Settings live in `config.ini` under the `[SETTINGS]` section.

## Keys

| Setting | Description | Default | Example |
| --- | --- | --- | --- |
| `THEME` | Theme directory under `themes/` | `SuiteDark` | `SuiteDark` |
| `COUNT_TIMER_ONGOING` | Seconds between playlist/job *starts* (shared across workers) | `2.5` | `3` |
| `COOKIES_FROM_BROWSER` | Browser cookies for yt-dlp | empty | `brave:Default` |
| `COOKIES_FILE` | Cookie file path | empty | `/path/to/cookies.txt` |
| `JS_RUNTIME` | JavaScript runtime name | `node` | `node` |
| `JS_RUNTIME_PATH` | Absolute path to runtime binary | empty | `/usr/bin/node` |
| `MAX_WORKERS` | Concurrent download workers | `2` | `2` |
| `MAX_RETRIES` | Retries per item after failure | `3` | `3` |
| `BACKOFF_BASE` | Base seconds for exponential retry backoff | `2` | `2` |
| `BACKOFF_FACTOR` | Multiplier applied each retry | `2` | `2` |
| `BACKOFF_MAX` | Maximum retry wait (seconds); rate limits use a harder base | `90` | `90` |
| `AUDIO_FORMAT` | Preferred audio extract format | `m4a` | `mp3` |
| `VIDEO_FORMAT` | yt-dlp format expression | `bestvideo+bestaudio/best` | `best` |
| `DEFAULT_OUTPUT` | Default output folder | empty | `/home/you/Videos` |

## Environment variables / secrets

This project does **not** require cloud API keys.

Sensitive local inputs:

- Browser cookie profiles referenced by `COOKIES_FROM_BROWSER`
- Exported `cookies.txt` / `cookies.json` (ignored by git)
- Optional local override file `config.ini.local` (ignored by git)
- Queue snapshot `.ytsdownloader/queue_state.json` (ignored by git; may include URLs and local paths)

## Authentication tips

1. Prefer `COOKIES_FROM_BROWSER = chrome` (or `firefox`, `edge`, `brave`, `opera`) when the browser is logged in.
2. Otherwise export cookies to a file and set `COOKIES_FILE`.
3. Keep `JS_RUNTIME = node` and set `JS_RUNTIME_PATH` only when `node` is not on `PATH`.

## Themes

Create `themes/MyTheme/style.qss` (and optional `images/`), then set `THEME = MyTheme`.
