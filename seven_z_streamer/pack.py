from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import BinaryIO

from .checksum import write_bytes_with_sha256
from .constants import MANIFEST_NAME, PAYLOAD_NAME
from .container_7z import create_7z_package
from .errors import StreamerError
from .manifest import add_package, finalize_manifest, new_manifest
from .processes import check_processes, terminate_processes
from .stream_source import read_chunk, start_source_stream
from .toolchain import require_toolchain


def pack(args: argparse.Namespace) -> int:
    source = args.source.resolve()
    transfer_dir = args.transfer_dir.resolve()
    _validate_source(source)
    transfer_dir.mkdir(parents=True, exist_ok=True)

    tools = require_toolchain(args.zstd)
    manifest_package_path = transfer_dir / f"{args.prefix}-manifest.7z"
    _prepare_output_paths(transfer_dir, args.prefix, manifest_package_path, args.force)

    manifest = new_manifest(source, args.prefix, args.chunk_size, args.zstd, args.zstd_level)
    processes = []
    stream: BinaryIO | None = None
    sequence = 1
    total_payload_bytes = 0

    try:
        processes, stream = start_source_stream(source, args.zstd, args.zstd_level)
        while True:
            payload = read_chunk(stream, args.chunk_size)
            if not payload:
                break

            package_name = f"{args.prefix}-{sequence:06d}.7z"
            package_path = transfer_dir / package_name
            if package_path.exists() and not args.force:
                raise StreamerError(f"package already exists: {package_path}; use --force to replace it")
            if package_path.exists():
                package_path.unlink()

            payload_sha256 = _write_package_payload(transfer_dir, package_name, payload, tools.seven_zip, package_path)
            add_package(manifest, sequence, package_name, len(payload), payload_sha256, package_path)
            total_payload_bytes += len(payload)
            _print_package_status(package_name, len(payload), package_path.stat().st_size)
            sequence += 1

        if stream is not None:
            stream.close()
        check_processes(processes)
    except BaseException:
        terminate_processes(processes)
        raise

    finalize_manifest(manifest, total_payload_bytes)
    _write_manifest_package(transfer_dir, manifest_package_path, manifest, tools.seven_zip)
    print(f"wrote manifest package: {manifest_package_path}", file=sys.stderr)
    return 0


def _validate_source(source: Path) -> None:
    if not source.exists():
        raise StreamerError(f"source does not exist: {source}")
    if not source.is_dir():
        raise StreamerError(f"source must be a directory: {source}")


def _prepare_output_paths(transfer_dir: Path, prefix: str, manifest_package_path: Path, force: bool) -> None:
    if manifest_package_path.exists() and not force:
        raise StreamerError(f"manifest package already exists: {manifest_package_path}; use --force to replace it")
    if not force:
        return
    for stale_package in transfer_dir.glob(f"{prefix}-*.7z"):
        stale_package.unlink()


def _write_package_payload(
    transfer_dir: Path,
    package_name: str,
    payload: bytes,
    seven_zip: str,
    package_path: Path,
) -> str:
    with tempfile.TemporaryDirectory(prefix=f".{package_name}.", suffix=".work", dir=str(transfer_dir)) as work_dir:
        payload_path = Path(work_dir) / PAYLOAD_NAME
        payload_sha256 = write_bytes_with_sha256(payload_path, payload)
        create_7z_package(seven_zip, payload_path, package_path)
    return payload_sha256


def _write_manifest_package(transfer_dir: Path, manifest_package_path: Path, manifest: dict, seven_zip: str) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f".{manifest_package_path.name}.",
        suffix=".work",
        dir=str(transfer_dir),
    ) as work_dir:
        manifest_path = Path(work_dir) / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        create_7z_package(seven_zip, manifest_path, manifest_package_path, MANIFEST_NAME)


def _print_package_status(package_name: str, payload_size: int, package_size: int) -> None:
    print(
        f"packed {package_name}: payload={payload_size} package={package_size}",
        file=sys.stderr,
        flush=True,
    )
