import json
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context

from credit_os.checks.run import check_handoff
from credit_os.handoff.document import parse

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
FILES: dict[str, dict[str, Any]] = json.loads(
    (HERE / "expected" / "fixtures.json").read_text("utf-8")
)["files"]


@pytest.mark.parametrize("name", sorted(FILES))
def test_fixture(name: str) -> None:
    entry = FILES[name]
    context = build_context({}, entry["context"])
    found = check_handoff(parse((HANDOFFS / name).read_bytes()), context)
    assert [[f.check, f.severity, f.line, f.quoted] for f in found] == entry["findings"]


def test_key_names_every_fixture() -> None:
    folders = ("synthetic-new-format", "synthetic-data-views", "tdg-2026-11-09")
    on_disk = sorted(
        path.relative_to(HANDOFFS).as_posix()
        for folder in folders
        for path in (HANDOFFS / folder).glob("*.md")
    )
    assert len(on_disk) == 26
    assert sorted(FILES) == on_disk
