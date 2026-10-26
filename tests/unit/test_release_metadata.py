"""Release metadata and the release process must stay deliberate and consistent.

Publication is an explicit maintainer action (Issue #18):

- ``.github/workflows/publish-testpypi.yml`` runs only on ``workflow_dispatch``;
- ``.github/workflows/publish-pypi.yml`` runs only when a GitHub Release is
  published, and only for a tag equal to ``v<project.version>``;
- merging or pushing to master publishes, tags and releases nothing.

These tests pin that contract, plus the metadata a PyPI release depends on:
the CHANGELOG documents the declared version, every README install reference
names a version that is actually published, and the README/package metadata
keep the independence disclaimer. The maintainer procedure is
``docs/RELEASING.md`` (Issue #46).

Publication cannot be observed offline, so the release state is pinned here:

- ``LATEST_PUBLISHED_RELEASE`` is the newest version on PyPI and its date. It
  is the newest dated CHANGELOG section and the version every README install
  reference names.
- ``RELEASE_CANDIDATE`` is the declared ``project.version`` while it is not yet
  tagged or uploaded, or ``None`` when the declared version is the latest
  published release. A candidate has no dated CHANGELOG section, is named as
  ``Target release:`` under ``## [Unreleased]``, and the README never offers
  to install it.

The release cut (``docs/RELEASING.md``, step 2) moves the declared version
from one to the other: it dates the CHANGELOG section, points the README
install references at the new version, sets ``LATEST_PUBLISHED_RELEASE`` to it
and ``RELEASE_CANDIDATE`` to ``None``.

The release cut is merged *before* the upload, because the README it freezes
becomes the PyPI project description. From that merge until the upload,
``LATEST_PUBLISHED_RELEASE`` is the intended publication (version and date),
not evidence that the index already has it; these offline tests cannot tell
the difference. If publication slips, the CHANGELOG date and this constant are
corrected together before tagging or uploading.

Stale versions are found by pattern, not by line: every install reference the
README contains (pip/requirement specifiers, Git and GitHub tag refs, wheel
and sdist file names) must name the latest published release, the four
documented install forms must all be present, and no other released version
may appear anywhere in the README or the release procedure. The version
history belongs to the CHANGELOG alone.

The workflow checks read the YAML as text on purpose: the files are small, the
checked lines are distinctive, and the dev environment has no YAML parser.

These tests are cheap and offline: they read files in the repository, and the
master-ancestry gate of ``build-dist.yml`` is executed against throwaway git
repositories under ``tmp_path``.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
CHANGELOG = REPO / "CHANGELOG.md"
README = REPO / "README.md"
RELEASING = REPO / "docs" / "RELEASING.md"
CONTRIBUTING = REPO / "CONTRIBUTING.md"
WORKFLOWS = REPO / ".github" / "workflows"
TESTPYPI_WORKFLOW = WORKFLOWS / "publish-testpypi.yml"
PYPI_WORKFLOW = WORKFLOWS / "publish-pypi.yml"
BUILD_WORKFLOW = WORKFLOWS / "build-dist.yml"
DEPENDABOT = REPO / ".github" / "dependabot.yml"

FINAL_REPOSITORY = "https://github.com/yaselc/khipu-python-sdk"

#: The first release published to PyPI, and the date it was published (#31).
FIRST_PUBLIC_RELEASE = ("0.3.3", "2026-10-17")

#: The newest release published to PyPI, and the date it was published.
#: After a release cut and before its upload, the intended publication (#46).
LATEST_PUBLISHED_RELEASE = ("0.3.5", "2026-10-21")

#: ``project.version`` while it is prepared but not tagged or uploaded;
#: ``None`` when the declared version is ``LATEST_PUBLISHED_RELEASE``.
RELEASE_CANDIDATE: str | None = "0.4.0"

#: Wording that only described 0.3.3 before it was published (Issue #22).
PRE_RELEASE_WORDING = (
    "Pre-release status",
    "next planned release",
    "not yet published",
    "not yet released",
    "does not yet exist",
    "latest existing tag",
    "is released)",
    "is released:",
    "same tag from source",
    "has not been published to PyPI yet",
)

#: A version as an install reference can spell it, pre-releases included. A
#: trailing sentence period is stripped from matches.
_VERSION = r"v?(\d+(?:\.\d+)*(?:[-.+]?[A-Za-z0-9]+)*)"

#: Every way a README can tell a reader to install a particular version,
#: whatever its line or code block: a requirement specifier (``==``, ``>=``,
#: ``~=``, ...), with or without extras or quotes; a Git ref of this
#: repository (``.git@v1.2.3``); a GitHub tag, release or archive URL; a wheel
#: or sdist file name.
INSTALL_REFERENCES = (
    re.compile(
        r"khipu[-_.]python[-_.]sdk\s*(?:\[[^\]\n]*\])?\s*"
        r"(?:===|==|~=|>=|<=|!=|>|<)\s*" + _VERSION,
        re.I,
    ),
    re.compile(r"khipu-python-sdk(?:\.git)?@" + _VERSION, re.I),
    re.compile(
        r"github\.com/yaselc/khipu-python-sdk/"
        r"(?:releases/tag|tree|blob|archive(?:/refs/tags)?)/" + _VERSION,
        re.I,
    ),
    re.compile(r"khipu_python_sdk-" + _VERSION + r"(?=-py|\.tar|\.zip)", re.I),
)

#: A dotted ``X.Y.Z`` version anywhere in prose, ``vX.Y.Z`` tags included,
#: but not inside a longer dotted number or an identifier.
VERSION_TOKEN = re.compile(r"(?<![\w.])v?(\d+\.\d+\.\d+)(?!\w|\.\d)")

#: The four install forms the README documents, each pinned to ``{version}``.
INSTALL_FORMS = (
    "```bash\npip install khipu-python-sdk=={version}\n```",
    "```text\nkhipu-python-sdk=={version}\n```",
    '  "khipu-python-sdk=={version}",\n',
    "khipu-python-sdk @ git+https://github.com/yaselc/khipu-python-sdk.git@v{version}\n",
)

#: The links the README Releases section must give, absolute so they work in
#: the PyPI long description (#31, #46).
RELEASE_LINKS = (
    "https://github.com/yaselc/khipu-python-sdk/blob/master/CHANGELOG.md",
    "https://github.com/yaselc/khipu-python-sdk/releases",
    "https://github.com/yaselc/khipu-python-sdk/blob/master/docs/RELEASING.md",
)

#: ``## [1.2.3] - 2026-09-22`` -- a released section, not ``## [Unreleased]``.
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.M)


#: The ``version = "..."`` line inside the ``[project]`` table. Read with a
#: regex rather than ``tomllib``, which is stdlib only from Python 3.11 while
#: this package supports 3.10.
PROJECT_TABLE = re.compile(r"^\[project\]$(.*?)(?=^\[)", re.M | re.S)
VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)

#: The ``## [Unreleased]`` section, up to the next ``## `` heading.
UNRELEASED_SECTION = re.compile(r"^## \[Unreleased\]\n(.*?)(?=^## )", re.M | re.S)
#: How ``## [Unreleased]`` names the release candidate its entries will ship as.
TARGET_RELEASE_LINE = re.compile(r"^Target release: (.*)$", re.M)


def project_table() -> str:
    table = PROJECT_TABLE.search(PYPROJECT.read_text(encoding="utf-8"))
    assert table is not None, "pyproject.toml has no [project] table"
    return table.group(1)


def declared_version() -> str:
    version = VERSION_LINE.search(project_table())
    assert version is not None, "pyproject.toml [project] declares no version"
    return version.group(1)


def released_versions() -> list[str]:
    return [match.group(1) for match in RELEASE_HEADING.finditer(
        CHANGELOG.read_text(encoding="utf-8")
    )]


def unreleased_section() -> str:
    section = UNRELEASED_SECTION.search(CHANGELOG.read_text(encoding="utf-8"))
    assert section is not None, "CHANGELOG.md has no '## [Unreleased]' section"
    return section.group(1)


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def flat(text: str) -> str:
    """Markdown prose on one line, without blockquote markers or emphasis."""
    return " ".join(text.replace(">", " ").replace("*", "").split())


def readme_installation() -> str:
    """The ``## Installation`` section of the README, up to the next ``## ``."""
    match = re.search(
        r"^## Installation\n(.*?)(?=^## )", README.read_text("utf-8"), re.M | re.S
    )
    assert match is not None, "README has no '## Installation' section"
    return match.group(1)


