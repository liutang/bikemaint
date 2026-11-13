"""Versioned addresses for static files (specs/020-free-placement-and-categories, FR-014).

A stylesheet or script is requested as `/static/name?v=<token>` where the token is a hash of the
file's content, so a browser fetches the new file after an upgrade instead of reusing an old copy.
Callable without FastAPI or request objects.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# (directory, name) -> ((mtime_ns, size), token): rehash only when the file changes.
_cache: dict[tuple[str, str], tuple[tuple[int, int], str]] = {}


def static_url(name: str, *, static_dir: Path = STATIC_DIR) -> str:
    """`/static/<name>?v=<token>`, or the plain address when the file does not exist."""
    path = static_dir / name
    try:
        stat = path.stat()
    except OSError:
        return f"/static/{name}"
    stamp = (stat.st_mtime_ns, stat.st_size)
    key = (str(static_dir), name)
    cached = _cache.get(key)
    if cached is None or cached[0] != stamp:
        token = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
        _cache[key] = (stamp, token)
        return f"/static/{name}?v={token}"
    return f"/static/{name}?v={cached[1]}"
