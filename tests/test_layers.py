"""Mechanical enforcement of the hexagonal layer boundaries (AD-1).

These tests make the architecture invariants executable:

* every layer is an importable top-level package backed by ``src/<layer>``,
* every package under ``src/`` is declared as a ``root_packages`` entry,
* the shipped ``[tool.importlinter]`` contract pins the inward-only direction,
* the throwaway and unresolved-layer contracts do not drift from the shipped one,
* ``import-linter`` keeps that contract on the real project,
* a domain or application module importing any higher layer breaks the contract,
* the permitted inward direction (higher layers importing lower ones) stays green,
* a declared layer that cannot be imported is reported instead of silently skipped,
* a stylistically broken file fails Ruff with the expected diagnostic, and
* the CI merge gate still exists and still runs every verification command.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYERS = ("domain", "application", "infrastructure")

_LAYERS_CONTRACT = """\
[tool.importlinter]
root_packages = ["domain", "application", "infrastructure"]

[[tool.importlinter.contracts]]
name = "Hexagonal dependency rule"
type = "layers"
layers = ["infrastructure", "application", "domain"]
"""

_UNRESOLVED_LAYER_CONTRACT = """\
[tool.importlinter]
root_packages = ["domain", "application", "infrastructure", "missing_layer"]

[[tool.importlinter.contracts]]
name = "Hexagonal dependency rule"
type = "layers"
layers = ["infrastructure", "application", "domain"]
"""

_EXPECTED_CONTRACT = {
    "name": "Hexagonal dependency rule",
    "type": "layers",
    "layers": ["infrastructure", "application", "domain"],
}


def _shipped_importlinter_config() -> dict:
    """Parse the shipped ``[tool.importlinter]`` table from ``pyproject.toml``."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as config_file:
        return tomllib.load(config_file)["tool"]["importlinter"]


def _named_layers_contract(config: dict) -> dict:
    """Return the boundary contract by name, ignoring any other contracts."""
    contracts = [
        contract
        for contract in config["contracts"]
        if contract.get("name") == _EXPECTED_CONTRACT["name"]
    ]
    assert len(contracts) == 1, contracts
    return contracts[0]


@pytest.mark.parametrize("layer", LAYERS)
def test_layer_package_is_importable(layer: str) -> None:
    """Each layer must be importable and resolve to its own ``src/<layer>``."""
    module = importlib.import_module(layer)
    module_file = getattr(module, "__file__", None)

    assert module.__name__ == layer
    assert module_file is not None
    assert Path(module_file).resolve().parent == (PROJECT_ROOT / "src" / layer)


def test_shipped_contract_pins_inward_direction() -> None:
    """The shipped contract must forbid the outward direction, not merely exist."""
    config = _shipped_importlinter_config()

    assert config["root_packages"] == list(LAYERS)
    contract = _named_layers_contract(config)
    assert contract["type"] == _EXPECTED_CONTRACT["type"]
    assert contract["layers"] == _EXPECTED_CONTRACT["layers"]


def test_declared_root_packages_cover_src_layers() -> None:
    """Every ``src/`` package is declared, so no layer can escape the contract."""
    config = _shipped_importlinter_config()
    packages_on_disk = {
        path.name
        for path in (PROJECT_ROOT / "src").iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }

    assert set(config["root_packages"]) == packages_on_disk


def test_throwaway_contract_matches_shipped_contract() -> None:
    """The negative-control copies must not drift from the shipped contract."""
    shipped = _shipped_importlinter_config()
    shipped_contract = _named_layers_contract(shipped)

    throwaway = tomllib.loads(_LAYERS_CONTRACT)["tool"]["importlinter"]
    assert throwaway["root_packages"] == shipped["root_packages"]
    assert _named_layers_contract(throwaway) == shipped_contract

    unresolved = tomllib.loads(_UNRESOLVED_LAYER_CONTRACT)["tool"]["importlinter"]
    assert unresolved["root_packages"] == [*shipped["root_packages"], "missing_layer"]
    assert _named_layers_contract(unresolved) == shipped_contract


def _tool_executable(name: str) -> str:
    """Locate a console script in PATH or the active environment's bin dir."""
    executable = shutil.which(name)
    if executable is not None:
        return executable

    bin_dir = Path(sys.executable).parent
    for suffix in ("", ".exe", ".cmd", ".bat"):
        candidate = bin_dir / f"{name}{suffix}"
        if candidate.is_file():
            return str(candidate)

    pytest.fail(
        f"{name} executable not found in PATH or the active environment; "
        "run the suite with `uv run pytest`"
    )


