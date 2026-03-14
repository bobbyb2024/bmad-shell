import pathlib


def test_layer_packages_exist(project_root: pathlib.Path):
    """Verify that each layer package exists as a directory with __init__.py (AC10)."""
    layers = [
        "rendering",
        "providers",
        "engine",
        "state",
        "config",
        "types",
    ]
    for layer in layers:
        layer_dir = project_root / "src" / "bmad_orch" / layer
        assert layer_dir.is_dir(), f"Layer '{layer}' must be a package directory, not a module file"
        assert (layer_dir / "__init__.py").exists(), f"Layer '{layer}' missing __init__.py"


def test_import_linter_contract_exists(pyproject_content):
    """Verify that import-linter contract is defined in pyproject.toml."""
    importlinter = pyproject_content.get("tool", {}).get("importlinter", {})
    contracts = importlinter.get("contracts", [])
    assert len(contracts) > 0, "No import-linter contracts defined"
    # Find the layers contract
    layers_contract = None
    for contract in contracts:
        if contract.get("type") == "layers":
            layers_contract = contract
            break
    assert layers_contract is not None, "No layers contract found"
    layers = layers_contract.get("layers", [])
    expected = ["rendering", "providers", "engine", "state", "config", "types"]
    for expected_layer in expected:
        assert any(expected_layer in layer for layer in layers), f"Layer '{expected_layer}' not in contract"
