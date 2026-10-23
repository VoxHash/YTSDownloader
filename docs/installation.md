# Installation

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

## Python dependencies

```bash
cd YTSDownloader
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Optional activation (not required if you call `.venv/bin/python` directly):

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

From the repo root, with the project venv already holding `requirements.txt`:

```bash
.venv/bin/python -m pip install -U "pyinstaller>=6.11"
./scripts/build_pyinstaller.sh
```

Fish-safe (no `source` of bash activate scripts):

```fish
.venv/bin/python -m pip install -U "pyinstaller>=6.11"
./scripts/build_pyinstaller.sh
```

Manual equivalent (same flags the script uses):

```bash
.venv/bin/pyinstaller \
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
  --add-data "$(pwd)/config.ini:." \
  --specpath build --workpath build/pyi --distpath dist \
  main.py
```

Use absolute paths for `--add-data` when `--specpath` is outside the repo root layout (PyInstaller resolves relative sources against the spec directory). PyQt6 widgets/core/gui are collected by PyInstaller’s built-in hooks — avoid `--collect-all PyQt6` (it pulls unused QML/3D plugins and balloons the tree).


Output: `dist/YTSDownloader/` (executable + `_internal/` on recent PyInstaller). The helper also copies `config.ini` and `themes/` next to the binary because the Suite loads those paths from the **process cwd**. **Ship the whole folder**; do not move the binary alone.

Launch from that folder (writable cwd for `.ytsdownloader/` queue state):

```bash
cd dist/YTSDownloader
./YTSDownloader
# smoke (no display):
QT_QPA_PLATFORM=offscreen timeout 8 ./YTSDownloader
```

### Linux

1. Build on the **oldest glibc** you intend to support (or a manylinux-style container). Newer hosts can fail with `GLIBC_x.y not found` on older distros.
2. Preserve **symlinks** when copying or archiving PyInstaller 6+ trees (`cp -a`, `tar`, or `zip -y`).
3. Optional packaging of the folder: AppImage / `.tar.gz` / Briefcase `system_runtime_requires` including `ffmpeg`.
4. Metadata bridge still needs `dbus-send` or `busctl` on the user machine when that feature is used.

### macOS

1. Build on the macOS / arch you target (Intel vs Apple Silicon are separate builds unless you explicitly produce a universal workflow).
2. After `onedir`, wrap with PyInstaller `BUNDLE` or Briefcase for a `.app`, then **codesign** and **notarize** before wide distribution (Apple requirements change; follow current Apple + Briefcase docs).
3. Users still need Homebrew (or equivalent) `ffmpeg` / `ffprobe` on `PATH` unless you legally redistribute binaries and point the app at them.

Example Homebrew deps on the **build** and **run** machines:

```bash
brew install python ffmpeg
```

### Windows

1. Build on Windows with the same Python major/minor you validate in CI/manual smoke.
2. Prefer `onedir`; zip the folder or wrap with Inno Setup / Briefcase MSI for Start Menu shortcuts.
3. Install [FFmpeg builds](https://ffmpeg.org/download.html) and ensure `ffmpeg.exe` / `ffprobe.exe` are on user `PATH`.
4. PowerShell (venv without bash activate):

```powershell
$Root = (Get-Location).Path
.\.venv\Scripts\python.exe -m pip install -U "pyinstaller>=6.11"
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name YTSDownloader --onedir `
  --paths $Root --collect-all yt_dlp --collect-all imageio_ffmpeg `
  --collect-all moviepy --collect-submodules ytscore --collect-submodules ytsgui `
  --hidden-import PIL --add-data "$Root\themes;themes" --add-data "$Root\config.ini;." `
  --specpath build --workpath build\pyi --distpath dist main.py
```

(`;` in `--add-data` remains valid on Windows; PyInstaller 6+ also accepts `source:dest`. Prefer absolute source paths when using `--specpath build`.)


### What not to automate yet

- **Unit / offscreen Suite smoke** already runs on GitHub Actions (`.github/workflows/ci.yml`) with `QT_QPA_PLATFORM=offscreen` — that is not a freeze matrix.
- No cross-OS **PyInstaller freeze** CI matrix is claimed in-repo: freezing PyQt6 + yt-dlp needs per-OS runners, signing secrets, and ffmpeg on those images. Add freeze CI only after a green manual freeze on each platform.
- Do not bundle GPL UI or extractor sources into this MIT tree; ship yt-dlp as its upstream package inside the freeze only.

### Checklist before you publish a build

- [ ] `ffmpeg -version` and `ffprobe -version` work on a clean test account
- [ ] Suite window opens; theme loads (`themes/SuiteDark`)
- [ ] One short download + optional watermark completes
- [ ] Cookies / Node notes documented for end users when platforms require them
