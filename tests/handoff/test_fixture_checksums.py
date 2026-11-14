import hashlib
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"
EXEMPT = {"SHA256SUMS", ".gitattributes"}


def problems(folder: Path) -> list[str]:
    """Mismatched, unlisted and missing files of a fixtures folder, as readable strings."""
    entries = (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    found: list[str] = []
    listed: set[str] = set()
    for entry in entries:
        digest, relative = entry.split()
        listed.add(relative)
        target = folder / relative
        if not target.is_file():
            found.append(f"missing: {relative}")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            found.append(f"mismatch: {relative}")
    on_disk = {
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() and path.relative_to(folder).as_posix() not in EXEMPT
    }
    found.extend(f"unlisted: {name}" for name in sorted(on_disk - listed))
    return found


def _folder(tmp_path: Path, listed_bytes: bytes, actual_bytes: bytes) -> Path:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.md").write_bytes(actual_bytes)
    (tmp_path / "sub" / "extra.txt").write_bytes(b"x")
    (tmp_path / ".gitattributes").write_bytes(b"* -text\n")
    digest = hashlib.sha256(listed_bytes).hexdigest()
    (tmp_path / "SHA256SUMS").write_text(f"{digest}  sub/a.md\n", encoding="utf-8")
    return tmp_path


def test_an_unlisted_file_at_any_depth_and_extension_is_reported(tmp_path: Path) -> None:
    folder = _folder(tmp_path, b"same", b"same")
    assert problems(folder) == ["unlisted: sub/extra.txt"]


def test_a_listed_file_with_different_bytes_is_reported(tmp_path: Path) -> None:
    folder = _folder(tmp_path, b"listed", b"changed")
    assert "mismatch: sub/a.md" in problems(folder)


def test_the_real_fixtures_are_all_listed_and_match() -> None:
    entries = (FIXTURES / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(entries) == 27
    assert problems(FIXTURES) == []
