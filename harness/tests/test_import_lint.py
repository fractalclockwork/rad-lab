"""Import rules: lesson labs must not pull hardware TX modules."""

from pathlib import Path
import ast


REPO_ROOT = Path(__file__).resolve().parents[2]
LESSON_LABS = REPO_ROOT / "lesson" / "labs"
HUMAN_DIR = REPO_ROOT / "human"
SOFTWARE_DIR = REPO_ROOT / "software"
HARNESS_DIR = REPO_ROOT / "harness"

FORBIDDEN_HARDWARE = {
    "hardware",
    "hardware.loopback",
    "hardware.firmware",
    "hardware.stages",
    "hardware.probe",
    "hardware.labs",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                found.add(parts[0])
                if len(parts) > 1:
                    found.add(".".join(parts[:2]))
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            found.add(parts[0])
            if len(parts) > 1:
                found.add(".".join(parts[:2]))
            found.add(node.module)
    return found


def test_lesson_labs_do_not_import_hardware_tx():
    offenders = []
    for path in sorted(LESSON_LABS.glob("*.py")):
        mods = _imports(path)
        bad = mods & FORBIDDEN_HARDWARE
        if bad:
            offenders.append(f"{path.name}: {sorted(bad)}")
    assert not offenders, "lesson labs imported hardware modules:\n" + "\n".join(offenders)


def test_human_assent_does_not_import_hardware_tx():
    for path in sorted(HUMAN_DIR.glob("*.py")):
        mods = _imports(path)
        assert not (mods & FORBIDDEN_HARDWARE), f"{path.name} imported {mods & FORBIDDEN_HARDWARE}"


def test_software_does_not_import_hardware_human_or_environment():
    forbidden = FORBIDDEN_HARDWARE | {"human", "environment"}
    for path in sorted(SOFTWARE_DIR.rglob("*.py")):
        if "tests" in path.parts:
            continue
        mods = _imports(path)
        assert not (mods & forbidden), f"{path.relative_to(REPO_ROOT)} imported {mods & forbidden}"


def test_harness_does_not_import_hardware_or_human():
    forbidden = FORBIDDEN_HARDWARE | {"human"}
    for path in sorted(HARNESS_DIR.glob("*.py")):
        mods = _imports(path)
        assert not (mods & forbidden), f"{path.name} imported {mods & forbidden}"