def release_dates() -> list[str]:
    return [match.group(2) for match in RELEASE_HEADING.finditer(
        CHANGELOG.read_text(encoding="utf-8")
    )]


def install_references(text: str) -> list[str]:
    """The version of every install reference in ``text``, in no fixed order."""
    return [
        version.rstrip(".")
        for pattern in INSTALL_REFERENCES
        for version in pattern.findall(text)
    ]


def known_versions() -> set[str]:
    """Every version this project has released or declared."""
    known = set(released_versions()) | {declared_version()}
    if RELEASE_CANDIDATE is not None:
        known.add(RELEASE_CANDIDATE)
    return known


def triggers(workflow: Path) -> str:
    """The top-level ``on:`` block of a workflow, up to the next top-level key."""
    text = workflow.read_text(encoding="utf-8")
    match = re.search(r"^on:\n(.*?)(?=^\S)", text, re.M | re.S)
    assert match is not None, f"{workflow.name} has no top-level 'on:' block"
    return match.group(1)


def job(workflow: Path, name: str) -> str:
    """The body of one job, up to the next job or the end of the file."""
    text = workflow.read_text(encoding="utf-8")
    match = re.search(rf"^  {name}:\n(.*?)(?=^  \S|\Z)", text, re.M | re.S)
    assert match is not None, f"{workflow.name} has no job {name!r}"
    return match.group(1)


