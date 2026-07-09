from __future__ import annotations

import argparse
from pathlib import Path

from .constants import DEFAULT_CHUNK_SIZE
from .pack import pack
from .restore import restore
from .validators import parse_prefix, parse_size, parse_zstd_level
from .verify import verify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filetransfer",
        description="Stream tar/zstd data into ordered 7z transport packages and restore it.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pack_parser = subparsers.add_parser("pack", help="pack a source directory into 7z transport chunks")
    pack_parser.add_argument("source", type=Path)
    pack_parser.add_argument("transfer_dir", type=Path)
    pack_parser.add_argument("--prefix", required=True, type=parse_prefix)
    pack_parser.add_argument("--chunk-size", type=parse_size, default=parse_size(DEFAULT_CHUNK_SIZE))
    zstd_group = pack_parser.add_mutually_exclusive_group()
    zstd_group.add_argument("--zstd", dest="zstd", action="store_true", default=True)
    zstd_group.add_argument("--no-zstd", dest="zstd", action="store_false")
    pack_parser.add_argument("--zstd-level", type=parse_zstd_level, default=1)
    pack_parser.add_argument("--force", action="store_true", help="replace existing manifest/packages with same prefix")
    pack_parser.set_defaults(func=pack)

    restore_parser = subparsers.add_parser("restore", help="restore from a manifest and package directory")
    restore_parser.add_argument("manifest", type=Path)
    restore_parser.add_argument("target", type=Path)
    restore_parser.set_defaults(func=restore)

    verify_parser = subparsers.add_parser("verify", help="verify manifest and package checksums")
    verify_parser.add_argument("manifest", type=Path)
    verify_parser.set_defaults(func=verify)

    return parser
