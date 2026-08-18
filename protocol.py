#!/usr/bin/env python3
"""Brother DCP-J315W network scan protocol (TCP 54921 / brscan3-class)."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

DEFAULT_HOST = "192.168.0.80"
PORT = 54921
END = 0x80
DPI_CHOICES = (100, 150, 200, 300)


class ScannerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Offer:
    dpi_x: int
    dpi_y: int
    adf: int
    mm_x: int
    px_x: int
    mm_y: int
    px_y: int
    raw: str

    @classmethod
    def parse(cls, text: str) -> Offer:
        parts = text.split(",")
        if len(parts) < 7:
            raise ScannerError(f"bad offer: {text!r}")
        return cls(
            dpi_x=int(parts[0]),
            dpi_y=int(parts[1]),
            adf=int(parts[2]),
            mm_x=int(parts[3]),
            px_x=int(parts[4]),
            mm_y=int(parts[5]),
            px_y=int(parts[6]),
            raw=text,
        )

    @property
    def adf_enabled(self) -> bool:
        return self.adf != 2


@dataclass
class ScanResult:
    kind: str
    offer: Offer
    image: Image.Image
    raw_bytes: int


def recvn(sock: socket.socket, n: int, timeout: float) -> bytes:
    sock.settimeout(timeout)
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def read_banner(sock: socket.socket) -> bytes:
    sock.settimeout(5)
    buf = bytearray()
    while b"\n" not in buf and len(buf) < 64:
        chunk = sock.recv(64)
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def read_offer(sock: socket.socket) -> Offer:
    hdr = recvn(sock, 3, 5)
    if len(hdr) < 3:
        raise ScannerError(f"short offer header: {hdr!r}")
    body = recvn(sock, hdr[1], 5)
    return Offer.parse(body.decode("ascii", "replace"))


def _complete(data: bytes) -> bool:
    """True when all frames are whole and a 0x80 terminator follows."""
    i = 0
    frames = 0
    n = len(data)
    while i + 3 <= n:
        length = int.from_bytes(data[i + 1 : i + 3], "little")
        if length == 0:
            return False
        nxt = i + 3 + length
        if nxt > n:
            return False
        i = nxt
        frames += 1
    return frames > 0 and data[i:] == bytes([END])


def decode_jpeg(data: bytes) -> Image.Image:
    payload = b"".join(parse_frames(data))
    jpeg = extract_jpeg(payload)
    image = Image.open(BytesIO(jpeg))
    image.load()
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def collect(
    sock: socket.socket,
    idle_timeout: float = 20.0,
    max_seconds: float = 180.0,
    first_byte_timeout: float = 45.0,
) -> bytes:
    out = bytearray()
    deadline = time.time() + max_seconds
    sock.settimeout(first_byte_timeout)
    while time.time() < deadline:
        try:
            chunk = sock.recv(65536)
        except TimeoutError:
            if _complete(out):
                break
            if out:
                raise ScannerError(
                    f"scan truncated after {len(out)} B (idle {idle_timeout:.0f}s)"
                ) from None
            raise ScannerError("no data from scanner (timeout)") from None
        if not chunk:
            break
        out.extend(chunk)
        if _complete(out):
            sock.settimeout(0.4)
            try:
                extra = sock.recv(8192)
                if extra:
                    out.extend(extra)
            except TimeoutError:
                pass
            break
        sock.settimeout(idle_timeout)
    if not out:
        raise ScannerError("empty scan")
    return bytes(out)


def parse_frames(data: bytes) -> list[bytes]:
    if data.endswith(bytes([END])):
        data = data[:-1]
    frames: list[bytes] = []
    i = 0
    while i + 3 <= len(data):
        length = int.from_bytes(data[i + 1 : i + 3], "little")
        i += 3
        if length == 0:
            break
        if i + length > len(data):
            frames.append(data[i:])
            break
        frames.append(data[i : i + length])
        i += length
    return frames


def decode_gray(data: bytes) -> Image.Image:
    rows = parse_frames(data)
    if not rows:
        raise ScannerError("no image rows")
    width = max(len(r) for r in rows)
    pixels = b"".join(r.ljust(width, b"\xff") for r in rows)
    return Image.frombytes("L", (width, len(rows)), pixels)


def extract_jpeg(data: bytes) -> bytes:
    soi = data.find(b"\xff\xd8")
    eoi = data.rfind(b"\xff\xd9")
    if soi < 0 or eoi < soi:
        raise ScannerError("JPEG markers not found")
    return data[soi : eoi + 2]


def probe(host: str = DEFAULT_HOST) -> tuple[str, Offer]:
    with socket.create_connection((host, PORT), timeout=8) as sock:
        banner = read_banner(sock)
        if not banner.startswith(b"+OK 200"):
            raise ScannerError(f"scanner not ready: {banner!r}")
        sock.sendall(b"\x1bI\nR=100,100\nM=GRAY64\n" + bytes([END]))
        offer = read_offer(sock)
    return banner.decode("ascii", "replace").strip(), offer


def scan(
    host: str = DEFAULT_HOST,
    dpi: int = 200,
    mode: str = "color",
    brightness: int = 50,
    contrast: int = 50,
    idle_timeout: float = 25.0,
    max_seconds: float = 180.0,
) -> ScanResult:
    if dpi not in DPI_CHOICES:
        raise ScannerError(f"unsupported dpi: {dpi}")
    if mode not in ("color", "gray"):
        raise ScannerError(f"unsupported mode: {mode}")
    brightness = max(0, min(100, int(brightness)))
    contrast = max(0, min(100, int(contrast)))

    color = mode == "color"
    m = "CGRAY" if color else "GRAY64"
    c = "JPEG" if color else "NONE"

    with socket.create_connection((host, PORT), timeout=8) as sock:
        banner = read_banner(sock)
        if not banner.startswith(b"+OK 200"):
            raise ScannerError(f"scanner not ready: {banner!r}")

        sock.sendall(f"\x1bI\nR={dpi},{dpi}\nM={m}\n".encode() + bytes([END]))
        offer = read_offer(sock)

        req = (
            f"\x1bX\nR={offer.dpi_x},{offer.dpi_y}\nM={m}\nC={c}\n"
            f"J=MID\nB={brightness}\nN={contrast}\n"
            f"A=0,0,{offer.px_x},{offer.px_y}\n"
        ).encode() + bytes([END])
        sock.sendall(req)
        raw = collect(sock, idle_timeout=idle_timeout, max_seconds=max_seconds)

    if color:
        image = decode_jpeg(raw)
        kind = "jpeg"
    else:
        image = decode_gray(raw)
        kind = "gray"
    return ScanResult(kind=kind, offer=offer, image=image, raw_bytes=len(raw))


def save_image(image: Image.Image, dest, fmt: str | None = None):
    from pathlib import Path

    dest = Path(dest)
    suffix = dest.suffix.lower()
    fmt = (fmt or "").upper() or {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".pdf": "PDF",
        ".tif": "TIFF",
        ".tiff": "TIFF",
    }.get(suffix, "PNG")

    img = image
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if fmt == "PDF":
        rgb = img.convert("RGB")
        rgb.save(dest, "PDF", resolution=200.0)
        return dest
    extra = {}
    if fmt == "JPEG":
        extra = {"quality": 92, "optimize": True}
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, fmt, **extra)
    return dest
