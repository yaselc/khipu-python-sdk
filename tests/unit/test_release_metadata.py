"""Release metadata and the release process must stay deliberate and consistent.

Publication is an explicit maintainer action (Issue #18):

- ``.github/workflows/publish-testpypi.yml`` runs only on ``workflow_dispatch``;
- ``.github/workflows/publish-pypi.yml`` runs only when a GitHub Release is
  published, and only for a tag equal to ``v<project.version>``;
- merging or pushing to master publishes, tags and releases nothing.

These tests pin that contract, plus the metadata a PyPI release depends on:
the declared version has a dated CHANGELOG section, README install pins name
that version, and the README/package metadata keep the independence
disclaimer.

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

#: ``## [1.2.3] - 2026-09-22`` -- a released section, not ``## [Unreleased]``.
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.M)


#: The ``version = "..."`` line inside the ``[project]`` table. Read with a
#: regex rather than ``tomllib``, which is stdlib only from Python 3.11 while
#: this package supports 3.10.
PROJECT_TABLE = re.compile(r"^\[project\]$(.*?)(?=^\[)", re.M | re.S)
VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)


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
# Version / changelog / README pins
# --------------------------------------------------------------------------


def test_the_declared_version_has_a_dated_changelog_section():
    """A release with no changelog section ships with nothing to read."""
    assert declared_version() in released_versions(), (
        f"pyproject declares {declared_version()} but CHANGELOG.md has no "
        f"'## [{declared_version()}] - <date>' section"
    )


def test_the_declared_version_is_the_newest_changelog_section():
    """Catches a CHANGELOG release written without bumping pyproject."""
    assert released_versions()[0] == declared_version(), (
        f"newest CHANGELOG release is {released_versions()[0]}, but pyproject "
        f"declares {declared_version()}"
    )


def test_readme_install_pins_point_at_the_declared_version():
    """A README still pinning the previous release sends consumers to old code."""
    readme = README.read_text("utf-8")
    pypi_pins = set(re.findall(r"khipu-python-sdk==(\d+\.\d+\.\d+)", readme))
    git_pins = set(re.findall(r"khipu-python-sdk\.git@v(\d+\.\d+\.\d+)", readme))

    assert pypi_pins, "README no longer shows a pinned PyPI install example"
    assert git_pins, "README no longer shows a pinned Git install example"
    assert pypi_pins | git_pins == {declared_version()}, (
        f"README pins {sorted(pypi_pins | git_pins)}; pyproject declares "
        f"{declared_version()}"
    )


# --------------------------------------------------------------------------
# Public identity / disclaimer
# --------------------------------------------------------------------------


def test_readme_states_independence_from_khipu_near_the_top():
    """The README is also the PyPI project page; the disclaimer must lead it."""
    head = README.read_text("utf-8")[:2000]
    flat = " ".join(head.replace(">", " ").replace("*", "").split())

    assert "Community-maintained Python SDK for the Khipu API." in flat
    assert "not affiliated with, endorsed by, or maintained by Khipu" in flat


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
