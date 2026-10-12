"""Release metadata and the release process must stay deliberate and consistent.

Publication is an explicit maintainer action (Issue #18):

- ``.github/workflows/publish-testpypi.yml`` runs only on ``workflow_dispatch``;
- ``.github/workflows/publish-pypi.yml`` runs only when a GitHub Release is
  published, and only for a tag equal to ``v<project.version>``;
- merging or pushing to master publishes, tags and releases nothing.

These tests pin that contract, plus the metadata a PyPI release depends on:
the CHANGELOG documents the declared version, README install pins name that
version, and the README/package metadata keep the independence disclaimer.

The declared version is a release *candidate*, not proof of publication
(Issue #22). Until 0.3.3 is actually on PyPI and tag ``v0.3.3`` exists, the
CHANGELOG keeps its entries under ``## [Unreleased]`` as the target release
(no dated heading), the README says it is not yet published, and its install
commands are scoped to after the release. That state cannot be observed
offline, so it is pinned here as an explicit contract (``PLANNED_RELEASE`` /
``LATEST_EXISTING_TAG``). Once 0.3.3 is genuinely released, a follow-up PR
cuts the entries into ``## [0.3.3] - <release date>``, removes the README's
pre-release note, makes the install commands current and replaces the
pre-release tests below with the released-state contract.

The workflow checks read the YAML as text on purpose: the files are small, the
checked lines are distinctive, and the dev environment has no YAML parser.

These tests are cheap and offline: they only read files in the repository.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
CHANGELOG = REPO / "CHANGELOG.md"
README = REPO / "README.md"
WORKFLOWS = REPO / ".github" / "workflows"
TESTPYPI_WORKFLOW = WORKFLOWS / "publish-testpypi.yml"
PYPI_WORKFLOW = WORKFLOWS / "publish-pypi.yml"
BUILD_WORKFLOW = WORKFLOWS / "build-dist.yml"

FINAL_REPOSITORY = "https://github.com/yaselc/khipu-python-sdk"

#: The declared release candidate, not yet published anywhere (Issue #22).
PLANNED_RELEASE = "0.3.3"
#: The newest tag that actually exists. ``v<PLANNED_RELEASE>`` does not yet.
LATEST_EXISTING_TAG = "v0.3.2"
#: How the README scopes every install command for ``PLANNED_RELEASE``.
POST_RELEASE_SCOPE = f"(after {PLANNED_RELEASE} is released)"

PYPI_PIN = re.compile(r"khipu-python-sdk==(\d+\.\d+\.\d+)")
GIT_PIN = re.compile(r"khipu-python-sdk\.git@v(\d+\.\d+\.\d+)")

#: ``## [1.2.3] - 2026-09-22`` -- a released section, not ``## [Unreleased]``.
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.M)


#: The ``version = "..."`` line inside the ``[project]`` table. Read with a
#: regex rather than ``tomllib``, which is stdlib only from Python 3.11 while
#: this package supports 3.10.
PROJECT_TABLE = re.compile(r"^\[project\]$(.*?)(?=^\[)", re.M | re.S)
VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)

#: The ``## [Unreleased]`` section, up to the next ``## `` heading.
UNRELEASED_SECTION = re.compile(r"^## \[Unreleased\]\n(.*?)(?=^## )", re.M | re.S)
#: How ``## [Unreleased]`` names the version its entries will ship as.
TARGET_RELEASE_LINE = re.compile(r"^Target release: (\d+\.\d+\.\d+)$", re.M)


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


def unreleased_target() -> str:
    section = UNRELEASED_SECTION.search(CHANGELOG.read_text(encoding="utf-8"))
    assert section is not None, "CHANGELOG.md has no '## [Unreleased]' section"
    targets = TARGET_RELEASE_LINE.findall(section.group(1))
    assert len(targets) == 1, (
        f"'## [Unreleased]' must name exactly one 'Target release: X.Y.Z', "
        f"found {targets}"
    )
    return targets[0]


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
# Version / changelog (pre-release, Issue #22) / README pins
# --------------------------------------------------------------------------


def test_the_declared_version_is_the_unreleased_target_release():
    """Pre-release: the candidate's entries live under [Unreleased], targeted."""
    assert declared_version() == PLANNED_RELEASE, (
        f"pyproject declares {declared_version()}; the pre-release contract "
        f"still describes {PLANNED_RELEASE}"
    )
    assert unreleased_target() == declared_version(), (
        f"CHANGELOG [Unreleased] targets {unreleased_target()}, but pyproject "
        f"declares {declared_version()}"
    )


def test_the_declared_version_has_no_released_changelog_section():
    """A dated heading claims a release; 0.3.3 has not been released."""
    assert declared_version() not in released_versions(), (
        f"CHANGELOG.md has a dated '## [{declared_version()}] - <date>' section, "
        f"but {declared_version()} is not released yet"
    )


