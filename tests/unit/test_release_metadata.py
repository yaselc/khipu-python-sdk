"""Release metadata must stay internally consistent.

``.github/workflows/release-on-merge.yml`` reads ``project.version`` from
``pyproject.toml``, forms the tag ``v<version>``, and **skips tag creation when
that tag already exists**. Merging to master without bumping the version
therefore lands new code that downstream applications have no new tag to pin --
silently, with a green build.

The same workflow builds its release notes by locating ``## [<version>]`` in
CHANGELOG.md, and falls back to a stub when that heading is missing.

These tests are cheap and offline: they only read files in the repository.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
CHANGELOG = REPO / "CHANGELOG.md"
README = REPO / "README.md"

#: ``## [1.2.3] - 2026-09-22`` -- a released section, not ``## [Unreleased]``.
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.M)


def declared_version() -> str:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def unreleased_section() -> str:
    """The body under ``## [Unreleased]``, minus headings and the _TBD_ stub."""
    text = CHANGELOG.read_text(encoding="utf-8")
    start = text.find("## [Unreleased]")
    if start == -1:
        return ""
    end = text.find("\n## [", start + len("## [Unreleased]"))
    section = text[start:] if end == -1 else text[start:end]

    kept = [
        line
        for line in section.splitlines()[1:]
        if line.strip() and not line.startswith("#") and line.strip() != "- _TBD_"
    ]
    return "\n".join(kept).strip()


def released_versions() -> list[str]:
    return [match.group(1) for match in RELEASE_HEADING.finditer(
        CHANGELOG.read_text(encoding="utf-8")
    )]


def test_the_declared_version_has_a_dated_changelog_section():
    """Without this heading the release workflow ships a stub for release notes."""
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
    """A README still pinning the previous tag sends consumers to old code."""
    pinned = set(
        re.findall(r"khipu-python-sdk\.git@v(\d+\.\d+\.\d+)", README.read_text("utf-8"))
    )

    assert pinned, "README no longer shows a pinned install example"
    assert pinned == {declared_version()}, (
        f"README pins {sorted(pinned)}; pyproject declares {declared_version()}"
    )


def test_no_changes_are_left_sitting_in_unreleased():
    """This repository tags a release from every merge to master.

    ``release-on-merge.yml`` runs on every push to master, reads the version
    from pyproject.toml and tags it -- unless that tag already exists, in which
    case it silently does nothing. So changes merged while still filed under
    ``## [Unreleased]`` land on master with no tag for a consumer to pin, and
    the release notes for whatever tag does exist will not mention them.

    Cutting the section into ``## [<version>] - <date>`` and bumping
    ``project.version`` is what makes the merge releasable.
    """
    leftover = unreleased_section()

    assert not leftover, (
        "CHANGELOG.md still has entries under '## [Unreleased]'. Move them into "
        f"a '## [<version>] - <date>' section and bump project.version (now "
        f"{declared_version()}, already tagged as v{declared_version()}):\n"
        f"{leftover}"
    )
