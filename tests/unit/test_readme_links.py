"""The README is also the PyPI project page, so its links must work there (#31).

``pyproject.toml`` ships ``README.md`` as the package's long description, and
PyPI renders it with no knowledge of the repository: a target relative to the
repository, such as ``LICENSE`` or ``docs/guide.md``, resolves on GitHub and is
broken on PyPI. 0.3.3 was published with five such links.

``tools/check_dist.py`` rejects them in the long description of the built
wheel and sdist, which is the exact text PyPI receives. These tests pin that
checker against synthetic cases and apply it to the README the package
metadata names, so a relative link fails ``pytest`` before anything is built.

Offline: no URL is fetched. Whether an absolute URL is live is not checked.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
CHECK_DIST = REPO / "tools" / "check_dist.py"

#: ``readme = "..."`` inside ``[project]``, read like test_release_metadata.py
#: does (no ``tomllib`` on Python 3.10).
PROJECT_TABLE = re.compile(r"^\[project\]$(.*?)(?=^\[)", re.M | re.S)
README_LINE = re.compile(r'^readme\s*=\s*"([^"]+)"', re.M)

#: A Markdown ATX heading, as GitHub and PyPI both anchor it.
HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)[ \t#]*$", re.M)


def load_check_dist() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_dist", CHECK_DIST)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_dist = load_check_dist()


def long_description_source() -> Path:
    """The file ``pyproject.toml`` publishes as the long description."""
    table = PROJECT_TABLE.search(PYPROJECT.read_text(encoding="utf-8"))
    assert table is not None, "pyproject.toml has no [project] table"
    readme = README_LINE.search(table.group(1))
    assert readme is not None, "pyproject.toml [project] declares no readme"
    return REPO / readme.group(1)


def heading_anchors(markdown: str) -> set[str]:
    """GitHub-style anchors for every heading outside code.

    Lowercase, punctuation other than ``-`` and ``_`` dropped, spaces to
    hyphens, and ``-1``, ``-2``... for repeated headings. PyPI's renderer
    produces the same slugs, prefixed ``user-content-`` together with the
    links that point at them.
    """
    anchors: set[str] = set()
    for title in HEADING.findall(check_dist.without_code(markdown)):
        slug = re.sub(r"[^\w\- ]", "", title.replace("`", "").lower()).replace(" ", "-")
        anchor, n = slug, 0
        while anchor in anchors:
            n += 1
            anchor = f"{slug}-{n}"
        anchors.add(anchor)
    return anchors


# --------------------------------------------------------------------------
# The real long description
# --------------------------------------------------------------------------


def test_the_long_description_is_the_readme():
    assert long_description_source() == REPO / "README.md"


def test_the_long_description_has_only_portable_links():
    readme = long_description_source().read_text(encoding="utf-8")

    assert check_dist.link_targets(readme), "no links found; the extractor is broken"
    assert check_dist.unportable_link_targets(readme) == []


def test_every_in_document_fragment_names_a_readme_heading():
    readme = long_description_source().read_text(encoding="utf-8")
    anchors = heading_anchors(readme)
    fragments = [t[1:] for t in check_dist.link_targets(readme) if t.startswith("#")]

    assert fragments, "the README has no in-document links to check"
    assert [f for f in fragments if f not in anchors] == []


def test_repository_documents_are_linked_on_github():
    """The documents 0.3.3 linked relatively are still linked, absolutely."""
    targets = check_dist.link_targets(long_description_source().read_text("utf-8"))
    blob = "https://github.com/yaselc/khipu-python-sdk/blob/master/"

    for document in ("LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md"):
        assert blob + document in targets, document


# --------------------------------------------------------------------------
# The checker
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("markdown", "target"),
    [
        ("see [LICENSE](LICENSE)", "LICENSE"),
        ("see [policy](SECURITY.md#reporting)", "SECURITY.md#reporting"),
        ("[guide](docs/guide.md)", "docs/guide.md"),
        ("[guide](./docs/guide.md)", "./docs/guide.md"),
        ("[up](../README.md)", "../README.md"),
        ("[root](/CONTRIBUTING.md)", "/CONTRIBUTING.md"),
        ("[tools](tools/)", "tools/"),
        ('[t](CHANGELOG.md "Changelog")', "CHANGELOG.md"),
        ("![diagram](docs/flow.png)", "docs/flow.png"),
        ("[![badge](https://img.shields.io/x.svg)](LICENSE)", "LICENSE"),
        ("[![logo](assets/logo.svg)](https://example.com/)", "assets/logo.svg"),
        ("[License][lic]\n\n[lic]: LICENSE", "LICENSE"),
        ("[lic]: <./LICENSE> \"MIT\"", "./LICENSE"),
        ('<a href="CONTRIBUTING.md">contributing</a>', "CONTRIBUTING.md"),
        ("<img src='docs/flow.png' alt=''>", "docs/flow.png"),
        ("[protocol-relative](//github.com/x)", "//github.com/x"),
        ("[no host](https:///path)", "https:///path"),
        ("[ftp](ftp://example.com/file)", "ftp://example.com/file"),
        ("[empty]()", ""),
        ("[bare hash](#)", "#"),
    ],
)
def test_unportable_targets_are_rejected(markdown, target):
    assert check_dist.unportable_link_targets(markdown) == [target]


@pytest.mark.parametrize(
    "markdown",
    [
        "[docs](https://docs.khipu.com/)",
        "[http](http://example.com/)",
        "[license](https://github.com/yaselc/khipu-python-sdk/blob/master/LICENSE)",
        "[anchor](#idempotency-read-this-before-you-retry)",
        "[mail](mailto:security@example.com)",
        "[![CI](https://example.com/badge.svg)](https://example.com/ci)",
        "[ref][r]\n\n[r]: https://example.com/",
        '<a href="https://example.com/">x</a>',
        "<https://example.com/LICENSE>",
        "plain LICENSE and SECURITY.md text",
        "inline `[LICENSE](LICENSE)` code",
        "```markdown\n[LICENSE](LICENSE)\n![x](img.png)\n```",
        "~~~\n<a href=\"LICENSE\">\n~~~",
        "a [bracketed] word and a (parenthesised) one",
    ],
)
def test_portable_targets_and_code_are_accepted(markdown):
    assert check_dist.unportable_link_targets(markdown) == []


def test_every_offending_target_is_reported_in_order():
    markdown = "[a](LICENSE) [b](https://example.com/) [c](SECURITY.md)"
    assert check_dist.unportable_link_targets(markdown) == ["LICENSE", "SECURITY.md"]


def test_check_metadata_rejects_a_relative_link_in_the_long_description():
    """The artifact check, not only the README test, catches the regression."""
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: khipu-python-sdk\n"
        "Version: 9.9.9\n"
        "License-Expression: MIT\n"
        "License-File: LICENSE\n"
        "\n"
        "Community SDK, not affiliated with Khipu. See [LICENSE](LICENSE).\n"
    )

    problems = check_dist.check_metadata("wheel", metadata, "9.9.9")

    assert problems == [
        "wheel long description links 'LICENSE', which PyPI cannot resolve; "
        "use an absolute https:// URL or an in-document #fragment"
    ]


def test_check_metadata_accepts_the_real_readme():
    readme = long_description_source().read_text(encoding="utf-8")
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: khipu-python-sdk\n"
        "Version: 9.9.9\n"
        "License-Expression: MIT\n"
        "License-File: LICENSE\n"
        "Description-Content-Type: text/markdown\n"
        "\n" + readme
    )

    assert check_dist.check_metadata("sdist", metadata, "9.9.9") == []
