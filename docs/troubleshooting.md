# Troubleshooting

## YouTube: "Sign in to confirm you're not a bot"

Fresh environments without cookies commonly hit this. Configure authentication in `config.ini`:

```ini
COOKIES_FROM_BROWSER = chrome
```

or:

```ini
COOKIES_FILE = /absolute/path/to/cookies.txt
```

Restart the app after changing config. Validating with **Check Auth** on the YouTube tab is recommended.

## "No supported JavaScript runtime could be found"

Install Node.js and either keep `JS_RUNTIME = node` with `node` on `PATH`, or set:

```ini
JS_RUNTIME = node
JS_RUNTIME_PATH = /usr/bin/node
```

## ffmpeg errors / missing codecs

```bash
ffmpeg -version
```

Install ffmpeg via your OS package manager and ensure it is on `PATH`.

## "No videos found"

- Confirm the URL matches the selected platform tab
- Private / age-gated content needs cookies
- Profile pages may require authentication for Instagram / Facebook / TikTok

## Theme not loading

- Verify `themes/<THEME>/style.qss` exists
- Ensure `THEME` in `config.ini` matches the folder name exactly

## GUI / logging handler errors on exit

Known edge case during Qt shutdown order. Prefer confirming downloads completed; improvements are tracked under Milestone “Now” in `ROADMAP.md`.

## Still stuck?

Open an issue with OS, Python version, and logs: https://github.com/VoxHash/YTSDownloader/issues
