from __future__ import annotations

import subprocess
from pathlib import Path
from typing import BinaryIO

from ..system.errors import StreamerError
from ..system.toolchain import require_toolchain


def source_tar_args(source: Path, tar: str) -> list[str]:
    return [tar, "-C", str(source.parent), "-cf", "-", source.name]


def start_source_stream(
    source: Path,
    use_zstd: bool,
    compression_level: int,
) -> tuple[list[subprocess.Popen[bytes]], BinaryIO]:
    tools = require_toolchain(use_zstd)
    tar_proc = subprocess.Popen(
        source_tar_args(source, tools.tar),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if tar_proc.stdout is None:
        raise StreamerError("failed to open tar stdout")

    processes: list[subprocess.Popen[bytes]] = [tar_proc]
    stream: BinaryIO = tar_proc.stdout

    if use_zstd:
        zstd_proc = subprocess.Popen(
            [tools.zstd or "zstd", f"-{compression_level}", "-T0", "-c"],
            stdin=tar_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tar_proc.stdout.close()
        if zstd_proc.stdout is None:
            raise StreamerError("failed to open zstd stdout")
        processes.append(zstd_proc)
        stream = zstd_proc.stdout

    return processes, stream


def read_chunk(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        block = stream.read(min(1024 * 1024, remaining))
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
    return b"".join(chunks)
