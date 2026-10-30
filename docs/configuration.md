# Configuration

Settings live in `config.ini` under the `[SETTINGS]` section.

## Suite Settings UI

Open **Settings** in the Suite sidebar to edit the keys below. **Save to config.ini** writes atomically and applies into the running app (pace, backoff, cookies, TLS impersonate, JS runtime, formats, retries, default output, status analytics). **Max workers** is picked up on the next **Start Queue**. **Reload config.ini** re-reads the file into the form and runtime.

The Settings page also shows a **Native helpers** panel (`ytscore.native_bridge.native_status`): whether `YTS_USE_NATIVE` is on, the search directory, and paths for normalize / priority / inbox / Ruby filter sidecars (or an honest Python-fallback note when missing). **Refresh** re-scans after you build natives.

## Keys

| Setting | Description | Default | Example |
| --- | --- | --- | --- |
| `THEME` | Theme directory under `themes/` | `SuiteDark` | `SuiteDark` |
| `COUNT_TIMER_ONGOING` | Seconds between playlist/job *starts* (shared across workers) | `2.5` | `3` |
| `COOKIES_FROM_BROWSER` | Browser cookies for yt-dlp | empty | `brave:Default` |
| `COOKIES_FILE` | Cookie file path | empty | `/path/to/cookies.txt` |
| `IMPERSONATE` | yt-dlp TLS/HTTP client impersonation (needs `curl_cffi`); Suite **TLS impersonate** combo (editable); empty disables | `chrome` | `chrome` / `chrome120` / empty |
| `JS_RUNTIME` | JavaScript runtime name | `node` | `node` |
| `JS_RUNTIME_PATH` | Absolute path to runtime binary | empty | `/usr/bin/node` |
| `MAX_WORKERS` | Concurrent download workers | `2` | `2` |
| `MAX_RETRIES` | Retries per item after failure | `3` | `3` |
| `BACKOFF_BASE` | Base seconds for exponential retry backoff | `2` | `2` |
| `BACKOFF_FACTOR` | Multiplier applied each retry | `2` | `2` |
| `BACKOFF_MAX` | Maximum retry wait (seconds); rate limits use a harder base | `90` | `90` |
| `AUDIO_FORMAT` | Preferred audio extract format | `m4a` | `mp3` |
| `VIDEO_FORMAT` | yt-dlp format expression (resilient A/V+progressive chain; legacy `bestvideo+bestaudio/best` auto-upgraded) | `bestvideo*+bestaudio/bestvideo+bestaudio/bv*+ba/b` | `best` |
| `DEFAULT_OUTPUT` | Default output folder | empty | `/home/you/Videos` |
| `SHOW_STATUS_ANALYTICS` | Show local session OK / Err / Last / Avg counters in the Suite status bar | `true` | `false` |
| `PROCESS_NICE` | CPU nice applied on **Start Queue** (`0` = leave priority alone) | `0` | `5` |
| `PROCESS_IDLE_IO` | Linux idle I/O class on **Start Queue** (yields disk to interactive apps) | `true` | `false` |
| `SKIP_EXISTING` | Skip downloads when a matching media id is already on disk or in `.yts_download_archive.txt` (Suite **Skip existing files**; default on). Overwrite wins when both are set. | `true` | `false` |
| `OVERWRITE` | Force re-download / replace existing files (Suite **Overwrite**). Disables skip-existing while on. | `false` | `true` |
| `NUMBER_FILES` | Prefix new downloads with the queue index (`0001_Title [id].ext`). Off → `Title [id].ext` only. | `true` | `false` |

**Crawl Limit** on the Download page is a Suite control (not a `config.ini` key): `1`–`10000`, or `0` / **Unlimited** for no item cap.

Status analytics are **local and session-scoped** only. Nothing is sent over the network.

Optional native helpers (`YTS_USE_NATIVE`, `YTS_NATIVE_DIR`) are env-only (not `config.ini` keys). See the Settings **Native helpers** panel and [Installation → Native sidecars](installation.md#optional-native-sidecars).

## Environment variables / secrets

This project does **not** require cloud API keys.

Sensitive local inputs:

- Browser cookie profiles referenced by `COOKIES_FROM_BROWSER`
- Exported `cookies.txt` / `cookies.json` (ignored by git)
- Optional local override file `config.ini.local` (ignored by git)
- Queue snapshot `.ytsdownloader/queue_state.json` (ignored by git; may include URLs and local paths)
- Companion inbox `.ytsdownloader/inbox/` and `.ytsdownloader/companion_inbox.jsonl` (ignored by git; may include page URLs from a browser helper)

## Authentication tips

1. Prefer `COOKIES_FROM_BROWSER = chrome` (or `firefox`, `edge`, `brave`, `opera`) when the browser is logged in.
2. Otherwise export cookies to a file and set `COOKIES_FILE`.
3. Deep **Crawl mode** options on Download (Deep / Videos / Shorts / Posts) require one of the above; Shallow works without cookies. Crawls only enumerate content your session can already reach via yt-dlp.
4. **Private / unlisted playlists** (including adult-tube playlists) need the same cookie auth — only surfaces your signed-in browser session can already open. No credential stuffing, DRM, or paywall bypass.
5. Keep `JS_RUNTIME = node` and set `JS_RUNTIME_PATH` only when `node` is not on `PATH`.
6. Install `curl_cffi` (via `requirements.txt`) and keep `IMPERSONATE = chrome` when hosts return HTTP 403 to plain clients.

## Themes

Create `themes/MyTheme/style.qss` (and optional `images/`), then set `THEME = MyTheme`.