# --------------------------------------------------------------------------
# Version / changelog / README pins (release candidate vs released, #31, #33)
# --------------------------------------------------------------------------


def test_the_declared_version_is_the_candidate_or_the_latest_release():
    expected = RELEASE_CANDIDATE or LATEST_PUBLISHED_RELEASE[0]
    assert declared_version() == expected, (
        f"pyproject declares {declared_version()}, but the release state pins "
        f"RELEASE_CANDIDATE={RELEASE_CANDIDATE!r} and "
        f"LATEST_PUBLISHED_RELEASE={LATEST_PUBLISHED_RELEASE!r}"
    )


def test_a_release_candidate_is_newer_than_every_dated_release():
    """A candidate never reuses, or goes back behind, a published version."""
    if RELEASE_CANDIDATE is None:
        pytest.skip("no release candidate is declared")
    for released in released_versions():
        assert version_key(RELEASE_CANDIDATE) > version_key(released), released


def test_the_newest_dated_release_is_the_latest_published_release():
    """A dated CHANGELOG section claims a release; only published ones get one."""
    version, date = LATEST_PUBLISHED_RELEASE
    changelog = CHANGELOG.read_text(encoding="utf-8")

    assert released_versions(), "CHANGELOG.md has no dated release section"
    assert released_versions()[0] == version, (
        f"newest dated CHANGELOG release is {released_versions()[0]}, but the "
        f"latest published release is {version}"
    )
    assert f"\n## [{version}] - {date}\n" in changelog
    assert released_versions().count(version) == 1


def test_the_first_public_release_is_dated_with_its_publication_date():
    version, date = FIRST_PUBLIC_RELEASE
    changelog = CHANGELOG.read_text(encoding="utf-8")

    assert f"\n## [{version}] - {date}\n" in changelog
    assert released_versions().count(version) == 1


def test_the_changelog_keeps_an_unreleased_section_above_every_release():
    changelog = CHANGELOG.read_text(encoding="utf-8")
    headings = re.findall(r"^## .*$", changelog, re.M)

    assert headings[0] == "## [Unreleased]", headings[:2]
    assert headings.count("## [Unreleased]") == 1


def test_unreleased_names_the_release_candidate_and_nothing_else():
    """The candidate's entries wait under [Unreleased], undated, targeted."""
    targets = TARGET_RELEASE_LINE.findall(unreleased_section())

    if RELEASE_CANDIDATE is None:
        assert targets == [], "[Unreleased] targets a release, but none is declared"
    else:
        assert targets == [RELEASE_CANDIDATE], (
            f"[Unreleased] must name exactly 'Target release: "
            f"{RELEASE_CANDIDATE}', found {targets}"
        )
        assert RELEASE_CANDIDATE not in released_versions(), (
            f"CHANGELOG.md dates {RELEASE_CANDIDATE}, which is not published"
        )


def test_the_changelog_no_longer_calls_a_released_version_unpublished():
    changelog = flat(CHANGELOG.read_text(encoding="utf-8"))

    assert "not yet released" not in changelog
    assert "nothing is published to TestPyPI or PyPI" not in changelog
    assert "there is no `v0.3.3` tag" not in changelog


def test_changelog_releases_are_unique_and_in_reverse_chronological_order():
    """Newest first; a version is dated once; no date goes back in time."""
    versions, dates = released_versions(), release_dates()

    assert len(versions) == len(set(versions)), versions
    assert [version_key(v) for v in versions] == sorted(
        (version_key(v) for v in versions), reverse=True
    ), versions
    assert dates == sorted(dates, reverse=True), list(zip(versions, dates))
    for date in dates:
        assert datetime.date.fromisoformat(date).isoformat() == date, date


def test_the_release_state_dates_are_consistent():
    """The latest release is the first public one or comes after it."""
    first_version, first_date = FIRST_PUBLIC_RELEASE
    latest_version, latest_date = LATEST_PUBLISHED_RELEASE

    assert version_key(latest_version) >= version_key(first_version)
    assert latest_date >= first_date
    assert datetime.date.fromisoformat(latest_date).isoformat() == latest_date


def test_every_changelog_heading_is_unreleased_or_a_dated_release():
    """A malformed heading would hide a release from the checks above."""
    changelog = CHANGELOG.read_text(encoding="utf-8")
    for heading in re.findall(r"^## .*$", changelog, re.M):
        assert heading == "## [Unreleased]" or RELEASE_HEADING.fullmatch(heading), (
            f"CHANGELOG heading {heading!r} is neither [Unreleased] nor "
            "'## [X.Y.Z] - YYYY-MM-DD'"
        )


