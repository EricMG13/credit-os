import hashlib
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"


def test_every_listed_checksum_matches_the_file_bytes() -> None:
    entries = (FIXTURES / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert entries
    for entry in entries:
        digest, relative = entry.split()
        assert hashlib.sha256((FIXTURES / relative).read_bytes()).hexdigest() == digest, relative


def test_listed_paths_are_exactly_the_markdown_fixtures() -> None:
    entries = (FIXTURES / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    listed = {entry.split()[1] for entry in entries}
    on_disk = {path.relative_to(FIXTURES).as_posix() for path in FIXTURES.glob("*/*.md")}
    assert listed == on_disk
    assert len(on_disk) == 27
