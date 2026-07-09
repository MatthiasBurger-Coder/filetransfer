from __future__ import annotations

import argparse
from pathlib import Path


def parse_size(value: str) -> int:
    text = value.strip()
    if not text:
        raise argparse.ArgumentTypeError("chunk size must not be empty")

    suffixes = {
        "": 1,
        "b": 1,
        "k": 1000,
        "kb": 1000,
        "m": 1000**2,
        "mb": 1000**2,
        "g": 1000**3,
        "gb": 1000**3,
        "ki": 1024,
        "kib": 1024,
        "mi": 1024**2,
        "mib": 1024**2,
        "gi": 1024**3,
        "gib": 1024**3,
    }

    number_part = text
    suffix = ""
    for index, char in enumerate(text):
        if not (char.isdigit() or char == "."):
            number_part = text[:index]
            suffix = text[index:].lower()
            break

    try:
        number = float(number_part)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid size: {value!r}") from exc

    multiplier = suffixes.get(suffix)
    if multiplier is None:
        raise argparse.ArgumentTypeError(
            f"invalid size suffix {suffix!r}; use B, K, M, G, KiB, MiB, or GiB"
        )

    size = int(number * multiplier)
    if size <= 0:
        raise argparse.ArgumentTypeError("chunk size must be greater than zero")
    return size


def parse_prefix(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("prefix must not be empty")
    if Path(value).name != value or "/" in value or "\\" in value:
        raise argparse.ArgumentTypeError("prefix must be a file-name prefix without path separators")
    return value


def parse_zstd_level(value: str) -> int:
    try:
        level = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("zstd level must be an integer") from exc
    if not 1 <= level <= 19:
        raise argparse.ArgumentTypeError("zstd level must be between 1 and 19")
    return level
