# Contributing to YTSDownloader

Thanks for contributing to `YTSDownloader` by VoxHash Technologies.

## Development Setup

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Prefer `.venv/bin/python` / `.venv/bin/pip` (works in fish without activate). Optional: bash/zsh `source .venv/bin/activate`, fish `source .venv/bin/activate.fish`.

System dependencies:

- `ffmpeg` on `PATH` (`ffmpeg -version`)
- Optional: Node.js for yt-dlp JavaScript runtime (`node -v`)

## Run the App

```bash
.venv/bin/python main.py
# or: ./run.sh
```

## Validation

Primary path (same as CI): unit tests plus offscreen Suite smoke — no display required.

```bash
# fish-safe (no activate needed)
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

GitHub Actions runs the same command on Ubuntu with Qt runtime libraries installed (see `.github/workflows/ci.yml`). Headed GUI click farms are out of scope.

Optional compile / launch check:

```bash
.venv/bin/python -m py_compile main.py
.venv/bin/python main.py
```

Optional manual GUI smoke (before a release or UI-heavy PR):

- Suite window loads (sidebar: Download, Queue, Link Grabber, Metadata Bridge, Settings)
- Output folder + URL required-field validation works
- One short download completes when cookies/auth are configured if the platform requires it
- Optional watermark produces an output file

## Pull Request Process

- Keep scope focused on one issue or feature
- Update docs when behavior or configuration changes
- Link related issue(s) when available
- Follow conventional commits (`feat`, `fix`, `docs`, `chore`, …)

## Coding Notes

- Preserve existing user-facing behavior unless the PR explicitly targets a behavior change
- Document `config.ini` changes in `docs/configuration.md`
- Never commit cookie files or secrets (`cookies.txt`, `cookies.json`, `.env`)

## Code of Conduct

Please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
