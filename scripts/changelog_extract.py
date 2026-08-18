#!/usr/bin/env python3
"""Print the CHANGELOG section for a version (e.g. 0.2.0 or v0.2.0)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract(changelog: str, version: str) -> str:
    version = version.lstrip("v")
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        re.M | re.S,
    )
    match = pattern.search(changelog)
    if not match:
        raise SystemExit(f"no CHANGELOG section for {version}")
    return match.group(1).strip() + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("version")
    p.add_argument("--file", default="CHANGELOG.md")
    args = p.parse_args()
    text = Path(args.file).read_text(encoding="utf-8")
    sys.stdout.write(extract(text, args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
