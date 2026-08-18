# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Fixed
- Offline scanner no longer crashes the GUI (Python 3.14 except-variable lambdas + shadowed `Tk._root`)

## [0.2.0] — 2026-08-18

### Added
- English / Polish / German UI (`language: auto|en|pl|de`)
- `config.yaml` + `config.example.yaml` and documented load order
- User settings in `./settings.json` or `~/.config/j315scan/settings.json`
- Packaging files for a public GitHub repo (LICENSE, CONTRIBUTING, CI, issue templates)
- GitHub Actions: lint (Ruff), test on Python 3.10–3.13, sdist/wheel build, tag release

### Changed
- Default save folder is `~/Pictures` (no nested subfolder)
- Default file prefix is `scan-`
- Protocol error messages are English; UI strings go through i18n

## [0.1.0] — 2026-08-18

### Added
- Network scan client for Brother DCP-J315W (TCP 54921)
- Tk GUI and CLI
- Color JPEG and grayscale raw decode
- Object split for multiple photos on the flatbed
- `run.sh` / local venv
