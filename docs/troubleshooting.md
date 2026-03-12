# Troubleshooting

## YouTube "Sign in to confirm you're not a bot"
- Configure authentication in `config.ini`:
  - `COOKIES_FROM_BROWSER`
  - or `COOKIES_FILE`

## "No supported JavaScript runtime could be found"
- Ensure `JS_RUNTIME` is set (for example `node`).
- Ensure `JS_RUNTIME_PATH` points to a valid executable.

## ffmpeg-related failures
- Install ffmpeg and verify:
```bash
ffmpeg -version
```

## GUI exits with logging handler error
- This is related to shutdown order of Qt objects and logging handlers.
- Re-run and confirm download output first; track improvements in `ROADMAP.md` milestone 1.