def test_readme_install_references_all_name_the_latest_published_release():
    """No install reference, in any form or section, is stale or unpublished.

    The patterns cover requirement specifiers, Git refs, GitHub tag URLs and
    distribution file names, so a new example or a reworded one is checked
    without listing its line here.
    """
    readme = README.read_text("utf-8")
    latest = LATEST_PUBLISHED_RELEASE[0]
    found = install_references(readme)

    assert found, "README shows no pinned install reference"
    stale = sorted({version for version in found if version != latest})
    assert not stale, (
        f"README install references name {stale}; every one must name the "
        f"latest published release {latest}"
    )


def test_readme_shows_every_install_form_pinned_to_the_latest_release():
    """None of the four documented install forms is dropped or left behind."""
    installation = readme_installation()
    latest = LATEST_PUBLISHED_RELEASE[0]

    for form in INSTALL_FORMS:
        expected = form.format(version=latest)
        assert installation.count(expected) == 1, (
            f"README Installation must show {expected!r} exactly once"
        )
    assert len(install_references(installation)) == len(INSTALL_FORMS), (
        install_references(installation)
    )
    assert install_references(README.read_text("utf-8")) == install_references(
        installation
    ), "README has install references outside '## Installation'"


def test_readme_never_installs_the_package_unpinned():
    """``pip install khipu-python-sdk`` always names an exact version."""
    readme = README.read_text("utf-8")
    for line in re.findall(r"^.*pip install .*khipu[-_.]python[-_.]sdk.*$", readme, re.M | re.I):
        assert f"khipu-python-sdk=={LATEST_PUBLISHED_RELEASE[0]}" in line, line


def test_readme_names_no_release_other_than_the_latest():
    """Release history lives in the CHANGELOG, not in README prose (#46)."""
    readme = README.read_text("utf-8")
    latest = LATEST_PUBLISHED_RELEASE[0]
    mentioned = set(VERSION_TOKEN.findall(readme)) & known_versions()

    assert mentioned <= {latest}, (
        f"README mentions {sorted(mentioned - {latest})}; it may only name the "
        f"latest published release {latest}"
    )


@pytest.mark.parametrize("document", [RELEASING, CONTRIBUTING], ids=lambda p: p.name)
def test_the_release_procedure_names_no_particular_release(document):
    """The procedure is written for ``X.Y.Z`` and never needs a per-release edit."""
    text = document.read_text("utf-8")
    mentioned = set(VERSION_TOKEN.findall(text)) & known_versions()

    assert not mentioned, f"{document.name} names releases {sorted(mentioned)}"
    assert not install_references(text), install_references(text)


def test_readme_installs_the_latest_published_release_from_pypi_today():
    """The first command a reader copies is the current, unscoped pip install."""
    installation = readme_installation()
    first_command = re.search(r"```bash\n(.*?)\n```", installation, re.S)

    assert first_command is not None, "README Installation has no bash command"
    assert first_command.group(1) == (
        f"pip install khipu-python-sdk=={LATEST_PUBLISHED_RELEASE[0]}"
    )
    assert installation.lstrip().startswith("### From PyPI\n"), installation[:80]


def test_readme_never_offers_the_release_candidate():
    """A candidate is installable from nowhere until it is published."""
    if RELEASE_CANDIDATE is None:
        assert declared_version() == LATEST_PUBLISHED_RELEASE[0]
        return
    readme = README.read_text("utf-8")
    assert RELEASE_CANDIDATE not in install_references(readme)
    assert RELEASE_CANDIDATE not in VERSION_TOKEN.findall(readme)


def test_readme_releases_section_links_the_history_and_the_procedure():
    """Concise, PyPI-safe pointers instead of an accumulating history (#46)."""
    match = re.search(
        r"^## Releases\n(.*?)(?=^## )", README.read_text("utf-8"), re.M | re.S
    )
    assert match is not None, "README has no '## Releases' section"
    releases = match.group(1)

    for link in RELEASE_LINKS:
        assert f"]({link})" in releases, f"README Releases does not link {link}"
    assert "Merging to `master` does not release anything" in flat(releases)
    assert "Trusted Publishing" in releases


def test_the_release_procedure_covers_every_step_and_gate():
    """``docs/RELEASING.md`` keeps the whole procedure and its safety invariants.

    The checks name files, workflows, environments, markers and constants
    rather than prose, so the procedure can be reworded freely.
    """
    procedure = RELEASING.read_text("utf-8")
    flat_procedure = flat(procedure)

    for anchor in (
        # Release state and the release cut.
        "`project.version`",
        "`Target release: X.Y.Z`",
        "## [Unreleased]",
        "## [X.Y.Z] - YYYY-MM-DD",
        "`RELEASE_CANDIDATE",
        "`LATEST_PUBLISHED_RELEASE",
        "tests/unit/test_release_metadata.py",
        # Publication: TestPyPI rehearsal, then a GitHub Release for vX.Y.Z.
        "`.github/workflows/publish-testpypi.yml`",
        "`workflow_dispatch`",
        "`.github/workflows/publish-pypi.yml`",
        "`vX.Y.Z`",
        "GitHub Release",
        "`testpypi`",
        "`pypi`",
        # Gates that a build for an index must pass.
        "`.github/workflows/build-dist.yml`",
        "`master`",
        "`tools/check_dist.py",
        "`twine check --strict`",
        "`make smoke-dist`",
        "`PUBLICATION_GATES.toml`",
        "`LICENSE`",
        "OIDC",
        "`id-token: write`",
        # Verification and remediation.
        "https://pypi.org/pypi/khipu-python-sdk/X.Y.Z/json",
    ):
        assert anchor in procedure, f"docs/RELEASING.md no longer covers {anchor!r}"

    assert "Merging to `master` releases nothing" in flat_procedure
    assert "No PyPI API token is stored in this repository" in flat_procedure
    for heading in (
        "## 1. Release candidate",
        "## 2. Release cut",
        "## 3. TestPyPI rehearsal (optional)",
        "## 4. PyPI",
        "## 5. Verification",
        "## When the date slips or a step fails",
    ):
        assert f"\n{heading}\n" in procedure, heading


