# Installation

End-to-end **Desktop Suite** install for Linux / macOS / Windows, then open [usage.md](usage.md) for the post-install Suite flow. Companions: [android.md](android.md), [quest.md](quest.md). Handoff: [cross-platform.md](cross-platform.md).

## Desktop Suite — install (venv)

Fish-safe: call `.venv/bin/python` / `.venv/bin/pip` directly. Do **not** run `source .venv/bin/activate` in fish (use `source .venv/bin/activate.fish` if you want activation).

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
# or: ./run.sh
```

Windows (PowerShell, no Activate.ps1 required):

```powershell
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

After install: [Usage → After install](usage.md#after-install-desktop-suite).

## System packages

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg
# optional JS runtime
sudo apt install -y nodejs
```

### Fedora

```bash
sudo dnf install -y python3 ffmpeg nodejs
```

### macOS (Homebrew)

```bash
brew install python ffmpeg node
```

### Windows

1. Install Python 3.10+ from https://www.python.org/downloads/
2. Install FFmpeg and add it to `PATH` (https://ffmpeg.org/download.html)
3. Optional: install Node.js from https://nodejs.org/

## Python dependencies (detail)

Same venv as [Desktop Suite — install](#desktop-suite--install-venv). Optional activation (not required if you call `.venv/bin/python` directly):

- bash/zsh: `source .venv/bin/activate`
- fish: `source .venv/bin/activate.fish`
- Windows: `.venv\Scripts\activate`

Pinned packages (from `requirements.txt`):

- `yt-dlp==2026.10.21`
- `numpy==2.4.3`
- `moviepy==2.2.1`
- `pillow==11.3.0`
- `PyQt6==6.10.2`

## Verify

```bash
.venv/bin/python -m py_compile main.py
ffmpeg -version
ffprobe -version
.venv/bin/python -c "import yt_dlp, moviepy, PyQt6; print('ok')"
```

## Local desktop install (Linux menu / PATH)

Registers **one** user-local PATH wrapper and `.desktop` entry that always launch this checkout via `.venv/bin/python main.py` (fish-safe; no venv activate). Does **not** put `dist/` freeze binaries on PATH — keep the freeze as a build artifact only. Creates the venv and installs `requirements.txt` if needed.

```bash
chmod +x scripts/install_local.sh
./scripts/install_local.sh
ytsdownloader
```

Creates:

| Path | Role |
| --- | --- |
| `~/.local/bin/ytsdownloader` | Wrapper → absolute project `.venv/bin/python main.py` |
| `~/.local/share/applications/ytsdownloader.desktop` | Application menu entry (`Exec` → that wrapper, `Icon=ytsdownloader`) |
| `~/.local/share/icons/hicolor/*/apps/ytsdownloader.{png,svg}` | Freedesktop icon from `assets/icons/` |

Re-run the script after moving the repo (or after icon updates) so paths and icons stay correct. Personal `.desktop` / bin / icon files under `~/.local` are machine-local and are not committed.

## Optional native sidecars

Python + PyQt6 + yt-dlp remain the orchestration path. Optional helpers live under `native/` and install into `native/bin/` (override with `YTS_NATIVE_DIR`). If a binary is missing or fails, the Suite uses pure-Python fallbacks automatically.

| Tool | Language | Purpose |
| --- | --- | --- |
| `yts-normalize` | Rust | Batch URL/path normalize + dedupe (JSON IPC) |
| `yts-prio` | C (or `zig cc`) | Optional process nice + Linux idle I/O |
| `yts-inbox` | Go | Concurrent companion inbox consume |
| `yts_json_filter.rb` | Ruby | Optional companion JSON filter (`ruby` on `PATH`) |

### Build (fish-safe)

```bash
# Toolchains as available: cargo, cc/gcc (or zig), go, ruby (script copy)
./scripts/build_natives.sh
# Install prefix:
# YTS_NATIVE_DIR=/opt/yts/native ./scripts/build_natives.sh
```

Runtime knobs:

| Env / config | Meaning |
| --- | --- |
| `YTS_USE_NATIVE=0` | Disable all native discovery |
| `YTS_NATIVE_DIR` | Directory containing built binaries / Ruby script |
| `PROCESS_NICE` | CPU nice on Start Queue (`0` = unchanged; Settings spinbox) |
| `PROCESS_IDLE_IO` | Linux idle I/O class on Start Queue (default `true`) |

Frozen builds: the freeze helpers copy `native/bin/` into `dist/YTSDownloader/native/bin/` when the repo tree is non-empty (`BUNDLE_NATIVES=auto`, default). Force with `BUNDLE_NATIVES=1`, skip with `BUNDLE_NATIVES=0`. At runtime the Suite looks for sidecars next to the frozen executable (`<onedir>/native/bin`), then the checkout path, then `./native/bin`, or `YTS_NATIVE_DIR`. Natives are **not** required for the freeze to run (Python fallbacks).

## Optional Android / Quest companions

Kotlin companions under `android/` (no Play Services / FCM). Desktop Suite stays the richest downloader — companions export inbox payloads into `.ytsdownloader/inbox/`.

| Flavor | Build | Docs |
| --- | --- | --- |
| Phone / GrapheneOS | `./scripts/build_android.sh` | [android.md](android.md) — install + use |
| Meta Quest 3 (Horizon 2D + immersive shell) | `./scripts/build_quest.sh` (release: `RELEASE=1`) | [quest.md](quest.md) — install + use |
| Cross-platform handoff | — | [cross-platform.md](cross-platform.md) |

## Packaging (Windows / macOS / Linux distributables)

Ship frozen desktop builds with **PyInstaller** (`onedir`). PyInstaller has maintained PyQt6 hooks, does not cross-compile (build on each OS), and matches how most PyQt6 + heavy native-dep apps are frozen today. Prefer `onedir` over `onefile` for Qt plugin layout, faster cold start, and easier debugging.

| Tool | Role for this Suite |
| --- | --- |
| **PyInstaller** (primary) | Freeze `main.py` + `ytscore` / `ytsgui` + PyQt6 / yt-dlp / moviepy into a folder you zip or wrap |
| **Briefcase** (optional) | Wrap an already-built tree as MSI / DMG / native Linux package ([external app](https://briefcase.beeware.org/en/latest/how-to/building/external-apps/) mode) |
| **cx_Freeze** (alternative) | MIT-licensed freezer; same “build per OS” rule; less Suite-specific recipe here |
| **pyside6-deploy** | Qt for Python (PySide6) only — **not** used; this project is **PyQt6** |

### External runtime: ffmpeg / ffprobe

Distributables **do not** replace system mux/encode tools for yt-dlp:

- End users (or your installer) must provide **`ffmpeg` and `ffprobe` on `PATH`**.
- Watermarking via moviepy may also use the **`imageio-ffmpeg`** binary collected into the freeze; still keep system ffmpeg/ffprobe for download post-processing and format merge.
- Optional Node.js (`node` on `PATH`, or `JS_RUNTIME_PATH`) remains a separate install for extractor JS challenges.

Do **not** assume a frozen build is self-sufficient without documenting those PATH tools.

### Shared recipe (run on the target OS)

Helpers (same flags; post-copy `config.ini` + `themes/` + `assets/` next to the binary for cwd loading; `--icon` points at `assets/icons/256x256/ytsdownloader.png`):

| OS | Command |
| --- | --- |
| Linux / macOS | `./scripts/build_pyinstaller.sh` |
| Windows | `.\scripts\build_pyinstaller.ps1` |

From the repo root, with the project venv already holding `requirements.txt`:

```bash
# Linux / macOS (fish-safe — no activate required)
./scripts/build_natives.sh          # optional; skip for Python-only
./scripts/build_pyinstaller.sh      # auto-bundles native/bin/ when present
# optional offscreen start smoke + force/skip natives:
SMOKE=1 BUNDLE_NATIVES=1 ./scripts/build_pyinstaller.sh
BUNDLE_NATIVES=0 ./scripts/build_pyinstaller.sh
```

```powershell
# Windows PowerShell
# Build natives on WSL/Linux or a Windows toolchain first into native\bin
.\scripts\build_pyinstaller.ps1
# $env:BUNDLE_NATIVES = "1"   # require native\bin
# $env:BUNDLE_NATIVES = "0"   # skip bundling
```

Override the interpreter when you are not using `.venv` (CI / custom envs):

```bash
YTS_PYTHON="$(command -v python)" ./scripts/build_pyinstaller.sh
```

```powershell
$env:YTS_PYTHON = (Get-Command python).Source
.\scripts\build_pyinstaller.ps1
```

Manual equivalent (same flags the Linux/macOS script uses):

```bash
.venv/bin/python -m PyInstaller \
  --noconfirm --clean \
  --windowed --name YTSDownloader --onedir \
  --paths . \
  --collect-all yt_dlp \
  --collect-all imageio_ffmpeg \
  --collect-all moviepy \
  --collect-submodules ytscore \
  --collect-submodules ytsgui \
  --hidden-import PIL \
  --add-data "$(pwd)/themes:themes" \
  --add-data "$(pwd)/assets:assets" \
  --add-data "$(pwd)/config.ini:." \
  --icon "$(pwd)/assets/icons/256x256/ytsdownloader.png" \
  --specpath build --workpath build/pyi --distpath dist \
  main.py
# then copy config.ini + themes/ + assets/ into dist/YTSDownloader/ (scripts do this)
```

Use absolute paths for `--add-data` when `--specpath` is outside the repo root layout (PyInstaller resolves relative sources against the spec directory). PyQt6 widgets/core/gui are collected by PyInstaller’s built-in hooks — avoid `--collect-all PyQt6` (it pulls unused QML/3D plugins and balloons the tree).

Output: `dist/YTSDownloader/` (executable + `_internal/` on recent PyInstaller). **Ship the whole folder**; do not move the binary alone. `build/` and `dist/` stay gitignored.

When natives were built before the freeze, the tree also contains:

```text
dist/YTSDownloader/
  YTSDownloader          # or YTSDownloader.exe
  config.ini
  themes/
  assets/
  native/bin/            # optional sidecars (yts-normalize, yts-prio, …)
  _internal/
```

Launch from that folder (writable cwd for `.ytsdownloader/` queue state):

```bash
cd dist/YTSDownloader
./YTSDownloader
# smoke (no display):
QT_QPA_PLATFORM=offscreen timeout 8 ./YTSDownloader
# confirm native discovery (fish-safe from a checkout with the same tree):
YTS_NATIVE_DIR="$(pwd)/native/bin" .venv/bin/python -c "from ytscore.native_bridge import native_status; print(native_status())"
```

```powershell
cd dist\YTSDownloader
.\YTSDownloader.exe
```

### Linux

1. Prefer `./scripts/build_pyinstaller.sh` on the **oldest glibc** you intend to support (or a manylinux-style container). Newer hosts can fail with `GLIBC_x.y not found` on older distros.
2. Preserve **symlinks** when copying or archiving PyInstaller 6+ trees (`cp -a`, `tar`, or `zip -y`).
3. Optional packaging of the folder: AppImage / `.tar.gz` / Briefcase `system_runtime_requires` including `ffmpeg`.
4. Metadata bridge still needs `dbus-send` or `busctl` on the user machine when that feature is used.
5. Optional manual GitHub Actions freeze: **Actions → Freeze (manual) → Run workflow** (`.github/workflows/freeze.yml`, `workflow_dispatch` only, Ubuntu artifact). Inputs: offscreen smoke and **bundle natives** (best-effort `gcc` / `golang-go` build into the artifact’s `native/bin/`). Not a required PR check. If the run stays **Queued**, hosted runners may be unavailable for the org — freeze locally instead.

### macOS

1. Use the same bash helper on the Mac you will ship for (Intel vs Apple Silicon are separate builds unless you explicitly produce a universal workflow):

```bash
brew install python ffmpeg
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
./scripts/build_pyinstaller.sh
# optional:
SMOKE=1 ./scripts/build_pyinstaller.sh
```

2. After `onedir`, wrap with PyInstaller `BUNDLE` or Briefcase for a `.app`, then **codesign** and **notarize** before wide distribution (Apple requirements change; follow current Apple + Briefcase docs).
3. Users still need Homebrew (or equivalent) `ffmpeg` / `ffprobe` on `PATH` unless you legally redistribute binaries and point the app at them.
4. There is **no** macOS job in the optional `freeze.yml` workflow yet — treat GitHub macOS freeze as out of scope until a local Apple Silicon / Intel freeze is green and signing secrets exist.

### Windows

1. Build on Windows with the same Python major/minor you validate in CI/manual smoke.
2. Prefer `.\scripts\build_pyinstaller.ps1` (`onedir`); zip the folder or wrap with Inno Setup / Briefcase MSI for Start Menu shortcuts.
3. Install [FFmpeg builds](https://ffmpeg.org/download.html) and ensure `ffmpeg.exe` / `ffprobe.exe` are on user `PATH`.
4. PowerShell (venv without Activate.ps1):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\build_pyinstaller.ps1
```

(`;` in `--add-data` remains valid on Windows; the `.ps1` helper uses absolute sources and copies `config.ini` / `themes/` into `dist\YTSDownloader\`.)

5. No Windows matrix job is claimed in CI; freeze on a real Windows machine (or a trusted self-hosted runner) before publishing `.zip` / MSI.

### What not to automate yet

- **Unit / offscreen Suite smoke** already runs on GitHub Actions (`.github/workflows/ci.yml`) with `QT_QPA_PLATFORM=offscreen` — that is not a freeze matrix.
- **Full cross-OS freeze CI** (required PR matrix on ubuntu + windows + macos) stays out of scope until each OS has a green **manual** freeze and runner capacity is reliable. The optional `freeze.yml` is Ubuntu-only, `workflow_dispatch` only, and best-effort.
- Do not bundle GPL UI or extractor sources into this MIT tree; ship yt-dlp as its upstream package inside the freeze only.

### Checklist before you publish a build

- [ ] `ffmpeg -version` and `ffprobe -version` work on a clean test account
- [ ] Suite window opens; theme loads (`themes/SuiteDark`)
- [ ] One short download + optional watermark completes
- [ ] Cookies / Node notes documented for end users when platforms require them
- [ ] Built with `scripts/build_pyinstaller.sh` or `scripts/build_pyinstaller.ps1` on that OS
- [ ] Optional: `./scripts/build_natives.sh` then freeze (auto-bundles `native/bin/`), or ship Python-only with `BUNDLE_NATIVES=0`
