from __future__ import annotations

import argparse
import sys

from ..core.manifest import load_manifest, verify_packages
from ..system.toolchain import require_toolchain


def verify(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    require_toolchain(bool(manifest["stream"]["zstd"]))
    verify_packages(manifest_path, manifest)
    print(f"verified {len(manifest['packages'])} package(s)", file=sys.stderr)
    return 0