def test_the_release_procedure_is_linked_from_contributing():
    assert "docs/RELEASING.md" in CONTRIBUTING.read_text("utf-8")


def test_readme_links_the_procedure_but_does_not_duplicate_it():
    """The README keeps no copy of the step-by-step procedure."""
    readme = README.read_text("utf-8")

    assert "Target release:" not in readme
    assert "RELEASE_CANDIDATE" not in readme
    assert "LATEST_PUBLISHED_RELEASE" not in readme
    assert "Release cut" not in readme


def test_readme_has_no_pre_release_wording():
    readme = flat(README.read_text("utf-8"))

    for wording in PRE_RELEASE_WORDING:
        assert wording not in readme, wording


# --------------------------------------------------------------------------
# Public identity / disclaimer
# --------------------------------------------------------------------------


def test_readme_states_independence_from_khipu_near_the_top():
    """The README is also the PyPI project page; the disclaimer must lead it."""
    head = flat(README.read_text("utf-8")[:2000])

    assert "Community-maintained Python SDK for the Khipu API." in head
    assert "not affiliated with, endorsed by, or maintained by Khipu" in head


def test_package_summary_does_not_present_the_sdk_as_official():
    description = re.search(r'^description\s*=\s*"([^"]+)"', project_table(), re.M)
    assert description is not None
    summary = description.group(1).lower()

    assert "community-maintained" in summary and "unofficial" in summary
    assert "official sdk" not in summary


def test_distribution_and_import_names_are_frozen():
    assert re.search(r'^name\s*=\s*"khipu-python-sdk"$', project_table(), re.M)
    assert (REPO / "khipu_sdk" / "__init__.py").is_file()


def test_metadata_declares_license_maintainer_and_final_urls():
    table = project_table()

    assert re.search(r'^license\s*=\s*"MIT"$', table, re.M)
    assert re.search(r'^license-files\s*=\s*\["LICENSE"\]$', table, re.M)
    # A maintainer name only: no contact address has been approved for publication.
    assert re.search(r'^maintainers\s*=\s*\[\{ name = "Yasel Couce" \}\]$', table, re.M)

    urls = re.search(r"^\[project\.urls\]$(.*?)(?=^\[)", PYPROJECT.read_text("utf-8"), re.M | re.S)
    assert urls is not None, "pyproject.toml has no [project.urls] table"
    found = re.findall(r'=\s*"([^"]+)"', urls.group(1))
    assert found and all(url.startswith(FINAL_REPOSITORY) for url in found), found


def test_no_public_document_links_the_pre_transfer_repository():
    for path in (README, PYPROJECT, REPO / "SECURITY.md", REPO / "CONTRIBUTING.md"):
        assert "github.com/parle-cl/khipu-python-sdk" not in path.read_text("utf-8"), path


def test_python_classifiers_match_the_ci_test_matrix():
    """Advertise exactly the Python versions CI actually tests."""
    classifiers = set(re.findall(
        r'"Programming Language :: Python :: (3\.\d+)"', project_table()
    ))
    matrix = re.search(
        r"python-version:\s*\[([^\]]+)\]",
        (WORKFLOWS / "ci.yml").read_text("utf-8"),
    )
    assert matrix is not None, "ci.yml has no python-version matrix"
    tested = set(re.findall(r'"(3\.\d+)"', matrix.group(1)))

    assert classifiers == tested, f"classifiers {classifiers} vs CI {tested}"
    assert '"Typing :: Typed"' in project_table()


# --------------------------------------------------------------------------
# Deliberate release workflows
# --------------------------------------------------------------------------


def test_no_workflow_releases_on_merge_or_push():
    """The old 'every merge to master is a release' workflow must not return.

    No workflow may write repository contents (tags, releases), and none may
    tag or create a GitHub Release. Publishing to an index only happens in the
    two publish workflows, which are checked below.
    """
    assert not (WORKFLOWS / "release-on-merge.yml").exists()

    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        text = workflow.read_text("utf-8")
        assert "contents: write" not in text, workflow.name
        assert not re.search(r"git (tag|push)\b", text), workflow.name
        assert "action-gh-release" not in text, workflow.name
        assert "gh release create" not in text, workflow.name

        if "pypa/gh-action-pypi-publish" in text:
            assert workflow in (TESTPYPI_WORKFLOW, PYPI_WORKFLOW), workflow.name


