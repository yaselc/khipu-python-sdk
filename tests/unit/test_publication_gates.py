"""Issue #18 publication gates must block every publish until the owner resolves them.

``tools/check_dist.py --tag`` is the release check both publish workflows run
(through ``build-dist.yml``) before uploading anything. It must fail while:

- ``LICENSE`` still carries the template copyright placeholder; or
- ``PUBLICATION_GATES.toml`` does not record ``approved = true`` with evidence
  for the Khipu redistribution gate.

Both gates are resolved. The license gate (Issue #24): ``LICENSE`` carries the
owner-approved notice, pinned below. The redistribution gate (Issue #26):
``PUBLICATION_GATES.toml`` approves with the Issue #18 comment recording
Khipu's written permission as evidence, also pinned below.

The repository's real gate state is only ever read here. Refused states,
including the real gate file with its approval or evidence reverted, are
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

LICENSE = REPO / "LICENSE"
#: The owner-approved notice (Issue #24). Changing the holder or the years is
#: an owner decision, never an edit made to satisfy a check.
APPROVED_NOTICE = "Copyright (c) 2025-2026 Yasel Couce"

MIT_RESOLVED = "MIT License\n\nCopyright (c) 2026 Example Holder\n"
MIT_PLACEHOLDER = "MIT License\n\nCopyright (c) <YEAR> <COPYRIGHT HOLDER>\n"
#: Public record of Khipu's written permission (Issue #18). Changing it is an
#: owner decision, never an edit made to satisfy a check.
APPROVED_EVIDENCE = (
    "https://github.com/parle-cl/khipu-python-sdk/issues/18#issuecomment-6159094247"
)
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


def test_the_redistribution_gate_records_the_approved_decision():
    """Issue #26: approved, with the #18 comment recording Khipu's permission."""
    table = re.search(
        r"^\[khipu_redistribution\]$(.*?)(?=^\[|\Z)",
        GATES.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert table is not None
    assert re.findall(r"^approved\s*=\s*(\S+)", table.group(1), re.M) == ["true"]
    assert re.findall(r'^evidence\s*=\s*"([^"]*)"', table.group(1), re.M) == [
        APPROVED_EVIDENCE
    ]


def test_license_carries_the_approved_copyright_notice():
    """Issue #24: the holder and years are the owner's decision, pinned here."""
    lines = LICENSE.read_text(encoding="utf-8").splitlines()

    assert lines[:3] == ["MIT License", "", APPROVED_NOTICE]
    assert [line for line in lines if line.startswith("Copyright")] == [
        APPROVED_NOTICE
    ]
    assert "<YEAR>" not in "\n".join(lines)
    assert check_dist.LICENSE_PLACEHOLDER not in "\n".join(lines)


def test_no_publication_gate_blocks_the_repository():
    """Both gates are resolved, so neither blocks a publish."""
    assert check_dist.publication_gate_problems(REPO) == []


def test_check_dist_with_tag_raises_no_gate_failure(tmp_path):
    """The exact command build-dist.yml runs no longer fails on a gate.

    ``tmp_path`` holds no artifacts, so the command still fails, but only
    because the distribution is missing.
    """
    tag = f"v{check_dist.declared_version()}"
    result = subprocess.run(
        [sys.executable, str(CHECK_DIST), str(tmp_path), "--tag", tag],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    failures = [line for line in result.stdout.splitlines() if line.startswith("FAIL")]
    assert failures == [
        f"FAIL: {tmp_path} must hold exactly one wheel and one sdist, found []"
    ], result.stdout


def test_the_real_gate_reverted_to_false_blocks(tmp_path):
    """Fail-closed still holds for the committed file, not only for fixtures."""
    real = GATES.read_text(encoding="utf-8")
    assert real.count("\napproved = true\n") == 1
    repo = fake_repo(
        tmp_path,
        LICENSE.read_text(encoding="utf-8"),
        real.replace("\napproved = true\n", "\napproved = false\n"),
    )
    problems = check_dist.publication_gate_problems(repo)

    assert len(problems) == 1 and problems[0].startswith(BLOCKED), problems


def test_the_real_gate_without_its_evidence_blocks(tmp_path):
    real = GATES.read_text(encoding="utf-8")
    assert real.count(f'"{APPROVED_EVIDENCE}"') == 1
    repo = fake_repo(
        tmp_path,
        LICENSE.read_text(encoding="utf-8"),
        real.replace(f'"{APPROVED_EVIDENCE}"', '""'),
    )
    problems = check_dist.publication_gate_problems(repo)

    assert len(problems) == 1 and "no evidence is recorded" in problems[0], problems


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
