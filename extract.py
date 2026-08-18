#!/usr/bin/env python3
"""Split a flatbed scan into separate photos (white glass, multiple prints)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Crop:
    image: Image.Image
    box: tuple[int, int, int, int]  # x, y, w, h in source pixels
    area: int


def _order_points(pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype=np.float32,
    )


def _warp(bgr: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts)
    tl, tr, br, bl = rect
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    width = max(width, 8)
    height = max(height, 8)
    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(bgr, matrix, (width, height))


def _mask(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # White lid is ~251. Keep threshold below the gap-merge point (~248).
    _, mask = cv2.threshold(blur, 240, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def extract_objects(
    image: Image.Image,
    min_area_ratio: float = 0.03,
    max_area_ratio: float = 0.85,
    pad: int = 4,
) -> list[Crop]:
    rgb = np.array(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask = _mask(gray)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    page = gray.shape[0] * gray.shape[1]
    lo, hi = page * min_area_ratio, page * max_area_ratio
    found: list[Crop] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < lo or area > hi:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 40 or h < 40:
            continue
        rect = cv2.minAreaRect(contour)
        rw, rh = rect[1]
        if rw < 40 or rh < 40:
            continue
        angle = rect[2]
        aligned = abs(angle) <= 3 or abs(abs(angle) - 90) <= 3
        if aligned:
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(bgr.shape[1], x + w + pad)
            y1 = min(bgr.shape[0], y + h + pad)
            crop_bgr = bgr[y0:y1, x0:x1]
        else:
            crop_bgr = _warp(bgr, cv2.boxPoints(rect))
            if pad:
                crop_bgr = crop_bgr[
                    pad : max(pad + 1, crop_bgr.shape[0] - pad),
                    pad : max(pad + 1, crop_bgr.shape[1] - pad),
                ]
        if crop_bgr.size == 0:
            continue
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        if float(np.mean(crop_gray)) > 250:
            continue
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(crop_rgb)
        if image.mode == "L":
            pil = pil.convert("L")
        found.append(Crop(image=pil, box=(int(x), int(y), int(w), int(h)), area=int(area)))

    found.sort(key=lambda c: (c.box[1] // 80, c.box[0]))
    return found


def stamp_now() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d-%H%M%S")


def save_scan_set(
    full_image: Image.Image,
    crops: list[Crop],
    folder,
    stamp: str | None = None,
    prefix: str = "scan",
):
    from pathlib import Path

    from protocol import save_image

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = stamp or stamp_now()
    ext = ".jpg" if full_image.mode == "RGB" else ".png"
    paths = []
    if crops:
        for i, crop in enumerate(crops, 1):
            dest = folder / f"{prefix}-{stamp}-{i:02d}{ext}"
            paths.append(save_image(crop.image, dest))
    else:
        dest = folder / f"{prefix}-{stamp}{ext}"
        paths.append(save_image(full_image, dest))
    return paths
