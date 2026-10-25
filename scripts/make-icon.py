"""Draw `build/icon.ico` from code, so a build never depends on a drawing tool.

The mark is the app's accent rounded square with a `>_` prompt inside it. Each size is
supersampled 4x4 and averaged: a 16px chevron drawn without antialiasing is a blob.

Run: `uv run --project backend python scripts/make-icon.py`
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZES = (256, 128, 64, 48, 32, 16)
SUPERSAMPLE = 4

BACKGROUND = (0x0E, 0x7C, 0x86)  # --accent from docs/design-tokens.md
MARK = (0xF0, 0xFD, 0xFA)  # near-white with a trace of the accent tint

INSET = 0.035
RADIUS = 0.20
STROKE = 0.090

# The prompt mark in a 0..1 square: a chevron, then an underscore.
CHEVRON = ((0.30, 0.30, 0.52, 0.50), (0.52, 0.50, 0.30, 0.70))
UNDERSCORE = ((0.62, 0.70, 0.78, 0.70),)


def _inside_rounded(x: float, y: float) -> bool:
    """Is (x, y) inside the inset rounded square?"""
    low, high = INSET, 1.0 - INSET
    if not (low <= x <= high and low <= y <= high):
        return False
    nearest_x = min(max(x, low + RADIUS), high - RADIUS)
    nearest_y = min(max(y, low + RADIUS), high - RADIUS)
    dx, dy = x - nearest_x, y - nearest_y
    return dx * dx + dy * dy <= RADIUS * RADIUS


def _distance_to_segment(px: float, py: float, segment: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = segment
    vx, vy = x1 - x0, y1 - y0
    length = vx * vx + vy * vy
    along = 0.0 if length == 0 else ((px - x0) * vx + (py - y0) * vy) / length
    along = min(max(along, 0.0), 1.0)
    dx, dy = px - (x0 + along * vx), py - (y0 + along * vy)
    return (dx * dx + dy * dy) ** 0.5


def _inside_mark(x: float, y: float) -> bool:
    return any(_distance_to_segment(x, y, s) <= STROKE / 2 for s in CHEVRON + UNDERSCORE)


def render(size: int) -> bytes:
    """One size as straight-alpha RGBA, top row first."""
    pixels = bytearray(size * size * 4)
    samples = SUPERSAMPLE * SUPERSAMPLE
    step = 1.0 / (size * SUPERSAMPLE)
    for row in range(size):
        for col in range(size):
            covered = marked = 0
            for sub_y in range(SUPERSAMPLE):
                for sub_x in range(SUPERSAMPLE):
                    x = (col * SUPERSAMPLE + sub_x + 0.5) * step
                    y = (row * SUPERSAMPLE + sub_y + 0.5) * step
                    if _inside_rounded(x, y):
                        covered += 1
                        if _inside_mark(x, y):
                            marked += 1
            if not covered:
                continue
            share = marked / covered
            offset = (row * size + col) * 4
            for channel in range(3):
                pixels[offset + channel] = round(
                    BACKGROUND[channel] + (MARK[channel] - BACKGROUND[channel]) * share
                )
            pixels[offset + 3] = round(255 * covered / samples)
    return bytes(pixels)


def as_png(rgba: bytes, size: int) -> bytes:
    """A 32-bit PNG. Used for 256px, where a BMP payload would waste 256 KB."""
    raw = b"".join(b"\x00" + rgba[row * size * 4 : (row + 1) * size * 4] for row in range(size))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def as_dib(rgba: bytes, size: int) -> bytes:
    """A 32-bit bottom-up DIB with the all-zero AND mask 32-bit icons are read with."""
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    xor = bytearray()
    for row in reversed(range(size)):
        line = rgba[row * size * 4 : (row + 1) * size * 4]
        for col in range(size):
            red, green, blue, alpha = line[col * 4 : col * 4 + 4]
            xor += bytes((blue, green, red, alpha))
    mask_stride = ((size + 31) // 32) * 4
    return header + bytes(xor) + bytes(mask_stride * size)


def as_ico(images: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(images))
    directory = b""
    payload = b""
    offset = len(header) + 16 * len(images)
    for size, image in images:
        directory += struct.pack(
            "<BBBBHHII",
            size % 256,  # 256 is written as 0
            size % 256,
            0,
            0,
            1,
            32,
            len(image),
            offset,
        )
        payload += image
        offset += len(image)
    return header + directory + payload


def build() -> bytes:
    images = [
        (size, as_png(render(size), size) if size == 256 else as_dib(render(size), size))
        for size in SIZES
    ]
    return as_ico(images)


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "build" / "icon.ico"
    data = build()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(f"{target.relative_to(target.parents[2])}: {len(data)} bytes, sizes {list(SIZES)}")


if __name__ == "__main__":
    main()
