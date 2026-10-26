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
ffprobe -version
```

Install ffmpeg via your OS package manager and ensure **both** `ffmpeg` and `ffprobe` are on `PATH`. Frozen PyInstaller builds still expect these tools at runtime (see [Installation → Packaging](installation.md#packaging-windows--macos--linux-distributables)).

## "No videos found"

- Confirm the URL matches the selected platform tab
- Private / age-gated / unlisted content needs cookies (`COOKIES_FROM_BROWSER` or `COOKIES_FILE`)
- Profile pages may require authentication for Instagram / Facebook / TikTok
- Adult-tube playlists: configure cookies for private/unlisted lists; public singles still need `curl_cffi` + `IMPERSONATE` when the host returns HTTP 403

## HTTP 403 / "impersonation" warnings from yt-dlp

Install the optional TLS stack and keep impersonation on via Suite **Settings → TLS impersonate** (`chrome`) or `config.ini`:

```bash
.venv/bin/pip install -r requirements.txt
```

```ini
IMPERSONATE = chrome
```

Clear the Suite field (or empty `IMPERSONATE`) to disable the Suite default. Extractors may still request impersonation when `curl_cffi` is installed.

## Theme not loading

- Verify `themes/<THEME>/style.qss` exists
- Ensure `THEME` in `config.ini` matches the folder name exactly

## GUI / logging handler errors on exit

Known edge case during Qt shutdown order. Prefer confirming downloads completed; improvements are tracked under Milestone “Now” in `ROADMAP.md`.

## Tests fail / Qt needs a display

CI and local smoke use Qt’s **offscreen** platform — no X server or Xvfb required:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

On minimal Linux images, install Qt runtime libraries (same set as `.github/workflows/ci.yml`): `libegl1`, `libgl1`, `libdbus-1-3`, `libfontconfig1`, and the common `libxcb-*` / `libxkbcommon*` packages. Headed Suite click automation is not part of the supported validation path.

## Still stuck?

Open an issue with OS, Python version, and logs: https://github.com/VoxHash/YTSDownloader/issues
