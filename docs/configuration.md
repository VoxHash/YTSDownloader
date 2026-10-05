# Configuration

Settings live in `config.ini` under the `[SETTINGS]` section.

## Keys

| Setting | Description | Default | Example |
| --- | --- | --- | --- |
| `THEME` | Theme directory under `themes/` | `DarkFreeze` | `DarkFreeze` |
| `COUNT_TIMER_ONGOING` | Pause (seconds) between downloads | `2` | `2` |
| `COOKIES_FROM_BROWSER` | Browser cookies for yt-dlp | empty | `chrome` |
| `COOKIES_FILE` | Cookie file path | empty | `/path/to/cookies.txt` |
| `JS_RUNTIME` | JavaScript runtime name | `node` | `node` |
| `JS_RUNTIME_PATH` | Absolute path to runtime binary | empty | `/usr/bin/node` |

## Environment variables / secrets

This project does **not** require cloud API keys.

Sensitive local inputs:

- Browser cookie profiles referenced by `COOKIES_FROM_BROWSER`
- Exported `cookies.txt` / `cookies.json` (ignored by git)
- Optional local override file `config.ini.local` (ignored by git)

## Authentication tips

1. Prefer `COOKIES_FROM_BROWSER = chrome` (or `firefox`, `edge`, `brave`, `opera`) when the browser is logged in.
2. Otherwise export cookies to a file and set `COOKIES_FILE`.
3. Keep `JS_RUNTIME = node` and set `JS_RUNTIME_PATH` only when `node` is not on `PATH`.

## Themes

Create `themes/MyTheme/style.qss` (and optional `images/`), then set `THEME = MyTheme`.
