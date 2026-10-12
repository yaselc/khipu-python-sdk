"""Issue #18 publication gates must block every publish until the owner opens them.

``tools/check_dist.py --tag`` is the release check both publish workflows run
(through ``build-dist.yml``) before uploading anything. It must fail while:

- ``LICENSE`` still carries the template copyright placeholder; or
- ``PUBLICATION_GATES.toml`` does not record ``approved = true`` with evidence
  for the Khipu redistribution gate.

The repository's real gate state is only ever read here. Approved states are
exercised on temporary copies.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
GATES = REPO / "PUBLICATION_GATES.toml"
CHECK_DIST = REPO / "tools" / "check_dist.py"
BLOCKED = (
    "Khipu redistribution permission is not approved; publication is blocked "
    "by Issue #18"
)

MIT_RESOLVED = "MIT License\n\nCopyright (c) 2026 Example Holder\n"
MIT_PLACEHOLDER = "MIT License\n\nCopyright (c) <YEAR> <COPYRIGHT HOLDER>\n"
APPROVED = (
    "[khipu_redistribution]\n"
    "approved = true\n"
    'evidence = "https://example.invalid/issue-18-decision"\n'
)


def load_check_dist() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_dist", CHECK_DIST)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_dist = load_check_dist()


def fake_repo(tmp_path: Path, license_text: str, gates: str | None) -> Path:
    (tmp_path / "LICENSE").write_text(license_text, encoding="utf-8")
    if gates is not None:
        (tmp_path / "PUBLICATION_GATES.toml").write_text(gates, encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------------
# The repository's real state
# --------------------------------------------------------------------------


def test_the_redistribution_gate_exists_and_is_tracked():
    assert GATES.is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", GATES.name],
        cwd=REPO,
        capture_output=True,
    )
    assert tracked.returncode == 0, "PUBLICATION_GATES.toml is not tracked in Git"


def test_the_redistribution_gate_is_currently_unresolved():
    """Flipping this is a future, owner-reviewed decision recorded in #18."""
    table = re.search(
        r"^\[khipu_redistribution\]$(.*?)(?=^\[|\Z)",
        GATES.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert table is not None
    assert re.findall(r"^approved\s*=\s*(\S+)", table.group(1), re.M) == ["false"]
    assert re.findall(r'^evidence\s*=\s*"([^"]*)"', table.group(1), re.M) == [""]


def test_the_repository_is_not_publishable_today():
    problems = check_dist.publication_gate_problems(REPO)

    assert any(p.startswith(BLOCKED) for p in problems), problems
    assert any("<COPYRIGHT HOLDER>" in p for p in problems), problems


def test_check_dist_with_tag_fails_on_the_redistribution_gate(tmp_path):
    """The exact command build-dist.yml runs refuses to pass today."""
    result = subprocess.run(
        [sys.executable, str(CHECK_DIST), str(tmp_path), "--tag", "v0.0.0"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert f"FAIL: {BLOCKED}" in result.stdout, result.stdout


# --------------------------------------------------------------------------
# Gate logic, on temporary copies
# --------------------------------------------------------------------------


def test_both_gates_open_means_publishable(tmp_path):
    repo = fake_repo(tmp_path, MIT_RESOLVED, APPROVED)
    assert check_dist.publication_gate_problems(repo) == []


def test_license_placeholder_alone_still_blocks(tmp_path):
    repo = fake_repo(tmp_path, MIT_PLACEHOLDER, APPROVED)
    problems = check_dist.publication_gate_problems(repo)

    assert len(problems) == 1 and "<COPYRIGHT HOLDER>" in problems[0]


@pytest.mark.parametrize(
    "gates",
    [
        pytest.param(None, id="file-missing"),
        pytest.param("", id="file-empty"),
        pytest.param("[other]\napproved = true\n", id="table-missing"),
        pytest.param("[khipu_redistribution]\n", id="key-missing"),
        pytest.param("[khipu_redistribution]\napproved = false\n", id="false"),
        pytest.param('[khipu_redistribution]\napproved = "true"\n', id="string-true"),
        pytest.param("[khipu_redistribution]\napproved = True\n", id="capitalised"),
        pytest.param("[khipu_redistribution]\napproved = yes\n", id="yes"),
        pytest.param(
            "[khipu_redistribution]\napproved = true\napproved = false\n"
            'evidence = "x"\n',
            id="duplicate-key",
        ),
        pytest.param(
            "[khipu_redistribution]\napproved = false\n[other]\napproved = true\n"
            'evidence = "x"\n',
            id="approval-in-another-table",
        ),
        pytest.param(
            "[khipu_redistribution]\n# approved = true\napproved = false\n",
            id="commented-out",
        ),
    ],
)
def test_anything_but_an_explicit_approval_blocks(tmp_path, gates):
    repo = fake_repo(tmp_path, MIT_RESOLVED, gates)
    problems = check_dist.publication_gate_problems(repo)

    assert len(problems) == 1 and problems[0].startswith(BLOCKED), problems


@pytest.mark.parametrize(
    "evidence", ['evidence = ""', 'evidence = "   "', ""], ids=["empty", "blank", "absent"]
)
def test_approval_without_evidence_blocks(tmp_path, evidence):
    gates = f"[khipu_redistribution]\napproved = true\n{evidence}\n"
    repo = fake_repo(tmp_path, MIT_RESOLVED, gates)
    problems = check_dist.publication_gate_problems(repo)

    assert len(problems) == 1 and "no evidence is recorded" in problems[0], problems
