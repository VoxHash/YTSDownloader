# Contributing to YTSDownloader

Thanks for contributing to `YTSDownloader`.

## Development Setup
```bash
git clone https://github.com/VoxHash-Technologies/YTSDownloader.git
cd YTSDownloader
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the App
```bash
./.venv/bin/python main.py
```

## Validation and Tests
There is currently no dedicated automated test suite in this repository. Before opening a PR, run:

```bash
python -m py_compile main.py
./.venv/bin/python main.py
```

Then perform a manual smoke test:
- load the app successfully
- start one short download flow
- confirm output file generation in the selected folder

## Pull Request Process
- Keep the scope focused on one issue or feature.
- Update docs when behavior changes.
- Add a clear PR description with:
  - problem statement
  - approach
  - validation steps and results
- Link related issue(s) when available.

## Coding Notes
- Preserve existing user-facing behavior unless the PR explicitly targets behavior changes.
- Keep configuration changes in `config.ini` documented in `docs/configuration.md`.
