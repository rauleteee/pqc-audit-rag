import io
import zipfile

import pytest

from pqc_audit_rag.sources import SourceError, clone_github_repo, save_upload


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_clone_rejects_non_https_and_unknown_hosts():
    for url in [
        "http://github.com/a/b",
        "https://evil.com/a/b",
        "ftp://x",
        "",
        "file:///etc",
    ]:
        with pytest.raises(SourceError):
            clone_github_repo(url)


def test_save_upload_single_py(tmp_path):
    dest = save_upload("keys.py", b"import rsa\n")
    files = list(dest.rglob("*.py"))
    assert len(files) == 1
    assert files[0].read_text() == "import rsa\n"


def test_save_upload_zip_extracts(tmp_path):
    data = _zip({"proj/a.py": b"x=1\n", "proj/sub/b.py": b"y=2\n"})
    dest = save_upload("proj.zip", data)
    got = sorted(p.name for p in dest.rglob("*.py"))
    assert got == ["a.py", "b.py"]


def test_save_upload_rejects_other_extensions():
    with pytest.raises(SourceError):
        save_upload("notes.txt", b"hi")


def test_zip_slip_is_blocked():
    # An entry trying to escape the extraction dir must be refused.
    data = _zip({"../evil.py": b"pwned\n"})
    with pytest.raises(SourceError):
        save_upload("evil.zip", data)


def test_bad_zip_raises():
    with pytest.raises(SourceError):
        save_upload("broken.zip", b"not a zip")
