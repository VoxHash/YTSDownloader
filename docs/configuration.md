# Configuration

Settings are defined in `config.ini`.

## `SETTINGS` Keys
- `THEME`: Name of the folder under `themes/` (example: `DarkFreeze`).
- `COUNT_TIMER_ONGOING`: Refresh interval used by the UI.
- `COOKIES_FROM_BROWSER`: Browser source for yt-dlp cookies (optional).
- `COOKIES_FILE`: Cookie file path for authenticated access (optional).
- `JS_RUNTIME`: JavaScript runtime name for yt-dlp extraction (example: `node`).
- `JS_RUNTIME_PATH`: Absolute path to the runtime binary (optional but recommended).

## Notes
- If YouTube requests bot verification, set `COOKIES_FROM_BROWSER` or `COOKIES_FILE`.
- Keep `JS_RUNTIME` and `JS_RUNTIME_PATH` valid to avoid missing-format extraction warnings.