def test_the_newest_released_changelog_section_is_the_latest_existing_tag():
    """The newest dated section is the newest release that actually exists."""
    assert f"v{released_versions()[0]}" == LATEST_EXISTING_TAG, (
        f"newest dated CHANGELOG release is {released_versions()[0]}, but the "
        f"latest existing tag is {LATEST_EXISTING_TAG}"
    )


def test_readme_install_pins_point_at_the_declared_version():
    """A README still pinning the previous release sends consumers to old code.

    Every pin names the declared version -- never an older, existing tag such
    as ``v0.3.2`` -- and every pin lives in the Installation section, where
    the pre-release tests below can scope it.
    """
    readme = README.read_text("utf-8")
    pypi_pins = set(PYPI_PIN.findall(readme))
    git_pins = set(GIT_PIN.findall(readme))

    assert pypi_pins, "README no longer shows a pinned PyPI install example"
    assert git_pins, "README no longer shows a pinned Git install example"
    assert pypi_pins | git_pins == {declared_version()}, (
        f"README pins {sorted(pypi_pins | git_pins)}; pyproject declares "
        f"{declared_version()}"
    )

    installation = readme_installation()
    for pin in (PYPI_PIN, GIT_PIN):
        assert len(pin.findall(installation)) == len(pin.findall(readme)), (
            f"README has {pin.pattern!r} install pins outside '## Installation'"
        )


# --------------------------------------------------------------------------
# Pre-release README contract (Issue #22) -- replace once 0.3.3 is released
# --------------------------------------------------------------------------


def test_readme_states_the_pre_release_status_before_any_install_command():
    """The candidate version is not a published release, and the README says so."""
    installation = readme_installation()
    status = flat(installation[: installation.index("\n### ")])

    assert f"`{PLANNED_RELEASE}` is the next planned release" in status
    assert "the first planned public PyPI release" in status
    assert "It is not yet published" in status
    assert f"tag `v{PLANNED_RELEASE}` does not yet exist" in status
    assert f"The latest existing tag is `{LATEST_EXISTING_TAG}`" in status
    assert f"are for use after {PLANNED_RELEASE} is released" in status


def test_readme_install_commands_are_scoped_to_after_the_release():
    """No 0.3.3 install command may read as executable today."""
    subsections = re.split(r"^### ", readme_installation(), flags=re.M)[1:]
    pinned = [
        section for section in subsections
        if PYPI_PIN.search(section) or GIT_PIN.search(section)
    ]

    assert pinned, "README Installation has no pinned install subsection"
    for section in pinned:
        heading = section.splitlines()[0]
        assert heading.endswith(POST_RELEASE_SCOPE), (
            f"install subsection {heading!r} is not scoped {POST_RELEASE_SCOPE!r}"
        )
        before_first_command = flat(section[: section.index("```")])
        assert f"After {PLANNED_RELEASE} is released" in before_first_command or (
            f"After tag `v{PLANNED_RELEASE}` is created" in before_first_command
        ), heading


def test_readme_has_no_false_install_from_the_same_tag_fallback():
    """``v0.3.3`` does not exist either, so 'use the tag instead' is false."""
    readme = flat(README.read_text("utf-8"))

    assert "same tag from source" not in readme
    assert "has not been published to PyPI yet; install" not in readme


def test_readme_records_the_post_release_follow_up():
    """The transition to released-state docs is a written release step."""
    readme = flat(README.read_text("utf-8"))

    step = readme[readme.index(f"First public release only ({PLANNED_RELEASE}).") :]
    step = step[: step.index("Both workflows publish")]

    assert "stay under `## [Unreleased]` as its target release" in step
    assert (
        f"cuts the {PLANNED_RELEASE} entries from `## [Unreleased]` into a dated "
        f"`## [{PLANNED_RELEASE}] - YYYY-MM-DD` section carrying the actual "
        "release date"
    ) in step
    assert "removes the Pre-release status note" in step
    assert "makes the install commands current" in step
    assert "tests/unit/test_release_metadata.py` to released-state semantics" in step


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

    # The production tag must be the release's tag, built from that tag, and on master.
    pypi_build = job(PYPI_WORKFLOW, "build")
    assert "ref: refs/tags/${{ github.event.release.tag_name }}" in pypi_build
    assert "tag: ${{ github.event.release.tag_name }}" in pypi_build
    assert "require-on-master: true" in pypi_build
    assert "tag: v${{ inputs.version }}" in job(TESTPYPI_WORKFLOW, "build")

    shared = BUILD_WORKFLOW.read_text("utf-8")
    assert re.search(r"^  workflow_call:", triggers(BUILD_WORKFLOW), re.M)
    assert "id-token" not in shared
    assert "make smoke-dist" in shared
    assert 'tools/check_dist.py dist --tag "$TAG"' in shared
    assert "twine check --strict" in shared
    assert "git merge-base --is-ancestor HEAD origin/master" in shared


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
