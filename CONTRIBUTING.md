# Contributing

Thanks for helping with j315scan.

## Dev setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -q
```

## Guidelines

- Keep the protocol layer free of UI strings.
- New UI text goes in `locales/en.json` first, then `pl.json` and `de.json`.
- Do not commit `settings.json`, `config.yaml`, `.venv/`, or scan images.
- Prefer small, tested changes. Add a `CHANGELOG.md` entry under `Unreleased` or the next version.

## Protocol changes

If you have another Brother that speaks 54921, include `--probe` output (banner + offer) in the PR. Do not attach personal scans.
