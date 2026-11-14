"""Each committed answer-key script reproduces its committed JSON key."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

EXPECTED = Path(__file__).with_name("expected")
SCRIPTS = ("make_pr2", "make_pr3", "make_pr4a", "make_pr4b", "make_pr5")  # pr2 to pr5 keys


def load_script(name: str) -> ModuleType:
    """Import an answer-key script by path, without touching sys.path or the disk."""
    path = EXPECTED / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same(got: Any, want: Any, path: str = "$") -> None:
    """Fail with the path of the first difference: type, key order, length or value."""
    if type(got) is not type(want):
        raise AssertionError(f"{path}: type {type(got).__name__} != {type(want).__name__}")
    if isinstance(want, dict):
        if list(got) != list(want):
            raise AssertionError(f"{path}: keys {list(got)} != {list(want)}")
        for key in want:
            same(got[key], want[key], f"{path}.{key}")
    elif isinstance(want, list):
        if len(got) != len(want):
            raise AssertionError(f"{path}: length {len(got)} != {len(want)}")
        for index, item in enumerate(want):
            same(got[index], item, f"{path}[{index}]")
    elif got != want:
        raise AssertionError(f"{path}: {got!r} != {want!r}")


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_reproduces_its_key(name: str) -> None:
    number = name.removeprefix("make_pr")
    got = json.loads(load_script(name).render())
    want = json.loads((EXPECTED / f"pr{number}.json").read_text("utf-8"))
    same(got, want)


@pytest.mark.parametrize(
    ("got", "want"),
    [
        ({"a": 1}, {"a": 1.0}),
        ({"a": True}, {"a": 1}),
        ({"a": 1, "b": 2}, {"b": 2, "a": 1}),
        ([1, 2], [1, 2, 3]),
        ("1", 1),
    ],
)
def test_walker_refuses(got: Any, want: Any) -> None:
    with pytest.raises(AssertionError):
        same(got, want)


def test_walker_reports_deep_path() -> None:
    got = {"a": {"b": [{"c": 1}]}}
    want = {"a": {"b": [{"c": 2}]}}
    with pytest.raises(AssertionError, match=r"^\$\.a\.b\[0\]\.c: 1 != 2$"):
        same(got, want)


def test_walker_accepts_equal_and_empty() -> None:
    nested = {"a": [1, "x", None, {"b": [True, 2.5]}], "c": {}}
    same(nested, {"a": [1, "x", None, {"b": [True, 2.5]}], "c": {}})
    same({}, {})
    same([], [])


@pytest.mark.parametrize("name", SCRIPTS)
def test_render_writes_no_file(name: str) -> None:
    before = sorted(p.name for p in EXPECTED.iterdir())
    load_script(name).render()
    assert sorted(p.name for p in EXPECTED.iterdir()) == before
