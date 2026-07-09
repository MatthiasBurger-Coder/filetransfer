from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def write_bytes_with_sha256(path: Path, data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    with path.open("wb") as handle:
        handle.write(data)
    return digest.hexdigest()
