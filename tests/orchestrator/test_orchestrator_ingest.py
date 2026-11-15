"""The shown and stored form of a source error (C1, D12), against the controller's answer key
(`orchestrator_ingest_key.py`)."""

import ast
import builtins
import io
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NoReturn, cast

import orchestrator_ingest_key as key
import pytest

from credit_os import sources
from credit_os.orchestrator import ingest
from credit_os.orchestrator.ingest import (
    FolderCount,
    SourceForms,
    SourcesRefused,
    launch_problems,
    oversize,
    pin_sources,
    source_cap,
)
from credit_os.sources import PinnedFolder, SourceKind, SourcePin, pin_folder


class LaterUnreadable(sources.SourceUnreadable):
    """A subclass the class table has never heard of."""


def _raise_class(name: str) -> type[sources.SourceError]:
    found = LaterUnreadable if name == "LaterUnreadable" else getattr(sources, name)
    assert issubclass(found, sources.SourceError)
    return found


def _pin(row: key.Pin | None) -> SourcePin | None:
    if row is None:
        return None
    name, size, kind = row
    return SourcePin(name=name, sha256=key.SHA, size_bytes=size, kind=SourceKind(kind))


@pytest.mark.parametrize("name", list(key.ERRORS), ids=list(key.ERRORS))
def test_c1_d12_shown_and_stored_form(name: str) -> None:
    folder, raised, message, notes, pin, shown, detail = key.ERRORS[name]
    error = _raise_class(raised)(message)
    for note in notes:
        error.add_note(note)
    problem = SourceForms(folder).problem(error, _pin(pin))
    assert problem.shown == shown
    assert problem.detail() == detail
    for text in key.NEVER:
        assert text not in problem.shown
        assert all(text not in str(value) for value in problem.detail().values())


def test_d12_a_non_source_error_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        SourceForms(key.FOLDER).problem(cast(Any, ValueError("x")), None)


def test_d12_ingest_imports_only_sources_and_redact() -> None:
    tree = ast.parse(Path(ingest.__file__).read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    own = [m for m in modules if m.split(".")[0] == "credit_os"]
    assert "credit_os.store" not in own
    for module in own:
        assert module.startswith(("credit_os.sources", "credit_os.provider.redact")), module


# ---------------------------------------------------------------- PR 7a-2: the launch caps


def _pins(rows: list[key.Pin]) -> list[SourcePin]:
    pins = [_pin(row) for row in rows]
    return [pin for pin in pins if pin is not None]


def _fail(*_args: object, **_kwargs: object) -> NoReturn:
    pytest.fail("this must not be called")


def _write_tree(root: Path) -> None:
    for name, size, head, _counted in key.TREE:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((head + b"x" * size)[:size])


def _passing(_root: Path) -> FolderCount:
    return FolderCount(files=1, total_bytes=1)


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except NotImplementedError:
        pytest.skip("this platform cannot create symbolic links")
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("this account cannot create symbolic links")
        raise


class _Stat:
    def __init__(self, size: int) -> None:
        self.st_size = size


class _Entry:
    """A fake directory entry: a regular text file of an invented size."""

    def __init__(self, name: str, size: int) -> None:
        self.name = name
        self._size = size

    def is_symlink(self) -> bool:
        return False

    def is_junction(self) -> bool:
        return False

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return False

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return True

    def stat(self, *, follow_symlinks: bool = True) -> _Stat:
        return _Stat(self._size)


def _listing_of(sizes: list[int]) -> Any:
    def entries(_directory: Path) -> Iterator[_Entry]:
        for number, size in enumerate(sizes):
            yield _Entry(f"f{number:03}.txt", size)

    return entries


@pytest.mark.parametrize("name", list(key.COUNTS), ids=list(key.COUNTS))
def test_d16_the_launch_rule_over_a_count(name: str) -> None:
    files, total, problems = key.COUNTS[name]
    assert launch_problems(FolderCount(files=files, total_bytes=total)) == problems


@pytest.mark.parametrize("name", list(key.PIN_SETS), ids=list(key.PIN_SETS))
def test_d16_the_rule_again_over_the_pins_refuses(
    name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows, problems = key.PIN_SETS[name]
    folder = PinnedFolder(pins=tuple(_pins(rows)), skipped=())
    monkeypatch.setattr(ingest, "count_folder", _passing)
    monkeypatch.setattr(ingest, "pin_folder", lambda _root: folder)
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == problems
    assert str(refused.value) == "; ".join(problems)


@pytest.mark.parametrize(
    "name", [n for n, (_p, found) in key.PIN_SETS.items() if not found], ids=lambda n: n
)
def test_d16_pins_within_the_caps_are_returned(
    name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    folder = PinnedFolder(pins=tuple(_pins(key.PIN_SETS[name][0])), skipped=())
    monkeypatch.setattr(ingest, "count_folder", _passing)
    monkeypatch.setattr(ingest, "pin_folder", lambda _root: folder)
    found = pin_sources(tmp_path)
    assert found.pinned == folder
    assert found.root == tmp_path.resolve()


def test_d16_the_listing_refuses_files_before_any_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ingest, "_entries", _listing_of([1] * 201))
    monkeypatch.setattr(ingest, "pin_folder", _fail)
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == (key.FILES_201,)


def test_d16_the_listing_refuses_bytes_before_any_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ingest, "_entries", _listing_of([key.MAX_OTHER_BYTES] * 8 + [1]))
    monkeypatch.setattr(ingest, "pin_folder", _fail)
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == (key.BYTES_PLUS_1,)


def test_d16_the_count_is_exact_beyond_the_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ingest, "_entries", _listing_of([1] * 500))
    assert ingest.count_folder(tmp_path) == FolderCount(files=500, total_bytes=500)


