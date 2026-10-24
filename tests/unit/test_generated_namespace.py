"""Pin where the generated clients live and how that is packaged (#56).

The OpenAPI-generated clients used to ship as a top-level ``generated``
package. A consumer project or another distribution with a package of the same
name could shadow the SDK's clients, overwrite their files, or be hidden by
them. They now live in the private ``khipu_sdk._generated`` package, and the
distribution installs ``khipu_sdk`` alone.

These tests read the repository configuration with regexes, as
``test_release_metadata.py`` does (no ``tomllib`` on Python 3.10), and run
``tools/check_dist.py`` against small synthetic artifacts built in a temporary
directory, so a configuration or checker regression fails without a build.
"""

from __future__ import annotations

import importlib.util
import io
import re
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
MAKEFILE = REPO / "Makefile"
CI = REPO / ".github" / "workflows" / "ci.yml"
CHECK_DIST = REPO / "tools" / "check_dist.py"
GENERATED = REPO / "khipu_sdk" / "_generated"

VERSION = "9.9.9"


def load_check_dist() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_dist", CHECK_DIST)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_dist = load_check_dist()


def toml_table(name: str) -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(rf"^\[{re.escape(name)}\]$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    assert match is not None, f"pyproject.toml has no [{name}] table"
    return match.group(1)


def toml_value(table: str, key: str) -> str:
    match = re.search(rf"^{key}\s*=\s*(.+)$", toml_table(table), re.M)
    assert match is not None, f"[{table}] declares no {key}"
    return match.group(1).strip()


# --------------------------------------------------------------------------
# Source tree and configuration
# --------------------------------------------------------------------------


def test_the_generated_clients_live_in_the_private_sdk_package():
    assert not (REPO / "generated").exists(), "the top-level generated/ is back"
    assert (GENERATED / "__init__.py").is_file()
    for api in ("instant_payments", "automatic_payments"):
        assert (GENERATED / api / "client.py").is_file(), api


def test_the_makefile_generates_into_the_private_package():
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert re.findall(r"^GENERATED_DIR := (.*)$", makefile, re.M) == ["khipu_sdk/_generated"]
    # ensure-generated-package recreates the package marker in that directory.
    assert "> $(GENERATED_DIR)/__init__.py" in makefile


def test_setuptools_discovers_the_sdk_package_only():
    assert toml_value("tool.setuptools.packages.find", "include") == '["khipu_sdk*"]'


def test_ruff_and_mypy_exclude_exactly_the_generated_directory():
    """Excluding more would stop linting or type-checking hand-written code."""
    assert toml_value("tool.ruff", "extend-exclude") == '["khipu_sdk/_generated"]'
    assert toml_value("tool.mypy", "exclude") == "['^khipu_sdk/_generated/']"


def test_the_ci_regeneration_check_inspects_the_generated_directory():
    """A check left on the old path would pass however generated code drifted."""
    ci = CI.read_text(encoding="utf-8")
    paths = re.findall(r"git (?:status --porcelain|status --short|diff) -- ([^\s)\"]+)", ci)
    generated = [path for path in paths if "generated" in path]

    # The gate itself, then the two commands that report what drifted.
    assert "git status --porcelain -- khipu_sdk/_generated/" in ci
    assert generated == ["khipu_sdk/_generated/"] * 3, generated


# --------------------------------------------------------------------------
# tools/check_dist.py
# --------------------------------------------------------------------------


def long_description_headers() -> str:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    return (
        "Metadata-Version: 2.4\n"
        "Name: khipu-python-sdk\n"
        f"Version: {VERSION}\n"
        "License-Expression: MIT\n"
        "License-File: LICENSE\n"
        "\n"
        f"{readme}"
    )


def write_wheel(path: Path, *, top_level: str, extra: dict[str, str]) -> Path:
    dist_info = f"khipu_python_sdk-{VERSION}.dist-info/"
    with zipfile.ZipFile(path, "w") as wheel:
        for name in sorted(check_dist.source_files("khipu_sdk")):
            wheel.write(REPO / name, name)
        wheel.writestr(dist_info + "METADATA", long_description_headers())
        wheel.writestr(dist_info + "licenses/LICENSE", "MIT")
        wheel.writestr(dist_info + "top_level.txt", top_level)
        for name, content in extra.items():
            wheel.writestr(name, content)
    return path


def write_sdist(path: Path, *, top_level: str, extra: dict[str, str]) -> Path:
    prefix = f"khipu_python_sdk-{VERSION}/"
    files = {
        "PKG-INFO": long_description_headers(),
        "khipu_python_sdk.egg-info/top_level.txt": top_level,
        "khipu_sdk/__init__.py": "",
        "khipu_sdk/_generated/__init__.py": "",
        **extra,
    }
    with tarfile.open(path, "w:gz") as sdist:
        for name, content in files.items():
            data = content.encode("utf-8")
            member = tarfile.TarInfo(prefix + name)
            member.size = len(data)
            sdist.addfile(member, io.BytesIO(data))
    return path


@pytest.mark.parametrize("write", [write_wheel, write_sdist], ids=["wheel", "sdist"])
def test_a_clean_artifact_passes(tmp_path, write):
    check = check_dist.check_wheel if write is write_wheel else check_dist.check_sdist
    artifact = write(tmp_path / "artifact", top_level="khipu_sdk\n", extra={})

    assert check(artifact, VERSION) == []


@pytest.mark.parametrize("write", [write_wheel, write_sdist], ids=["wheel", "sdist"])
def test_an_obsolete_top_level_generated_package_is_rejected(tmp_path, write):
    check = check_dist.check_wheel if write is write_wheel else check_dist.check_sdist
    artifact = write(
        tmp_path / "artifact",
        top_level="generated\nkhipu_sdk\n",
        extra={
            "generated/__init__.py": "",
            "generated/instant_payments/client.py": "",
        },
    )

    problems = check(artifact, VERSION)

    kind = "wheel" if write is write_wheel else "sdist"
    assert sorted(problems) == [
        f"{kind} ships the obsolete top-level package: generated/__init__.py",
        f"{kind} ships the obsolete top-level package: generated/instant_payments/client.py",
        f"{kind} top_level.txt declares ['generated', 'khipu_sdk'], expected "
        "['khipu_sdk'] only; a second top-level package can collide with "
        "unrelated code",
    ]


def test_a_wheel_with_any_other_top_level_package_is_rejected(tmp_path):
    wheel = write_wheel(
        tmp_path / "artifact.whl",
        top_level="khipu_generated\nkhipu_sdk\n",
        extra={"khipu_generated/__init__.py": ""},
    )

    problems = check_dist.check_wheel(wheel, VERSION)

    assert "wheel ships unexpected file khipu_generated/__init__.py" in problems
    assert any("top_level.txt declares ['khipu_generated', 'khipu_sdk']" in p for p in problems)
