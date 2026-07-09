from __future__ import annotations

import json
import time
from pathlib import Path

from .checksum import sha256_file
from .constants import MANIFEST_VERSION, PAYLOAD_NAME
from .errors import StreamerError


def new_manifest(source: Path, prefix: str, chunk_size: int, use_zstd: bool, zstd_level: int) -> dict:
    return {
        "version": MANIFEST_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_name": source.name,
        "payload_name": PAYLOAD_NAME,
        "prefix": prefix,
        "chunk_size": chunk_size,
        "stream": {
            "format": "tar.zstd" if use_zstd else "tar",
            "zstd": bool(use_zstd),
            "zstd_level": zstd_level if use_zstd else None,
        },
        "packages": [],
    }


def add_package(manifest: dict, sequence: int, name: str, payload_size: int, payload_sha256: str, package_path: Path) -> None:
    manifest["packages"].append(
        {
            "sequence": sequence,
            "name": name,
            "payload_size": payload_size,
            "payload_sha256": payload_sha256,
            "package_size": package_path.stat().st_size,
            "package_sha256": sha256_file(package_path),
        }
    )


def finalize_manifest(manifest: dict, total_payload_bytes: int) -> None:
    manifest["package_count"] = len(manifest["packages"])
    manifest["total_payload_bytes"] = total_payload_bytes


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("version") != MANIFEST_VERSION:
        raise StreamerError(f"unsupported manifest version: {manifest.get('version')!r}")
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        raise StreamerError("manifest contains no packages")
    expected_sequences = list(range(1, len(packages) + 1))
    actual_sequences = [package.get("sequence") for package in packages]
    if actual_sequences != expected_sequences:
        raise StreamerError("manifest package sequence is not contiguous starting at 1")
    if manifest.get("package_count") not in (None, len(packages)):
        raise StreamerError("manifest package_count does not match package list")
    for package in packages:
        name = package.get("name")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".7z"):
            raise StreamerError(f"invalid package name in manifest: {name!r}")
    return manifest


def verify_packages(manifest_path: Path, manifest: dict) -> None:
    base = manifest_path.parent
    for package in manifest["packages"]:
        package_path = base / package["name"]
        if not package_path.exists():
            raise StreamerError(f"missing package: {package_path}")
        actual_size = package_path.stat().st_size
        if actual_size != package["package_size"]:
            raise StreamerError(
                f"package size mismatch for {package_path.name}: {actual_size} != {package['package_size']}"
            )
        actual_hash = sha256_file(package_path)
        if actual_hash != package["package_sha256"]:
            raise StreamerError(f"package checksum mismatch for {package_path.name}")
