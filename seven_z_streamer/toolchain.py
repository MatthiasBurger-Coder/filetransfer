from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Sequence

from .errors import StreamerError


@dataclass(frozen=True)
class Toolchain:
    tar: str
    seven_zip: str
    zstd: str | None


def find_tool(candidates: Sequence[str]) -> str | None:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def require_toolchain(use_zstd: bool) -> Toolchain:
    tar = find_tool(["tar"])
    seven_zip = find_tool(["7z", "7zz", "7za"])
    zstd = find_tool(["zstd"])

    missing: list[str] = []
    if tar is None:
        missing.append("tar")
    if seven_zip is None:
        missing.append("7z/7zz/7za")
    if use_zstd and zstd is None:
        missing.append("zstd")
    if missing:
        raise StreamerError("missing required tool(s): " + ", ".join(missing))

    return Toolchain(tar=tar, seven_zip=seven_zip, zstd=zstd)