def test_workflows_pin_actions_runners_and_drop_checkout_credentials():
    """What a workflow runs cannot change without a reviewed edit (#37).

    - every action other than the local build-dist.yml is pinned to a full
      commit SHA, with its release in a trailing ``# vX.Y.Z`` comment, so a
      moved or re-pointed tag cannot swap the code that builds or publishes;
    - every job names an explicit runner image, never a floating ``-latest``
      label that GitHub relabels on its own schedule;
    - no checkout leaves the job token in the workspace for later steps.
    """
    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        text = workflow.read_text("utf-8")

        for ref in re.findall(r"^\s+(?:- )?uses: (\S+.*)$", text, re.M):
            if ref.startswith("./.github/workflows/"):
                continue
            assert re.fullmatch(
                r"[\w.-]+/[\w.-]+@[0-9a-f]{40}  # v\d+\.\d+\.\d+", ref
            ), f"{workflow.name}: {ref!r} is not pinned to a commit SHA"

        runners = re.findall(r"^\s+runs-on: (\S+)$", text, re.M)
        assert len(runners) == text.count("runs-on:"), workflow.name
        for runner in runners:
            assert re.fullmatch(r"ubuntu-\d\d\.\d\d", runner), (
                f"{workflow.name}: runs-on {runner!r} is not a pinned image"
            )

        checkouts = re.findall(
            r"uses: actions/checkout@\S+.*\n((?: {8,}\S.*\n)*)", text
        )
        for options in checkouts:
            assert "persist-credentials: false" in options, (
                f"{workflow.name}: a checkout persists the job token"
            )
        assert "persist-credentials: true" not in text, workflow.name

    # Every job of every workflow is on the same image.
    images = {
        runner
        for workflow in WORKFLOWS.glob("*.y*ml")
        for runner in re.findall(r"runs-on: (\S+)", workflow.read_text("utf-8"))
    }
    assert len(images) == 1, images


