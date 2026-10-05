# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

Report security issues privately to **contact@voxhash.dev**.

Please include:

- A clear description of the issue
- Steps to reproduce
- Affected version / commit
- Impact assessment if known

Do not open a public GitHub issue for undisclosed vulnerabilities.

We aim to acknowledge reports within 7 days and provide a remediation plan or
status update after triage.

## Scope Notes

- `YTSDownloader` stores optional browser cookie paths and cookie files locally
  for `yt-dlp` authentication. Treat cookie files as secrets.
- Do not commit `cookies.txt`, `cookies.json`, or populated `config.ini.local`
  values that contain private paths or credentials.
