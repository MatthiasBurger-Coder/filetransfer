from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, Sequence

from .errors import StreamerError


def terminate_processes(processes: Iterable[subprocess.Popen[bytes]]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def check_processes(processes: Sequence[subprocess.Popen[bytes]]) -> None:
    errors: list[str] = []
    for proc in processes:
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code:
            command = Path(proc.args[0]).name if isinstance(proc.args, list) else str(proc.args)
            errors.append(f"{command} exited with {code}: {stderr.strip()}")
    if errors:
        raise StreamerError("; ".join(errors))
