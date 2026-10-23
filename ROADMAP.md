# Roadmap

Current product baseline: **v0.4.3** — Suite queue triage actions (context menu / Clear All / force download) + Linux volume-aware folder picker.

## Now (v0.4.x)

- [x] Deeper social profile crawl modes behind cookie auth (legally constrained surfaces only).
- [x] CI scripted offscreen smoke (`unittest` + `QT_QPA_PLATFORM=offscreen` on GitHub Actions).
- [x] Manual per-OS PyInstaller freeze path complete (`scripts/build_pyinstaller.sh` / `.ps1`, packaging docs, optional Ubuntu-only `freeze.yml` via `workflow_dispatch`).
- [x] Queue context menu (remove / force download), Clear All, and volume sidebar on output-folder Browse.

## Next

_(empty — promote from Later when ready)_

## Later

_(empty)_

## Out of Scope (for now)

- Cloud sync or hosted download services.
- Copying GPL UI or extractor code into this MIT tree.
- Automated headed end-to-end GUI CI (display / Xvfb Suite click farms). Validation path: local + CI **scripted offscreen** unit/smoke under `tests/`, plus optional manual GUI checks before release.
- **Required** cross-OS freeze CI matrix on every PR (ubuntu + windows + macos as required checks). Manual per-OS freezes first; optional best-effort Ubuntu freeze is `workflow_dispatch` only — see packaging docs. Do not claim a green required matrix while hosted runners are flaky or signing/ffmpeg per OS is unfinished.
