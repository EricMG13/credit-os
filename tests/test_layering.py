import ast
from pathlib import Path

import pytest

import credit_os

DYNAMIC_IMPORTERS = ("import_module", "__import__")


def _constant_text(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_argument(node: ast.Call, position: int, keyword: str) -> ast.expr | None:
    if len(node.args) > position:
        return node.args[position]
    return next((kw.value for kw in node.keywords if kw.arg == keyword), None)


def _dynamic_target(node: ast.Call, pkg_parts: list[str]) -> str | None | bool:
    """Module named by a dynamic import call: a dotted name, None when it is not such a
    call, False when the name cannot be resolved statically."""
    func = node.func
    called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    if called not in DYNAMIC_IMPORTERS:
        return None
    name = _constant_text(_call_argument(node, 0, "name"))
    if name is None:
        return False
    if not name.startswith("."):
        return name
    anchor = _call_argument(node, 1, "package")
    if isinstance(anchor, ast.Name) and anchor.id == "__package__":
        anchor_parts = pkg_parts
    elif (text := _constant_text(anchor)) is not None:
        anchor_parts = text.split(".")
    else:
        return False
    level = len(name) - len(name.lstrip("."))
    base = anchor_parts[: len(anchor_parts) - (level - 1)]
    return ".".join([*base, *([name.lstrip(".")] if name.lstrip(".") else [])])


def _static_targets(node: ast.Import | ast.ImportFrom, pkg_parts: list[str]) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level:
        base = pkg_parts[: len(pkg_parts) - (node.level - 1)]
        module = ".".join([*base, *([node.module] if node.module else [])])
    else:
        module = node.module or ""
    return [module, *(f"{module}.{alias.name}" for alias in node.names)] if module else []


def _offending_layers(
    targets: list[str],
    package: str,
    layers: tuple[str, ...],
    layer: str,
    isolated: frozenset[str],
) -> list[str]:
    offending: set[str] = set()
    for target in targets:
        parts = target.split(".")
        if len(parts) < 2 or parts[0] != package or parts[1] not in layers:
            continue
        other = parts[1]
        if other == layer:
            continue
        if layer in isolated or other in isolated or layers.index(other) > layers.index(layer):
            offending.add(other)
    return sorted(offending)


def _file_violations(
    path: Path,
    label: str,
    pkg_parts: list[str],
    layers: tuple[str, ...],
    layer: str,
    isolated: frozenset[str],
) -> list[str]:
    out: list[str] = []
    package = pkg_parts[0]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
        if isinstance(node, ast.Import | ast.ImportFrom):
            targets = _static_targets(node, pkg_parts)
        elif isinstance(node, ast.Call):
            dynamic = _dynamic_target(node, pkg_parts)
            if dynamic is None:
                continue
            if dynamic is False:
                out.append(
                    f"{path}:{node.lineno} {label} dynamic import with a non-literal "
                    "module name cannot be checked"
                )
                continue
            targets = [str(dynamic)]
        else:
            continue
        out.extend(
            f"{path}:{node.lineno} {label} imports {name}"
            for name in _offending_layers(targets, package, layers, layer, isolated)
        )
    return out


def violations(
    root: Path, layers: tuple[str, ...], isolated: frozenset[str] = frozenset()
) -> list[str]:
    out: list[str] = []
    package = root.name
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and entry.name not in layers and entry.name != "__pycache__":
            out.append(f"{entry}: sub-package {entry.name} is not in the layer list")
    for entry in sorted(root.rglob("*")):
        if entry.is_symlink() and entry.is_dir():
            out.append(f"{entry}: symlinked directory is not walked, replace it with a real one")
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if len(rel.parts) < 2:
            if rel.name == "__init__.py":
                out.extend(
                    _file_violations(path, "package root", [package], ("", *layers), "", isolated)
                )
            else:
                out.append(
                    f"{path}: module {rel.name} sits in the package root, outside every layer"
                )
            continue
        layer = rel.parts[0]
        if layer not in layers:
            continue
        pkg_parts = [package, *rel.parts[:-1]]
        out.extend(_file_violations(path, layer, pkg_parts, layers, layer, isolated))
    return out


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "credit_os"
    for name in credit_os.LAYERS:
        (root / name).mkdir(parents=True)
        (root / name / "__init__.py").write_text("")
    (root / "__init__.py").write_text("")
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return root


def test_absolute_later_import(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"handoff/a.py": "from credit_os.delivery import x\n"})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "handoff" in found[0] and "delivery" in found[0]


def test_relative_later_import(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"handoff/a.py": "from ..delivery import x\n"})
    assert len(violations(root, credit_os.LAYERS)) == 1


def test_earlier_import_allowed(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"delivery/a.py": "import credit_os.handoff.doc\n"})
    assert violations(root, credit_os.LAYERS) == []


def test_unlisted_subpackage(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"extras/__init__.py": ""})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "extras" in found[0]


def test_repo_has_no_violations() -> None:
    assert violations(Path("src/credit_os"), credit_os.LAYERS, credit_os.ISOLATED) == []


def test_relative_bare_package_import_of_later_layer(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"handoff/a.py": "from .. import delivery\n"})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "handoff" in found[0] and "delivery" in found[0]


def test_absolute_bare_package_import_of_later_layer(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"handoff/a.py": "from credit_os import delivery\n"})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "handoff" in found[0] and "delivery" in found[0]


