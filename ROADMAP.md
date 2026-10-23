# Roadmap

Current product baseline: **v0.4.1** — CI scripted offscreen unit / Suite smoke on push and PR.

## Now (v0.4.x)

- [x] Deeper social profile crawl modes behind cookie auth (legally constrained surfaces only).
- [x] CI scripted offscreen smoke (`unittest` + `QT_QPA_PLATFORM=offscreen` on GitHub Actions).

## Next

_(empty — promote from Later when ready)_

## Later

_(empty)_

## Out of Scope (for now)

- Cloud sync or hosted download services.
- Copying GPL UI or extractor code into this MIT tree.
- Automated headed end-to-end GUI CI (display / Xvfb Suite click farms). Validation path: local + CI **scripted offscreen** unit/smoke under `tests/`, plus optional manual GUI checks before release.
- Cross-OS freeze CI matrix (manual per-OS PyInstaller builds first; see packaging docs).
