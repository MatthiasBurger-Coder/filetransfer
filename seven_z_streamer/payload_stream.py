from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO

from .container_7z import extract_payload_to_stdout
from .errors import StreamerError


def stream_payloads(manifest_path: Path, manifest: dict, output: BinaryIO, seven_zip: str) -> None:
    base = manifest_path.parent
    for package in manifest["packages"]:
        package_path = base / package["name"]
        proc = extract_payload_to_stdout(seven_zip, package_path)
        if proc.stdout is None:
            raise StreamerError(f"failed to read payload from {package_path.name}")

        digest = hashlib.sha256()
        total = 0
        for block in iter(lambda: proc.stdout.read(1024 * 1024), b""):
            digest.update(block)
            total += len(block)
            output.write(block)
        proc.stdout.close()
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code:
            raise StreamerError(f"7z extract failed for {package_path.name}: {stderr.strip()}")
        if total != package["payload_size"]:
            raise StreamerError(f"payload size mismatch for {package_path.name}")
        if digest.hexdigest() != package["payload_sha256"]:
            raise StreamerError(f"payload checksum mismatch for {package_path.name}")