def test_bare_package_import_of_earlier_layer_allowed(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"delivery/a.py": "from credit_os import handoff\n"})
    assert violations(root, credit_os.LAYERS) == []


def test_nested_relative_import_resolves_from_its_own_directory(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "handoff/sub/a.py": "from ...delivery import x\n",
            "handoff/sub/b.py": "from ... import delivery\n",
            "handoff/sub/c.py": "from .. import sources\n",
        },
    )
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 2
    assert all("handoff" in item and "delivery" in item for item in found)


def test_root_module_other_than_init_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"extras.py": "x = 1\n"})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "extras.py" in found[0]


def test_dynamic_import_spellings_of_a_later_layer(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "orchestrator/a.py": "import importlib\nimportlib.import_module('credit_os.delivery')\n",
            "orchestrator/b.py": "from importlib import import_module\nimport_module('credit_os.delivery.x')\n",
            "orchestrator/c.py": "import importlib\nimportlib.import_module('..delivery', __package__)\n",
            "orchestrator/d.py": "__import__('credit_os.delivery')\n",
            "orchestrator/e.py": "import importlib\nimportlib.import_module('..delivery', package='credit_os.orchestrator')\n",
            "orchestrator/f.py": "import importlib\nimportlib.import_module(name='credit_os.delivery')\n",
        },
    )
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 6, found
    assert all("orchestrator" in item and "delivery" in item for item in found)


def test_dynamic_import_of_an_earlier_layer_allowed(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {"delivery/a.py": "import importlib\nimportlib.import_module('credit_os.handoff')\n"},
    )
    assert violations(root, credit_os.LAYERS) == []


def test_non_literal_dynamic_import_is_reported_as_its_own_kind(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "handoff/a.py": "import importlib\nname = 'x'\nimportlib.import_module(name)\n",
            "handoff/b.py": "__import__(f'credit_os.{1}')\n",
        },
    )
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 2
    assert all("dynamic import" in item and "cannot be checked" in item for item in found)
    assert not any("imports" in item for item in found)


def test_symlinked_directory_is_reported(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.py").write_text("from credit_os.delivery import x\n")
    root = _tree(tmp_path, {})
    try:
        (root / "handoff" / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "symlink" in found[0]


def test_root_init_importing_a_layer_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"__init__.py": "from credit_os import handoff\n"})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "handoff" in found[0]


def test_root_init_importing_nothing_from_layers_allowed(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"__init__.py": "from credit_os import LAYERS\n"})
    assert violations(root, credit_os.LAYERS) == []


def test_pycache_directory_is_not_a_sub_package(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"__pycache__/x.pyc": ""})
    assert violations(root, credit_os.LAYERS) == []


def test_files_in_an_unlisted_sub_package_only_report_the_sub_package(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"extras/a.py": "from credit_os.delivery import x\n"})
    found = violations(root, credit_os.LAYERS)
    assert len(found) == 1
    assert "sub-package extras" in found[0]


def _isolated(root: Path) -> list[str]:
    return violations(root, credit_os.LAYERS, credit_os.ISOLATED)


def test_isolated_package_importing_a_layer_absolute(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"signal/a.py": "from credit_os.sources import x\n"})
    found = _isolated(root)
    assert len(found) == 1
    assert "signal" in found[0] and "sources" in found[0]


def test_isolated_package_importing_a_layer_relative(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"signal/a.py": "from ..handoff import x\n"})
    found = _isolated(root)
    assert len(found) == 1
    assert "signal" in found[0] and "handoff" in found[0]


def test_isolated_package_importing_a_layer_bare(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"signal/a.py": "from credit_os import delivery\n"})
    found = _isolated(root)
    assert len(found) == 1
    assert "signal" in found[0] and "delivery" in found[0]


def test_layer_importing_the_isolated_package_bare(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"delivery/a.py": "from credit_os import signal\n"})
    found = _isolated(root)
    assert len(found) == 1
    assert "delivery" in found[0] and "signal" in found[0]


def test_layer_importing_the_isolated_package_static(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"sources/a.py": "import credit_os.signal.store\n"})
    found = _isolated(root)
    assert len(found) == 1
    assert "sources" in found[0] and "signal" in found[0]


def test_layer_importing_the_isolated_package_dynamic(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {"orchestrator/a.py": "import importlib\nimportlib.import_module('credit_os.signal')\n"},
    )
    found = _isolated(root)
    assert len(found) == 1
    assert "orchestrator" in found[0] and "signal" in found[0]


def test_isolated_package_importing_itself_allowed(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "signal/a.py": (
                "from . import b\nfrom credit_os.signal import store\nimport credit_os.signal.fold\n"
            ),
            "signal/b.py": "x = 1\n",
        },
    )
    assert _isolated(root) == []


def test_package_root_importing_the_isolated_package(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"__init__.py": "from credit_os import signal\n"})
    found = _isolated(root)
    assert len(found) == 1
    assert "signal" in found[0]


def test_empty_isolated_set_changes_nothing_for_ordinary_layers(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"delivery/a.py": "from credit_os import sources\n"})
    assert violations(root, credit_os.LAYERS, frozenset()) == []


def test_byte_order_mark_file_is_read(tmp_path: Path) -> None:
    root = _tree(tmp_path, {})
    (root / credit_os.LAYERS[0] / "bom.py").write_bytes(b"\xef\xbb\xbfx = 1\n")
    assert violations(root, credit_os.LAYERS) == []
