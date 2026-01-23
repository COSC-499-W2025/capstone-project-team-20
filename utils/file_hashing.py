from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def compute_file_hash(path: Path, chunk_size: int = 8192) -> Optional[str]:
    """Return SHA-256 hash for a file path, or None if unreadable."""
    try:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None