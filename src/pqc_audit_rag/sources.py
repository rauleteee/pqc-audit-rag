"""Fetch a scan target from a public GitHub URL or an uploaded .py/.zip.

The hosted UI runs on a server with no access to the visitor's machine, so to
scan their own project they either point at a public repo or upload it. Both
paths are hardened:

- **git clone**: only ``https`` URLs on an allowlisted host, shallow, no auth
  prompt, with a timeout.
- **zip**: entries with absolute or ``..`` paths are rejected (zip-slip), with
  caps on file count and uncompressed size.

Everything lands in a fresh temp directory (the caller scans it, then removes it).
"""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "codeberg.org"}
MAX_FILES = 5000
MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 200 MB uncompressed


class SourceError(Exception):
    """A user-facing problem fetching the scan target (bad URL, bad zip…)."""


def _tmpdir(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def clone_github_repo(url: str, *, timeout: int = 60) -> Path:
    """Shallow-clone a public repo into a temp dir; return its path."""
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in ALLOWED_GIT_HOSTS:
        raise SourceError(
            "Enter an https URL to a public repo on one of: "
            + ", ".join(sorted(ALLOWED_GIT_HOSTS))
        )
    dest = _tmpdir("pqc_repo_")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
            check=True,
            capture_output=True,
            timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError as exc:  # git missing
        raise SourceError("git is not available on this server.") from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError("Cloning timed out — is the repo public and small?") from exc
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or b"").decode(errors="replace").strip().splitlines()
        raise SourceError(
            "Clone failed: " + (tail[-1] if tail else "check the URL is public.")
        ) from exc
    return dest


def save_upload(filename: str, data: bytes) -> Path:
    """Store an uploaded ``.py`` (as-is) or ``.zip`` (safely extracted); return dir."""
    name = Path(filename or "").name
    lower = name.lower()
    dest = _tmpdir("pqc_upload_")
    if lower.endswith(".py"):
        (dest / (name or "uploaded.py")).write_bytes(data)
        return dest
    if lower.endswith(".zip"):
        _safe_extract_zip(data, dest)
        return dest
    raise SourceError("Upload a .py file or a .zip of your project.")


def _safe_extract_zip(data: bytes, dest: Path) -> None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SourceError("That is not a valid .zip file.") from exc
    root = dest.resolve()
    total = 0
    count = 0
    for info in archive.infolist():
        if info.is_dir():
            continue
        count += 1
        total += info.file_size
        if count > MAX_FILES or total > MAX_TOTAL_BYTES:
            raise SourceError("Archive too large to scan here.")
        target = (root / info.filename).resolve()
        if target != root and not str(target).startswith(str(root) + os.sep):
            raise SourceError("Refused a zip entry pointing outside the folder.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, open(target, "wb") as out:
            out.write(src.read())