def test_layering_contract_is_kept() -> None:
    """``import-linter`` must report every contract as kept."""
    result = subprocess.run(
        [_tool_executable("lint-imports")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Hexagonal dependency rule" in output
    assert "KEPT" in output
    assert "BROKEN" not in output


def _build_layer_project(
    root: Path,
    *,
    layers: tuple[str, ...] = LAYERS,
    bodies: dict[str, str] | None = None,
) -> Path:
    """Create a throwaway layered project for contract-failure scenarios."""
    (root / "pyproject.toml").write_text(_LAYERS_CONTRACT, encoding="utf-8")
    bodies = bodies or {}
    unknown = set(bodies) - set(layers)
    assert not unknown, f"bodies reference unknown layer(s): {sorted(unknown)}"
    for layer in layers:
        package = root / "src" / layer
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text(bodies.get(layer, ""), encoding="utf-8")
    return root


def _lint_imports_in(project: Path) -> subprocess.CompletedProcess[str]:
    """Run ``lint-imports`` against a throwaway project's own configuration."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(project / "src"), env.get("PYTHONPATH", "")) if part
    )
    return subprocess.run(
        [
            _tool_executable("lint-imports"),
            "--config",
            str(project / "pyproject.toml"),
        ],
        cwd=project,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )


def test_compliant_project_is_kept(tmp_path: Path) -> None:
    """The throwaway harness can pass: a compliant project keeps the contract."""
    project = _build_layer_project(tmp_path)

    result = _lint_imports_in(project)

    assert result.returncode == 0, result.stdout + result.stderr


def _assert_contract_broken(result: subprocess.CompletedProcess[str]) -> None:
    """A violation must break the named contract, not fail for another reason."""
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "Hexagonal dependency rule" in output
    assert "BROKEN" in output


def test_domain_may_not_import_infrastructure(tmp_path: Path) -> None:
    """A domain module importing infrastructure must break the contract."""
    project = _build_layer_project(
        tmp_path, bodies={"domain": "from infrastructure import __name__\n"}
    )

    _assert_contract_broken(_lint_imports_in(project))


def test_domain_may_not_import_application(tmp_path: Path) -> None:
    """A domain module importing application must break the contract."""
    project = _build_layer_project(
        tmp_path, bodies={"domain": "from application import __name__\n"}
    )

    _assert_contract_broken(_lint_imports_in(project))


def test_application_may_not_import_infrastructure(tmp_path: Path) -> None:
    """An application module importing infrastructure must break the contract."""
    project = _build_layer_project(
        tmp_path, bodies={"application": "from infrastructure import __name__\n"}
    )

    _assert_contract_broken(_lint_imports_in(project))


def test_permitted_inward_dependencies_are_kept(tmp_path: Path) -> None:
    """Higher layers may import lower ones; that direction must stay green."""
    project = _build_layer_project(
        tmp_path,
        bodies={
            "application": "from domain import __name__\n",
            "infrastructure": (
                "from application import __name__\nfrom domain import __name__\n"
            ),
        },
    )

    result = _lint_imports_in(project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "KEPT" in result.stdout + result.stderr


def test_unresolved_layer_is_reported(tmp_path: Path) -> None:
    """A declared layer that cannot be imported must fail loudly, never silently."""
    project = _build_layer_project(tmp_path)
    (project / "pyproject.toml").write_text(
        _UNRESOLVED_LAYER_CONTRACT, encoding="utf-8"
    )

    result = _lint_imports_in(project)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "missing_layer" in result.stdout + result.stderr


def test_ruff_flags_style_violation(tmp_path: Path) -> None:
    """Ruff must reject an unused import and unformatted source."""
    unused_import = tmp_path / "unused_import.py"
    unused_import.write_text("import os\n", encoding="utf-8")
    check = subprocess.run(
        [
            _tool_executable("ruff"),
            "check",
            "--config",
            str(PROJECT_ROOT / "pyproject.toml"),
            str(unused_import),
        ],
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )
    assert check.returncode != 0, check.stdout + check.stderr
    assert "F401" in check.stdout + check.stderr

    unformatted = tmp_path / "unformatted.py"
    unformatted.write_text("x=1\n", encoding="utf-8")
    fmt = subprocess.run(
        [
            _tool_executable("ruff"),
            "format",
            "--check",
            "--config",
            str(PROJECT_ROOT / "pyproject.toml"),
            str(unformatted),
        ],
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )
    assert fmt.returncode != 0, fmt.stdout + fmt.stderr
    assert "would be reformatted" in fmt.stdout + fmt.stderr


def test_ci_workflow_runs_the_verification_gate() -> None:
    """The merge gate must exist, trigger on PRs, and run every check.

    The workflow was deleted by accident once (commit ``20fcb23``) while the
    whole suite stayed green, so its presence is asserted rather than assumed.
    """
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "push:" in workflow
    assert "pull_request:" in workflow
    assert 'python-version: "3.12"' in workflow
    for command in (
        "uv sync --locked",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run lint-imports",
        "uv run pytest",
    ):
        assert command in workflow, command
