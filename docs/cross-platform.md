# Cross-platform handoff (Android / Quest ↔ Desktop Suite)

Companions collect media **page URLs** on phone or headset. The **desktop Suite** remains the richest downloader (deep crawl, cookies-from-browser profiles, paced queue). On-device yt-dlp on Android/Quest writes media into app storage for local use; inbox export is the bridge that enqueues the same URLs on desktop.

## Roles

| Surface | Package / launch | What it does | Inbox `source` |
| --- | --- | --- | --- |
| Desktop Suite | `.venv/bin/python main.py` or `ytsdownloader` / freeze | Resolve, crawl, download, watermark, queue | Consumes inbox |
| Phone / GrapheneOS | `dev.voxhash.ytscompanion.debug` (debug APK) | Queue, on-device download, export | `android-companion` |
| Meta Quest 3 | `dev.voxhash.ytscompanion.quest` | Same UI in 2D panel or immersive shell | `quest-companion` |

See [android.md](android.md), [quest.md](quest.md), [installation.md](installation.md), [usage.md](usage.md).

## NDJSON / JSON schema (v1)

Parsed by `ytscore.companion.parse_companion_payload` / `consume_companion_inbox`. Only `http` / `https` URLs are accepted.

Single object (or one NDJSON line):

```json
{"schema": 1, "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "title": "optional", "source": "android-companion"}
```

Batch document (what **Export to Downloads** / **Export inbox file** write from the companions):

```json
{
  "schema": 1,
  "source": "android-companion",
  "urls": [
    {"schema": 1, "url": "https://example.com/watch?v=1", "source": "android-companion", "title": "optional"},
    {"schema": 1, "url": "https://example.com/watch?v=2", "source": "android-companion"}
  ]
}
```

Quest uses the same shape with `"source": "quest-companion"`. Optional `title` / `page_url` are metadata only — desktop still resolves via yt-dlp.

Bare URL lines and `{"urls":["https://…"]}` are also accepted (browser helpers / scripts).

## Desktop inbox paths

Working directory is the Suite process cwd (same place as `config.ini` and `.ytsdownloader/queue_state.json`).

| Path | Role |
| --- | --- |
| `.ytsdownloader/inbox/` | Drop complete files (`*.json`, `*.jsonl`, `*.txt`, `*.url`, `*.urls`). After a successful read the Suite renames to `*.processed`. |
| `.ytsdownloader/companion_inbox.jsonl` | Append NDJSON (one object or bare URL per line). Suite truncates after consuming non-empty content. |

Ensure the layout exists (Suite creates it on launch):

```bash
mkdir -p .ytsdownloader/inbox
```

## Polling

While the Suite window is open, a timer polls the inbox about every **1.5 seconds** (`QTimer` interval `1500` ms in `ytsgui/main_window.py`). Consumed URLs take the same enqueue path as the Download drop zone / Link Grabber (active export preset + crawl settings on Download).

- Suite **must be running** (or you leave files for the next launch — they are consumed on the next poll after start).
- Duplicates in one consume pass are collapsed.
- No localhost HTTP server and no cloud relay — file drop only.

## Export from device → desktop

Preferred path (no SAF / share chooser):

1. On phone or Quest, fill the local queue, then tap **Export to Downloads** (or ADB `dev.voxhash.ytscompanion.action.EXPORT_DOWNLOADS`).
2. Files land under MediaStore **`Download/YTSCompanion/`** (plus an app-files copy under `Android/data/<package>/files/Download/`).
3. Pull into the Suite checkout inbox:

```bash
# Phone debug package
adb -s <pixel-serial> pull /sdcard/Download/YTSCompanion/ .ytsdownloader/inbox/

# Quest
adb -s "$QUEST_SERIAL" pull /sdcard/Download/YTSCompanion/ .ytsdownloader/inbox/
```

4. With Suite running, wait ~1–2 s (or longer if many files). Queue rows appear; press **Start** / **Start Queue** if the queue is paused.

Optional: **Share payload** (NDJSON/`text/plain` chooser), **Choose export folder (SAF)** + **Export inbox file**, or append lines yourself to `companion_inbox.jsonl`.

### Verify a payload without the UI

From the repo root (fish-safe):

```bash
.venv/bin/python -c "
from ytscore.companion import parse_companion_payload, consume_companion_inbox
from pathlib import Path
text = Path('.ytsdownloader/inbox').glob('yts_companion_*.json')
# peek one file if present:
files = sorted(Path('.ytsdownloader/inbox').glob('yts_companion_*.json'))
print('files', [p.name for p in files])
if files:
    print(parse_companion_payload(files[0].read_text()))
"
```

## End-to-end workflows

### A. Phone queue → desktop download

1. Install phone APK ([android.md](android.md)).
2. Paste / share URLs → optional on-device **Download queue** (media stays on phone).
3. **Export to Downloads** → `adb pull … .ytsdownloader/inbox/`.
4. Suite open → URLs enqueue → **Start Queue**.

### B. Quest browse → desktop download

1. Install Quest APK; clear **Unknown Sources** once ([quest.md](quest.md)).
2. Paste or ADB `ACTION_SEND` into the 2D panel (or immersive shell hosting the same UI).
3. **Export to Downloads** → `adb pull` into `.ytsdownloader/inbox/`.
4. Suite open → enqueue → **Start**.

### C. Desktop-only (no companion)

Use Download drop zone, Link Grabber, or write NDJSON yourself — same inbox contract ([architecture.md](architecture.md#browser-companion-handoff-contract)).

### D. Cookies split

| Need | Where |
| --- | --- |
| Cookies-from-browser profiles (`COOKIES_FROM_BROWSER`) | Desktop Settings only |
| Netscape `cookies.txt` for on-device yt-dlp | Export on desktop → copy to device → **Pick cookies.txt (SAF)** |
| Private / age-gated media on phone | Valid Netscape import on device, or hand off URL to desktop with browser cookies |

## What does *not* sync

- Downloaded media files on phone/Quest are **not** uploaded to the Suite. Pull with `adb pull` from app `Movies/YTSCompanion/` if you want local copies on the host.
- Queue state is separate: companion `shared_prefs` vs desktop `.ytsdownloader/queue_state.json`.
- No FCM / cloud sync — GrapheneOS-friendly by design.

## Related

- Architecture contract: [architecture.md → Browser companion handoff](architecture.md#browser-companion-handoff-contract)
- Optional Go/Ruby inbox helpers: [installation.md → Native sidecars](installation.md#optional-native-sidecars)