def test_dependabot_proposes_github_actions_updates_and_nothing_else():
    """Dependabot only watches the pinned actions, weekly, a few PRs at a time (#39).

    The configuration is compared as a whole (comments aside), so adding an
    ecosystem, a private registry, ``insecure-external-code-execution``, a
    different target branch or any other option is a reviewed edit of this
    test. Whether GitHub actually raises update PRs is server-side behavior
    and cannot be checked offline; the SHA/version-comment form Dependabot
    rewrites is pinned by the test above.
    """
    assert sorted(p.name for p in DEPENDABOT.parent.glob("dependabot.y*ml")) == [
        "dependabot.yml"
    ]
    for other in ("renovate.json", "renovate.json5", ".renovaterc", ".renovaterc.json"):
        assert not (REPO / other).exists(), other
        assert not (REPO / ".github" / other).exists(), other

    lines = [
        line.rstrip()
        for line in DEPENDABOT.read_text("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lines == [
        "version: 2",
        "updates:",
        '  - package-ecosystem: "github-actions"',
        '    directory: "/"',
        "    schedule:",
        '      interval: "weekly"',
        "    open-pull-requests-limit: 3",
        "    commit-message:",
        '      prefix: "ci"',
    ]


def test_no_workflow_approves_or_merges_pull_requests():
    """Dependency update PRs are reviewed and merged by the maintainer only (#39).

    No workflow runs on ``pull_request_target`` (which would hand a PR's
    workflow run a write token and secrets), asks for write access to pull
    requests, or approves, auto-merges or merges a PR.
    """
    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        text = workflow.read_text("utf-8")
        assert "pull_request_target" not in text, workflow.name
        assert "pull-requests: write" not in text, workflow.name
        assert "dependabot/fetch-metadata" not in text, workflow.name
        assert not re.search(r"gh pr (merge|review)\b", text), workflow.name
        assert "auto-merge" not in text, workflow.name
        assert "--auto" not in text, workflow.name


@pytest.mark.parametrize(
    ("workflow", "trigger"),
    [
        (TESTPYPI_WORKFLOW, "  workflow_dispatch:"),
        (PYPI_WORKFLOW, "  release:\n    types: [published]"),
    ],
)
def test_publish_workflows_have_exactly_one_deliberate_trigger(workflow, trigger):
    on = triggers(workflow)
    events = re.findall(r"^  (\w+):", on, re.M)

    assert len(events) == 1, f"{workflow.name} triggers on {events}"
    assert on.startswith(trigger), on


@pytest.mark.parametrize(
    ("workflow", "environment", "repository_url"),
    [
        (TESTPYPI_WORKFLOW, "testpypi", "https://test.pypi.org/legacy/"),
        (PYPI_WORKFLOW, "pypi", None),
    ],
)
def test_publish_job_uses_trusted_publishing_with_least_privilege(
    workflow, environment, repository_url
):
    text = workflow.read_text("utf-8")
    publish = job(workflow, "publish")

    # Trusted Publishing: the OIDC permission, the environment the trusted
    # publisher is bound to, and no token passed to the action.
    assert f"name: {environment}\n" in publish
    assert re.search(
        r"permissions:\n\s+contents: read\n\s+id-token: write\b", publish
    ), publish
    assert re.search(r"^permissions:\n  contents: read\n", text, re.M)
    assert "secrets." not in text
    assert "password:" not in text
    assert re.search(r"uses: pypa/gh-action-pypi-publish@[0-9a-f]{40}\b", publish)

    if repository_url is None:
        assert "repository-url" not in publish
    else:
        assert f"repository-url: {repository_url}" in publish

    # id-token is granted to the publish job alone.
    assert text.count("id-token: write") == 1


def test_publish_workflows_build_and_check_through_the_shared_workflow():
    for workflow in (TESTPYPI_WORKFLOW, PYPI_WORKFLOW):
        build = job(workflow, "build")
        assert "uses: ./.github/workflows/build-dist.yml" in build, workflow.name
        assert "needs: build" in job(workflow, "publish"), workflow.name

    # The production tag must be the release's tag; TestPyPI checks the
    # dispatched version. Neither caller says what to build (see below).
    pypi_build = job(PYPI_WORKFLOW, "build")
    assert "tag: ${{ github.event.release.tag_name }}" in pypi_build
    testpypi_build = job(TESTPYPI_WORKFLOW, "build")
    assert "tag: v${{ inputs.version }}" in testpypi_build

    shared = BUILD_WORKFLOW.read_text("utf-8")
    assert re.search(r"^  workflow_call:", triggers(BUILD_WORKFLOW), re.M)
    assert "id-token" not in shared
    assert "make smoke-dist" in shared
    assert 'tools/check_dist.py dist --tag "$TAG"' in shared
    assert "twine check --strict" in shared
    assert "git merge-base --is-ancestor HEAD origin/master" in shared


def test_every_build_for_an_index_is_on_master_before_repository_code_runs():
    """Both TestPyPI and PyPI build only commits already on master (Issue #28).

    - no caller can opt out: the shared workflow has no input that disables
      the ancestry check, and neither caller passes one;
    - the check step is unconditional;
    - it is the first step after checkout, so no step that can execute code
      from the checked-out tree (pip, the Makefile, tools/*.py) runs before
      the commit is known to be reviewed code on master.
    """
    for workflow in (BUILD_WORKFLOW, TESTPYPI_WORKFLOW, PYPI_WORKFLOW):
        assert "require-on-master" not in workflow.read_text("utf-8"), workflow.name

    steps = re.split(r"^      - name: ", job(BUILD_WORKFLOW, "build"), flags=re.M)[1:]
    names = [step.split("\n", 1)[0] for step in steps]
    assert names[:2] == ["Checkout", "Require the commit to be on master"], names

    check = steps[1]
    assert "if:" not in check, "the master-ancestry check must not be conditional"
    assert "git merge-base --is-ancestor HEAD origin/master" in check
    assert "exit 1" in check
    assert "fetch-depth: 0" in steps[0]


def test_no_caller_can_choose_the_commit_a_release_build_checks_out():
    """The release build only ever builds the triggering event's commit (Issue #28).

    ``build-dist.yml`` used to take the ref to build as an input, so whatever
    a caller passed was checked out and executed in the build job (the source
    of the CodeQL cache-poisoning alerts). It now accepts only the release tag
    string, which is never checked out or executed, and every checkout in the
    release workflows uses the event's own immutable commit (GITHUB_SHA).
    """
    inputs = re.search(
        r"^  workflow_call:\n(?:    #[^\n]*\n)*    inputs:\n(.*?)(?=^  \S|^\S|\Z)",
        triggers(BUILD_WORKFLOW) + "\n",
        re.M | re.S,
    )
    assert inputs is not None, "build-dist.yml declares no workflow_call inputs"
    assert re.findall(r"^      (\S+):", inputs.group(1), re.M) == ["tag"]

    for workflow in (TESTPYPI_WORKFLOW, PYPI_WORKFLOW):
        build = job(workflow, "build")
        passed = re.findall(r"^      (\S+):", build.split("    with:\n", 1)[1], re.M)
        assert passed == ["tag"], f"{workflow.name} passes {passed} to build-dist.yml"

    for workflow in (BUILD_WORKFLOW, TESTPYPI_WORKFLOW, PYPI_WORKFLOW):
        text = workflow.read_text("utf-8")
        checkouts = re.findall(
            r"uses: actions/checkout@\S+(?:  # \S+)?\n"
            r"(?:        with:\n((?:          .*\n)+))?",
            text,
        )
        assert checkouts, workflow.name
        for options in checkouts:
            assert not re.search(r"^\s+(ref|repository):", options, re.M), (
                f"{workflow.name} checks out something other than the event's commit"
            )


# --------------------------------------------------------------------------
# The master-ancestry gate, executed
# --------------------------------------------------------------------------


def master_gate_script() -> str:
    """The shell script of build-dist.yml's 'Require the commit to be on master'."""
    build = job(BUILD_WORKFLOW, "build")
    match = re.search(
        r"^      - name: Require the commit to be on master\n        run: \|\n"
        r"((?:          .*\n|\n)+)",
        build,
        re.M,
    )
    assert match is not None, "build-dist.yml has no master-ancestry step"
    return textwrap.dedent(match.group(1))


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def release_checkout(tmp_path):
    """A clone shaped like the build job's: full history, ``origin/master``.

    Upstream has two reviewed commits on master, a side branch with an
    unreviewed commit, a tag on master and a tag on the side branch.
    """
    if shutil.which("git") is None:
        pytest.skip("git is not installed")

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "-q", "-b", "master")
    git(upstream, "config", "user.name", "Test")
    git(upstream, "config", "user.email", "test@example.invalid")
    git(upstream, "config", "commit.gpgsign", "false")
    git(upstream, "config", "tag.gpgsign", "false")
    for message in ("reviewed 1", "reviewed 2"):
        git(upstream, "commit", "-q", "--allow-empty", "-m", message)
    git(upstream, "tag", "-a", "v9.9.9", "-m", "on master")
    git(upstream, "checkout", "-q", "-b", "side")
    git(upstream, "commit", "-q", "--allow-empty", "-m", "unreviewed")
    git(upstream, "tag", "-a", "v9.9.8", "-m", "on a side branch")
    git(upstream, "checkout", "-q", "master")

    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(upstream), str(clone))
    git(clone, "fetch", "-q", "--tags", "origin")
    return clone


