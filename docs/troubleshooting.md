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

Install Node.js (20+) or Deno and either keep `JS_RUNTIME = node` with `node` on `PATH`, or set:

```ini
JS_RUNTIME = node
JS_RUNTIME_PATH = /usr/bin/node
```

Suite also auto-resolves fnm-managed Node under `~/.local/share/fnm/node-versions/` when PATH is empty (common for GUI launches). Install deps with `pip install -r requirements.txt` so the `yt-dlp-ejs` challenge solver ships with `yt-dlp[default]`.

## "Requested format is not available" / Format / ffmpeg triage

YouTube often needs a working JS runtime (see above) so real video formats appear; without it yt-dlp may only list storyboard images and every video format fails. Suite defaults to a resilient merge chain (`bestvideo*+bestaudio/…/bv*+ba/b`) and falls back once if a custom `VIDEO_FORMAT` matches nothing. Keep ffmpeg on `PATH` so separate video+audio streams can remux to mp4.

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
- Adult video host (`rule34_video`): if resolve returns empty or download fails on restricted pages, set `COOKIES_FROM_BROWSER` (e.g. `brave:Default`) or `COOKIES_FILE` for a session that can already open the URL; keep `IMPERSONATE = chrome`
- Creator / gallery / clip hosts (`creator_media`): ManyVids may only expose previews without purchase cookies; Reddit / Vimeo often need a signed-in browser profile; Clips4Sale rewrite uses public preview MP4 when present; Aryion favorites / category listings paginate via `Page X of Y` + `?p=N` / `Next >>` under Deep/Videos or Unlimited resolve, then stream originals via `/g4/data.php?id=` (image, video, audio, PDF/DOC/DOCX, Flash/SWF, ZIP, etc.) with extension from Content-Type / Content-Disposition — re-run with skip-existing if older runs saved HTML/PDF payloads as `.mp4`

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

## Suite shows “Not Responding” with a huge Queue

Workers can keep downloading while the window frame freezes. That was usually **Queue UI + JSON persist on the main thread** (full-table filter / rebuild, rewriting `.ytsdownloader/queue_state.json` for every progress tick), not proof that the download core needs a new language.

From **v0.21.0** the Queue table shows one **filtered page** (Prev/Next, 250 rows), coalesces progress updates, and debounces compact snapshots off the UI thread. Practical tips for 10k+ jobs:

1. Update to **≥ 0.21.0**, then restart the Suite so restore uses the paged view (not one row insert per job).
2. Filter **State → Failed** (or Running) instead of scrolling All; use Prev/Next for other pages.
3. Prefer **Clear Finished** periodically so done/failed rows leave the persisted snapshot.
4. Avoid hammering Search while thousands of items are mid-progress; filters debounce, but typing still rescans the in-memory job list.
5. If the window was frozen mid-run on an older build, Stop → wait for the process to accept input → upgrade → Start again (restore remaps in-flight jobs to queued).

## Closing YTSDownloader also closes other VoxHash Qt apps (or vice versa)

From **v0.21.1** the Suite sets a unique Qt identity (`VoxHash` / `YTSDownloader` / desktop id `ytsdownloader`) before `QApplication`, and Linux menu/PATH launches go through `scripts/run_ytsdownloader.sh` (`setsid` + cleared host `QT_PLUGIN_PATH`). Re-install the desktop entry after upgrading:

```bash
./scripts/install_local.sh
```

Then fully quit and relaunch each app from its own menu/PATH entry (not a shared parent shell that backgrounds several `python main.py` jobs in one process group).

Sibling apps should each call `setApplicationName(<unique>)`, `setDesktopFileName(<desktop-basename>)`, and ship a matching `StartupWMClass` — recommended ids:

| App | ApplicationName | desktop file / `setDesktopFileName` |
| --- | --- | --- |
| YTSDownloader | `YTSDownloader` | `ytsdownloader` |
| ForexSmartBot | `ForexSmartBot` | `forexsmartbot` |
| DB Storage Manager | (existing `APP_NAME`) | `db-storage-manager` |
| Telegram Multi-Account Message Sender | `Telegram Multi-Account Message Sender` | match installed `.desktop` basename |

If a top strip shows “On Playground” / “On Workspace” with X buttons, that is the Cursor agent UI for multiple project chats — closing those cards does not quit the desktop apps.

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
