# j315scan

Unofficial network scanner for **Brother DCP-J315W** (and other brscan3-class devices) on modern macOS / Linux / Windows.

Official Brother Mac drivers stop at macOS 10.15. This app talks to TCP port **54921** directly. It is not affiliated with Brother Industries.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- Color (JPEG) and grayscale network scan at 100 / 150 / 200 / 300 dpi
- GUI (Tk) and CLI
- Split several photos on the glass into separate files
- Languages: English, Polish, German (`auto` follows the OS)
- Config file + remembered GUI settings
- Default save folder: `~/Pictures`

## Requirements

- Python 3.10+ with Tk
- Same LAN as the printer (VPN split-tunnel can steal `192.168.0.0/16`)
- Device must expose port 54921 (`+OK 200`)

## Install

```bash
git clone https://github.com/<you>/j315scan.git
cd j315scan
./run.sh
```

`run.sh` creates `.venv` and installs `requirements.txt`.

Double-click on macOS: `Skaner.command`.

Manual:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## CLI

```bash
.venv/bin/python cli.py --probe
.venv/bin/python cli.py --mode color --dpi 200
.venv/bin/python cli.py --no-split --lang pl
.venv/bin/python cli.py --host 192.168.0.80 -o ~/Pictures
```

Files: `~/Pictures/scan-YYYYMMDD-HHMMSS.jpg`  
With split: `scan-…-01.jpg`, `scan-…-02.jpg`, …

## Configuration

| Key | Default | Meaning |
|---|---|---|
| `host` | `192.168.0.80` | Scanner IP |
| `port` | `54921` | Brother scan port |
| `mode` | `color` | `color` or `gray` |
| `dpi` | `200` | 100, 150, 200, 300 |
| `split` | `true` | Detect and crop objects |
| `outdir` | `~/Pictures` | Save folder |
| `filename_prefix` | `scan` | File name prefix |
| `language` | `auto` | `auto`, `en`, `pl`, `de` |
| `jpeg_quality` | `92` | JPEG quality |
| `idle_timeout` | `25` | Seconds of silence between frames |
| `max_seconds` | `180` | Hard cap per scan |

Load order (later wins):

1. Built-in defaults
2. `config.yaml` next to the app (copy from `config.example.yaml`)
3. `~/.config/j315scan/settings.json`
4. `./settings.json` (gitignored; written by the GUI)

## Protocol

1. Banner `+OK 200`
2. `ESC I` lease → `dpi,dpi,adf,mmX,pxX,mmY,pxY`
3. `ESC X` scan → gray rows (`type + len16le + pixels`) or chunked JPEG

Printing (Brother HBP on :9100) is out of scope.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m build
```

CI (`.github/workflows/ci.yml`) runs lint, tests on Python 3.10–3.13, and publishes sdist/wheel artifacts.

## Release

1. Bump `version` in `pyproject.toml` and add a `## [x.y.z]` section in `CHANGELOG.md`.
2. Commit, then:

```bash
git tag v0.2.0
git push origin main --tags
```

`.github/workflows/release.yml` builds, re-runs tests, and creates a GitHub Release with notes from the changelog plus `dist/*.whl` / `dist/*.tar.gz`.

Manual: Actions → Release → Run workflow.

## License

MIT. See [LICENSE](LICENSE). Protocol notes are based on public reverse-engineering of brscan-class devices.

## Disclaimer

Use on your own hardware. Firmware varies; if lease works (`--probe`) but a scan fails, open an issue with the banner and offer line (no photos required).
