#!/usr/bin/env python3
"""CLI for DCP-J315W scanner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config
from extract import extract_objects, save_scan_set
from i18n import get_i18n
from protocol import DPI_CHOICES, ScannerError, probe, save_image, scan


def main() -> int:
    cfg = load_config()
    i18n = get_i18n(cfg.get("language", "auto"))
    default_out = str(cfg.get("outdir"))
    default_host = str(cfg.get("host"))

    p = argparse.ArgumentParser(description=i18n.t("cli_description"))
    p.add_argument("--host", default=default_host)
    p.add_argument("--dpi", type=int, default=int(cfg.get("dpi", 200)), choices=DPI_CHOICES)
    p.add_argument("--mode", choices=("gray", "color"), default=str(cfg.get("mode", "color")))
    p.add_argument("--brightness", type=int, default=int(cfg.get("brightness", 50)))
    p.add_argument("--contrast", type=int, default=int(cfg.get("contrast", 50)))
    p.add_argument("-o", "--output", default=default_out)
    p.add_argument("--split", action="store_true", default=None, help=i18n.t("cli_split"))
    p.add_argument("--no-split", action="store_true")
    p.add_argument("--lang", default=None, help="en | pl | de | auto")
    p.add_argument("--probe", action="store_true", help=i18n.t("cli_probe"))
    args = p.parse_args()

    if args.lang:
        i18n.set_language(args.lang)

    if args.probe:
        banner, offer = probe(args.host)
        print(banner)
        print(
            f"{offer.px_x}x{offer.px_y} @{offer.dpi_x}dpi  "
            f"area {offer.mm_x}x{offer.mm_y}mm  adf={offer.adf}"
        )
        return 0

    do_split = bool(cfg.get("split", True))
    if args.no_split:
        do_split = False
    elif args.split:
        do_split = True

    result = scan(
        host=args.host,
        dpi=args.dpi,
        mode=args.mode,
        brightness=args.brightness,
        contrast=args.contrast,
        idle_timeout=float(cfg.get("idle_timeout", 25)),
        max_seconds=float(cfg.get("max_seconds", 180)),
    )
    dest = Path(args.output)
    crops = extract_objects(result.image) if do_split else []
    prefix = str(cfg.get("filename_prefix") or "scan")
    if dest.suffix:
        if crops:
            paths = save_scan_set(result.image, crops, dest.parent, stamp=dest.stem, prefix=prefix)
        else:
            paths = [save_image(result.image, dest)]
    else:
        dest.mkdir(parents=True, exist_ok=True)
        paths = save_scan_set(result.image, crops, dest, prefix=prefix)

    for path in paths:
        print(f"{path}  {result.offer.raw}  {result.raw_bytes}B")
    if do_split:
        print(i18n.t("cli_objects", n=len(crops)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ScannerError) as e:
        cfg = load_config()
        print(get_i18n(cfg.get("language", "auto")).t("err_scanner", error=e), file=sys.stderr)
        raise SystemExit(1) from e
