import ast
from pathlib import Path

import credit_os


def violations(root: Path, layers: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    package = root.name
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and entry.name not in layers and entry.name != "__pycache__":
            out.append(f"{entry}: sub-package {entry.name} is not in the layer list")
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if len(rel.parts) < 2:
            if rel.name != "__init__.py":
                out.append(
                    f"{path}: module {rel.name} sits in the package root, outside every layer"
                )
            continue
        layer = rel.parts[0]
        if layer not in layers:
            continue
        pkg_parts = [package, *rel.parts[:-1]]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Import | ast.ImportFrom):
                continue
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            else:
                if node.level:
                    base = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                    module = ".".join([*base, *([node.module] if node.module else [])])
                else:
                    module = node.module or ""
                if module:
                    targets = [module, *(f"{module}.{alias.name}" for alias in node.names)]
            later: set[str] = set()
            for target in targets:
                parts = target.split(".")
                if len(parts) < 2 or parts[0] != package or parts[1] not in layers:
                    continue
                if layers.index(parts[1]) > layers.index(layer):
                    later.add(parts[1])
            out.extend(f"{path}:{node.lineno} {layer} imports {name}" for name in sorted(later))
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
    assert violations(Path("src/credit_os"), credit_os.LAYERS) == []


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
