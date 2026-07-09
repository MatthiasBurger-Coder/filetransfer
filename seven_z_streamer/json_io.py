from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, data: dict) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        Path(temp_name).rename(path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()