@pytest.mark.parametrize("name", list(key.CAPS), ids=list(key.CAPS))
def test_d13_one_sources_cap(name: str) -> None:
    row, shown = key.CAPS[name]
    pin = _pin(row)
    assert pin is not None
    problem = oversize(pin)
    if shown is None:
        assert problem is None
        return
    assert problem is not None
    assert problem.shown == shown
    assert problem.detail() == {
        "error": "SourceTooLarge",
        "source": pin.name,
        "reason": shown.split(": ", 1)[1],
        "note": None,
    }


def test_d13_the_cap_by_kind() -> None:
    for kind in SourceKind:
        expected = key.MAX_TEXT_BYTES if kind in (SourceKind.TEXT, SourceKind.CSV) else None
        assert source_cap(kind) == (expected or key.MAX_OTHER_BYTES)


def test_d16_the_caps_are_the_rulings() -> None:
    assert ingest.MAX_FILES == key.MAX_FILES
    assert ingest.MAX_TOTAL_BYTES == key.MAX_TOTAL_BYTES
    assert ingest.MAX_TEXT_BYTES == key.MAX_TEXT_BYTES


def test_c3_the_listing_counts_what_pin_folder_pins(tmp_path: Path) -> None:
    _write_tree(tmp_path)
    files, total = key.TREE_COUNT
    assert ingest.count_folder(tmp_path) == FolderCount(files=files, total_bytes=total)
    pinned = pin_folder(tmp_path)
    assert (len(pinned.pins), sum(pin.size_bytes for pin in pinned.pins)) == (files, total)
    assert files == sum(1 for *_rest, counted in key.TREE if counted)


def test_c3_links_are_neither_counted_nor_entered(tmp_path: Path) -> None:
    _write_tree(tmp_path)
    for link, target in key.TREE_LINKS:
        _symlink(tmp_path / link, tmp_path / target)
    files, total = key.TREE_COUNT
    assert ingest.count_folder(tmp_path) == FolderCount(files=files, total_bytes=total)


def test_c3_a_fifo_is_not_counted(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("os.mkfifo is not available on this platform")
    _write_tree(tmp_path)
    os.mkfifo(tmp_path / key.TREE_FIFO)
    files, total = key.TREE_COUNT
    assert ingest.count_folder(tmp_path) == FolderCount(files=files, total_bytes=total)


def test_c3_no_file_is_opened_while_counting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_tree(tmp_path)
    monkeypatch.setattr(builtins, "open", _fail)
    monkeypatch.setattr(io, "open", _fail)
    monkeypatch.setattr(os, "open", _fail)
    files, total = key.TREE_COUNT
    assert ingest.count_folder(tmp_path) == FolderCount(files=files, total_bytes=total)


def test_c3_a_directory_name_the_walk_refuses_is_refused_with_its_class_reason(
    tmp_path: Path,
) -> None:
    if os.name == "nt":
        pytest.skip("Windows cannot hold this name")
    bad = tmp_path / "a:b"
    bad.mkdir()
    (bad / "x.txt").write_bytes(b"x")
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == (f"{key.FOLDER_LEAD}: {key.R_REFUSED}",)
    assert refused.value.__cause__ is None
    assert refused.value.__suppress_context__
    assert "a:b" not in str(refused.value)


def test_d16_a_missing_folder_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path / "missing")
    assert refused.value.problems == key.LAUNCH["missing_folder"]
    assert str(tmp_path) not in str(refused.value)


def test_d16_a_file_is_not_a_folder(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"x")
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(target)
    assert refused.value.problems == key.LAUNCH["a_file_not_a_folder"]


def test_o4_a_filesystem_root_is_refused_before_any_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ingest, "count_folder", _fail)
    monkeypatch.setattr(ingest, "pin_folder", _fail)
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(Path(Path.cwd().anchor))
    assert refused.value.problems == key.LAUNCH["filesystem_root"]


def test_c3_a_listing_that_fails_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def failing(_directory: Path) -> Iterator[_Entry]:
        raise PermissionError(13, f"denied {tmp_path}")
        yield _Entry("never", 0)

    monkeypatch.setattr(ingest, "_entries", failing)
    monkeypatch.setattr(ingest, "pin_folder", _fail)
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == key.LAUNCH["listing_fails"]
    assert refused.value.__cause__ is None
    assert str(tmp_path) not in str(refused.value)


def test_c1_pin_folder_refusing_is_the_class_reason_with_no_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def refusing(_root: Path) -> PinnedFolder:
        raise sources.SourceUnreadable(f"{key.FOLDER}/notes.txt: cannot read")

    monkeypatch.setattr(ingest, "count_folder", _passing)
    monkeypatch.setattr(ingest, "pin_folder", refusing)
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == key.LAUNCH["pin_folder_refuses"]
    assert refused.value.__cause__ is None
    assert refused.value.__suppress_context__
    assert "synthetic" not in str(refused.value)


def test_o5_a_folder_with_no_source_file_refuses_the_launch(tmp_path: Path) -> None:
    (tmp_path / "skip.json").write_bytes(b"{}")
    with pytest.raises(SourcesRefused) as refused:
        pin_sources(tmp_path)
    assert refused.value.problems == (key.NO_FILE,)


def test_d16_a_real_folder_launches(tmp_path: Path) -> None:
    _write_tree(tmp_path)
    found = pin_sources(tmp_path)
    assert found.root == tmp_path.resolve()
    assert [pin.name for pin in found.pinned.pins] == sorted(
        name for name, _size, _head, counted in key.TREE if counted
    )


def test_d16_ingest_imports_no_store() -> None:
    tree = ast.parse(Path(ingest.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any("store" in alias.name.split(".") for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert "store" not in (node.module or "").split(".")