def run_master_gate(clone: Path, checked_out: str, github_sha: str):
    git(clone, "checkout", "-q", "--detach", checked_out)
    sha = git(clone, "rev-parse", f"{github_sha}^{{commit}}")
    return subprocess.run(
        ["bash", "-e", "-c", master_gate_script()],
        cwd=clone,
        env={"PATH": os.environ["PATH"], "GITHUB_SHA": sha},
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "ref",
    ["origin/master", "origin/master~1", "v9.9.9"],
    ids=["master-tip", "older-master-commit", "release-tag-on-master"],
)
def test_master_gate_accepts_reviewed_commits(release_checkout, ref):
    result = run_master_gate(release_checkout, ref, ref)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "ref",
    ["origin/side", "v9.9.8"],
    ids=["side-branch-dispatch", "release-tag-on-side-branch"],
)
def test_master_gate_rejects_commits_not_on_master(release_checkout, ref):
    result = run_master_gate(release_checkout, ref, ref)
    assert result.returncode != 0
    assert "is not on master; refusing to publish it." in result.stdout


def test_master_gate_rejects_a_checkout_other_than_the_triggering_commit(
    release_checkout,
):
    """Even a reviewed commit is refused if it is not the event's commit."""
    result = run_master_gate(release_checkout, "origin/master~1", "origin/master")
    assert result.returncode != 0
    assert "refusing to publish it." in result.stdout


def test_no_publish_path_can_skip_the_release_check():
    """Upload only artifacts that passed ``check_dist.py --tag`` (Issue #18 gates).

    - every workflow that can upload to an index is one of the two publish
      workflows, and its only publishing job needs the shared build;
    - the publish job never builds anything itself, it only downloads the
      artifact the shared build uploaded;
    - in build-dist.yml the release check is unconditional, cannot be
      soft-failed, and runs before the artifact is uploaded.
    """
    for workflow in (TESTPYPI_WORKFLOW, PYPI_WORKFLOW):
        text = workflow.read_text("utf-8")
        publish = job(workflow, "publish")

        assert text.count("pypa/gh-action-pypi-publish") == 1, workflow.name
        assert "pypa/gh-action-pypi-publish" in publish, workflow.name
        assert re.search(r"^    needs: build$", publish, re.M), workflow.name
        assert "continue-on-error" not in text, workflow.name
        assert "always()" not in text, workflow.name
        for builder in ("python -m build", "make build", "make smoke-dist", "twine upload"):
            assert builder not in publish, f"{workflow.name} publish job runs {builder!r}"
        assert "uses: actions/download-artifact@" in publish, workflow.name

    shared = BUILD_WORKFLOW.read_text("utf-8")
    assert "continue-on-error" not in shared
    check = shared.index('tools/check_dist.py dist --tag "$TAG"')
    upload = shared.index("uses: actions/upload-artifact@")
    assert check < upload, "the artifact must be uploaded only after the release check"

    step = shared[shared.rindex("- name:", 0, check):check]
    assert "if:" not in step, "the release check must not be conditional"
