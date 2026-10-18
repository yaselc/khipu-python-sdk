"""Release metadata and the release process must stay deliberate and consistent.

Publication is an explicit maintainer action (Issue #18):

- ``.github/workflows/publish-testpypi.yml`` runs only on ``workflow_dispatch``;
- ``.github/workflows/publish-pypi.yml`` runs only when a GitHub Release is
  published, and only for a tag equal to ``v<project.version>``;
- merging or pushing to master publishes, tags and releases nothing.

These tests pin that contract, plus the metadata a PyPI release depends on:
the CHANGELOG documents the declared version, README install pins name a
version that is actually published, and the README/package metadata keep the
independence disclaimer.

Publication cannot be observed offline, so the release state is pinned here:

- ``LATEST_PUBLISHED_RELEASE`` is the newest version on PyPI and its date. It
  is the newest dated CHANGELOG section and the version every README install
  command names.
- ``RELEASE_CANDIDATE`` is the declared ``project.version`` while it is not yet
  tagged or uploaded (0.3.4, Issue #33), or ``None`` when the declared version
  is the latest published release. A candidate has no dated CHANGELOG section,
  is named as ``Target release:`` under ``## [Unreleased]``, and the README
  never offers to install it.

The release cut (README "Releases", step 2) moves the declared version from
one to the other: it dates the CHANGELOG section, points the README install
commands at the new version, sets ``LATEST_PUBLISHED_RELEASE`` to it and
``RELEASE_CANDIDATE`` to ``None``. 0.3.3, the first public release, was
published on 2026-10-17 (Issue #31); before that it was a candidate too (#22).

The release cut is merged *before* the upload, because the README it freezes
becomes the PyPI project description. From that merge until the upload,
``LATEST_PUBLISHED_RELEASE`` is the intended publication (version and date),
not evidence that the index already has it; these offline tests cannot tell
the difference. 0.3.4 is in that state after its release cut (Issue #35),
dated for publication on 2026-10-18. If publication slips, the CHANGELOG date
and this constant are corrected together before tagging or uploading.

The workflow checks read the YAML as text on purpose: the files are small, the
checked lines are distinctive, and the dev environment has no YAML parser.

These tests are cheap and offline: they read files in the repository, and the
master-ancestry gate of ``build-dist.yml`` is executed against throwaway git
repositories under ``tmp_path``.
"""

from __future__ import annotations

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
WORKFLOWS = REPO / ".github" / "workflows"
TESTPYPI_WORKFLOW = WORKFLOWS / "publish-testpypi.yml"
PYPI_WORKFLOW = WORKFLOWS / "publish-pypi.yml"
BUILD_WORKFLOW = WORKFLOWS / "build-dist.yml"

FINAL_REPOSITORY = "https://github.com/yaselc/khipu-python-sdk"

#: The first release published to PyPI, and the date it was published (#31).
FIRST_PUBLIC_RELEASE = ("0.3.3", "2026-10-17")

#: The newest release published to PyPI, and the date it was published. After
#: a release cut and before its upload, the intended publication (#35).
LATEST_PUBLISHED_RELEASE = ("0.3.4", "2026-10-18")

#: ``project.version`` while it is prepared but not tagged or uploaded (#33);
#: ``None`` when the declared version is ``LATEST_PUBLISHED_RELEASE``.
RELEASE_CANDIDATE: str | None = None

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


def test_readme_install_pins_point_at_the_latest_published_release():
    """Every pin names a version a reader can install today.

    Never an older tag such as ``v0.3.2``, never an unpublished candidate, and
    every pin lives in the Installation section.
    """
    readme = README.read_text("utf-8")
    pypi_pins = set(PYPI_PIN.findall(readme))
    git_pins = set(GIT_PIN.findall(readme))
    latest = LATEST_PUBLISHED_RELEASE[0]

    assert pypi_pins, "README no longer shows a pinned PyPI install example"
    assert git_pins, "README no longer shows a pinned Git install example"
    assert pypi_pins | git_pins == {latest}, (
        f"README pins {sorted(pypi_pins | git_pins)}; the latest published "
        f"release is {latest}"
    )

    installation = readme_installation()
    for pin in (PYPI_PIN, GIT_PIN):
        assert len(pin.findall(installation)) == len(pin.findall(readme)), (
            f"README has {pin.pattern!r} install pins outside '## Installation'"
        )


def test_readme_installs_the_latest_published_release_from_pypi_today():
    """The first command a reader copies is the current, unscoped pip install."""
    installation = readme_installation()
    first_command = re.search(r"```bash\n(.*?)\n```", installation, re.S)

    assert first_command is not None, "README Installation has no bash command"
    assert first_command.group(1) == (
        f"pip install khipu-python-sdk=={LATEST_PUBLISHED_RELEASE[0]}"
    )
    assert installation.lstrip().startswith("### From PyPI\n"), installation[:80]


def test_readme_states_the_release_candidate_without_offering_it():
    """A candidate is described as one, and only while there is one."""
    readme = flat(README.read_text("utf-8"))

    if RELEASE_CANDIDATE is None:
        latest = LATEST_PUBLISHED_RELEASE[0]
        assert "is at step 1" not in readme
        assert f"there is no `v{latest}` tag" not in readme
        assert "the install commands above still name" not in readme
        return
    assert f"khipu-python-sdk=={RELEASE_CANDIDATE}" not in readme
    assert f"khipu-python-sdk.git@v{RELEASE_CANDIDATE}" not in readme
    assert f"{RELEASE_CANDIDATE}, a documentation and package-metadata release" in readme
    assert f"is at step 1: `project.version` is {RELEASE_CANDIDATE}" in readme
    assert f"there is no `v{RELEASE_CANDIDATE}` tag" in readme
    assert f"the install commands above still name {LATEST_PUBLISHED_RELEASE[0]}" in readme


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
