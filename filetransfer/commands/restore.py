from __future__ import annotations

import argparse
import subprocess
import sys

from ..core.manifest import load_manifest, verify_packages
from ..core.payload_stream import stream_payloads
from ..system.errors import StreamerError
from ..system.processes import terminate_processes
from ..system.toolchain import require_toolchain


def restore(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.resolve()
    target = args.target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(manifest_path)
    tools = require_toolchain(bool(manifest["stream"]["zstd"]))

    verify_packages(manifest_path, manifest)

    tar_cmd = [tools.tar, "-C", str(target), "-xf", "-"]
    if manifest["stream"]["zstd"]:
        _restore_zstd_stream(manifest_path, manifest, tools, tar_cmd)
    else:
        _restore_tar_stream(manifest_path, manifest, tools, tar_cmd)

    print(f"restored into: {target}", file=sys.stderr)
    return 0


def _restore_zstd_stream(manifest_path, manifest: dict, tools, tar_cmd: list[str]) -> None:
    zstd_proc = subprocess.Popen(
        [tools.zstd or "zstd", "-d", "-c"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if zstd_proc.stdin is None or zstd_proc.stdout is None:
        raise StreamerError("failed to start zstd restore pipeline")
    tar_proc = subprocess.Popen(
        tar_cmd,
        stdin=zstd_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    zstd_proc.stdout.close()
    try:
        stream_payloads(manifest_path, manifest, zstd_proc.stdin, tools.seven_zip)
        zstd_proc.stdin.close()
        zstd_stderr = zstd_proc.stderr.read().decode(errors="replace") if zstd_proc.stderr else ""
        tar_stderr = tar_proc.stderr.read().decode(errors="replace") if tar_proc.stderr else ""
        zstd_code = zstd_proc.wait()
        tar_code = tar_proc.wait()
    except BaseException:
        terminate_processes([zstd_proc, tar_proc])
        raise
    if zstd_code:
        raise StreamerError(f"zstd restore failed: {zstd_stderr.strip()}")
    if tar_code:
        raise StreamerError(f"tar restore failed: {tar_stderr.strip()}")


def _restore_tar_stream(manifest_path, manifest: dict, tools, tar_cmd: list[str]) -> None:
    tar_proc = subprocess.Popen(
        tar_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if tar_proc.stdin is None:
        raise StreamerError("failed to start tar restore pipeline")
    try:
        stream_payloads(manifest_path, manifest, tar_proc.stdin, tools.seven_zip)
        tar_proc.stdin.close()
        tar_stderr = tar_proc.stderr.read().decode(errors="replace") if tar_proc.stderr else ""
        tar_code = tar_proc.wait()
    except BaseException:
        terminate_processes([tar_proc])
        raise
    if tar_code:
        raise StreamerError(f"tar restore failed: {tar_stderr.strip()}")
