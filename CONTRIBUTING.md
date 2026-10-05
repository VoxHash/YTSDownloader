# Contributing to YTSDownloader

Thanks for contributing to `YTSDownloader` by VoxHash Technologies.

## Development Setup

```bash
git clone https://github.com/VoxHash/YTSDownloader.git
cd YTSDownloader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

System dependencies:

- `ffmpeg` on `PATH` (`ffmpeg -version`)
- Optional: Node.js for yt-dlp JavaScript runtime (`node -v`)

## Run the App

```bash
python main.py
```

## Validation

There is currently no automated test suite. Before opening a PR:

```bash
python -m py_compile main.py
python main.py
```

Manual smoke checklist:

- App window loads with four platform tabs
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
