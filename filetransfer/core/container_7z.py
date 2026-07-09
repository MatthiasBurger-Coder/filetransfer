from __future__ import annotations

import subprocess
from pathlib import Path

from .constants import PAYLOAD_NAME
from ..system.errors import StreamerError


def create_7z_package(
    seven_zip: str,
    source_path: Path,
    package_path: Path,
    archive_name: str = PAYLOAD_NAME,
) -> None:
    if package_path.exists():
        raise StreamerError(f"refusing to overwrite existing package: {package_path}")

    temp_package = package_path.with_suffix(package_path.suffix + ".tmp")
    if temp_package.exists():
        temp_package.unlink()

    try:
        result = subprocess.run(
            [seven_zip, "a", "-t7z", "-mx=0", "-bd", str(temp_package), archive_name],
            cwd=str(source_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise StreamerError(
                f"7z failed for {package_path.name}: {result.stderr.strip() or result.stdout.strip()}"
            )
        temp_package.rename(package_path)
    finally:
        if temp_package.exists():
            temp_package.unlink()


def extract_payload_to_stdout(seven_zip: str, package_path: Path) -> subprocess.Popen[bytes]:
    return extract_file_to_stdout(seven_zip, package_path, PAYLOAD_NAME)


def extract_file_to_stdout(seven_zip: str, package_path: Path, archive_name: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [seven_zip, "x", "-so", "-bd", str(package_path), archive_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
