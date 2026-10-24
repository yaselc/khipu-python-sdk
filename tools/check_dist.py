"""Inspect the built wheel and sdist before anything is published.

Usage: ``python tools/check_dist.py [DIST_DIR] [--tag vX.Y.Z]``

Run against a freshly built ``dist/`` (``make build``). It fails when:

- ``dist/`` does not hold exactly one wheel and one sdist;
- either artifact's version differs from ``project.version`` in
  ``pyproject.toml`` (or from ``--tag``, which must be ``v<version>``);
- the wheel does not ship ``khipu_sdk`` (including the generated clients under
  ``khipu_sdk/_generated``) exactly as it is in the source tree, plus
  ``khipu_sdk/py.typed``;
- either artifact installs a top-level import package other than
  ``khipu_sdk``, as recorded in its ``top_level.txt`` or implied by its files,
  or still ships the obsolete top-level ``generated`` package (#56);
- either artifact contains anything outside the explicit allowlist below --
  the specs, tests, tools, CI config, local environment files, caches,
  credentials or certificates are not part of the distribution;
- ``--tag`` is given, i.e. something is about to be published, and a
  publication gate from Issue #18 is still closed: ``LICENSE`` still has the
  template copyright placeholder, or ``PUBLICATION_GATES.toml`` does not record
  ``approved = true`` (with evidence) for the Khipu redistribution gate;
- either artifact's long description (the README, rendered as the PyPI
  project page) links or embeds a target PyPI cannot resolve: anything other
  than an absolute ``https://``/``http://``/``mailto:`` URL or an in-document
  ``#fragment``, such as ``LICENSE`` or ``docs/guide.md`` relative to the
  repository.

Only the standard library is used, and only offline file reads are made.
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import zipfile
from email.parser import HeaderParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]

#: Same approach as tests/unit/test_release_metadata.py: a regex instead of
#: ``tomllib``, which only exists from Python 3.11 while 3.10 is supported.
PROJECT_TABLE = re.compile(r"^\[project\]$(.*?)(?=^\[)", re.M | re.S)
VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)

#: The unfilled MIT template line. Publishing with it would ship a license
#: that names no copyright holder (Issue #18, license gate).
LICENSE_PLACEHOLDER = "<COPYRIGHT HOLDER>"

#: Owner-controlled publication gate state (Issue #18). Read with strict
#: regexes rather than ``tomllib`` (3.11+ only), and fail closed: a missing
#: file, table or key, or any value other than the literal ``true``, keeps the
#: gate closed.
GATES_FILE = "PUBLICATION_GATES.toml"
REDISTRIBUTION_TABLE = re.compile(
    r"^\[khipu_redistribution\][ \t]*$(.*?)(?=^\[|\Z)", re.M | re.S
)
APPROVED_LINE = re.compile(r"^approved[ \t]*=[ \t]*(\S+)[ \t]*(#.*)?$", re.M)
EVIDENCE_LINE = re.compile(r'^evidence[ \t]*=[ \t]*"([^"]*)"[ \t]*(#.*)?$', re.M)

#: The only top-level import package either artifact may install (#56). The
#: generated clients live under ``khipu_sdk/_generated``; a generic top-level
#: name such as the former ``generated`` can be shadowed by, overwrite, or hide
#: an unrelated package of the same name.
TOP_LEVEL = "khipu_sdk"

#: The top-level package the generated clients used to ship as, before #56.
OBSOLETE_TOP_LEVEL = "generated"

#: Packages the wheel must ship, mirrored file for file from the source tree.
PACKAGES = (TOP_LEVEL,)

#: Files at the sdist root (below ``<name>-<version>/``) that may be shipped.
SDIST_ROOT_FILES = {"LICENSE", "PKG-INFO", "README.md", "pyproject.toml", "setup.cfg"}

#: Nothing matching these may appear in either artifact, wherever it sits.
FORBIDDEN = re.compile(
    r"(^|/)("
    r"\.env(\..*)?|\.pypirc|\.netrc|\.git(/|$)|\.github/|"
    r"__pycache__/|.*\.py[cod]$|\.(pytest|mypy|ruff)_cache/|"
    r".*\.(pem|key|p12|pfx|crt|cer|jks)$|id_(rsa|ed25519).*"
    r")",
    re.I,
)

#: Markdown code is text, not links: fenced blocks first, then inline spans.
FENCED_CODE = re.compile(r"^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1[ \t]*$", re.M | re.S)
CODE_SPAN = re.compile(r"(`+).+?\1", re.S)

#: Where a long description can point a reader or a browser:
#: ``[text](target)`` and ``![alt](target)``, reference definitions
#: ``[label]: target``, and raw HTML ``href``/``src`` attributes. The first
#: pattern is a lookahead, so matches may overlap and a linked badge
#: ``[![alt](image)](target)`` yields both ``target`` and ``image``.
#: ``<https://...>`` autolinks are absolute by construction.
LINK_TARGETS = (
    re.compile(r"(?=\[(?:[^\[\]\n]|\[[^\[\]\n]*\])*\]\(\s*<?([^\s<>()]*))"),
    re.compile(r"^ {0,3}\[[^\]\n]+\]:[ \t]*<?([^\s<>]*)", re.M),
    re.compile(r"\b(?:href|src)[ \t]*=[ \t]*[\"']([^\"']*)[\"']", re.I),
)

#: Targets that resolve wherever the description is rendered. ``http`` is
#: tolerated because it resolves too; the README itself uses ``https``.
ABSOLUTE_SCHEMES = {"https", "http"}


def without_code(markdown: str) -> str:
    """``markdown`` with fenced code blocks and inline code spans removed."""
    return CODE_SPAN.sub("", FENCED_CODE.sub("", markdown))


def link_targets(markdown: str) -> list[str]:
    """Every link and image target in ``markdown``, in document order per syntax."""
    text = without_code(markdown)
    return [target for pattern in LINK_TARGETS for target in pattern.findall(text)]


def is_portable_target(target: str) -> bool:
    """Whether ``target`` resolves outside GitHub, e.g. on the PyPI project page.

    A relative target (``LICENSE``, ``./docs/``, ``../x``, ``/SECURITY.md``)
    only works where the renderer knows the repository, which PyPI does not.
    """
    if target.startswith("#"):
        return len(target) > 1
    parts = urlsplit(target)
    if parts.scheme == "mailto":
        return bool(parts.path)
    return parts.scheme in ABSOLUTE_SCHEMES and bool(parts.netloc)


def unportable_link_targets(markdown: str) -> list[str]:
    """The targets in ``markdown`` that :func:`is_portable_target` rejects."""
    return [target for target in link_targets(markdown) if not is_portable_target(target)]


def declared_version() -> str:
    table = PROJECT_TABLE.search((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    if table is None:
        raise SystemExit("pyproject.toml has no [project] table")
    version = VERSION_LINE.search(table.group(1))
    if version is None:
        raise SystemExit("pyproject.toml [project] declares no version")
    return version.group(1)


def source_files(package: str) -> set[str]:
    """Every file a package is expected to ship, as wheel-style paths."""
    root = REPO / package
    files = {p for p in root.rglob("*") if p.is_file()}
    return {
        p.relative_to(REPO).as_posix()
        for p in files
        if "__pycache__" not in p.parts and p.suffix in {".py", ".typed"}
    }


def check_wheel(path: Path, version: str) -> list[str]:
    problems: list[str] = []
    names = [n for n in zipfile.ZipFile(path).namelist() if not n.endswith("/")]
    dist_info = f"khipu_python_sdk-{version}.dist-info/"

    shipped: set[str] = set()
    for name in names:
        if FORBIDDEN.search(name):
            problems.append(f"wheel ships forbidden file {name}")
        if name.startswith(dist_info):
            continue
        if PurePosixPath(name).parts[0] == OBSOLETE_TOP_LEVEL:
            problems.append(f"wheel ships the obsolete top-level package: {name}")
        elif PurePosixPath(name).parts[0] not in PACKAGES:
            problems.append(f"wheel ships unexpected file {name}")
        else:
            shipped.add(name)

    expected: set[str] = set()
    for package in PACKAGES:
        expected |= source_files(package)
    for extra in sorted(shipped - expected):
        problems.append(f"wheel ships {extra}, which is not in the source tree")
    for missing in sorted(expected - shipped):
        problems.append(f"wheel is missing {missing}")
    if "khipu_sdk/py.typed" not in shipped:
        problems.append("wheel is missing khipu_sdk/py.typed")

    if dist_info + "top_level.txt" in names:
        top_level = zipfile.ZipFile(path).read(dist_info + "top_level.txt").decode("utf-8")
        problems += check_top_level("wheel", top_level)

    metadata = zipfile.ZipFile(path).read(dist_info + "METADATA").decode("utf-8")
    problems += check_metadata("wheel", metadata, version)
    if dist_info + "licenses/LICENSE" not in names:
        problems.append("wheel does not ship LICENSE under dist-info/licenses/")
    return problems


def check_sdist(path: Path, version: str) -> list[str]:
    problems: list[str] = []
    prefix = f"khipu_python_sdk-{version}/"
    with tarfile.open(path) as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        pkg_info = None
        for member in members:
            name = member.name
            if not name.startswith(prefix):
                problems.append(f"sdist ships {name} outside {prefix}")
                continue
            rel = name[len(prefix):]
            top = PurePosixPath(rel).parts[0]
            if FORBIDDEN.search(rel):
                problems.append(f"sdist ships forbidden file {rel}")
            elif top == OBSOLETE_TOP_LEVEL:
                problems.append(f"sdist ships the obsolete top-level package: {rel}")
            elif not (
                rel in SDIST_ROOT_FILES
                or top in PACKAGES
                or top == "khipu_python_sdk.egg-info"
            ):
                problems.append(f"sdist ships unexpected file {rel}")
            if rel == "PKG-INFO":
                extracted = tar.extractfile(member)
                assert extracted is not None
                pkg_info = extracted.read().decode("utf-8")
            if rel == "khipu_python_sdk.egg-info/top_level.txt":
                extracted = tar.extractfile(member)
                assert extracted is not None
                problems += check_top_level("sdist", extracted.read().decode("utf-8"))

    if pkg_info is None:
        problems.append("sdist has no PKG-INFO")
    else:
        problems += check_metadata("sdist", pkg_info, version)
    return problems


def check_top_level(kind: str, raw: str) -> list[str]:
    """Problems with a ``top_level.txt``: it must name ``khipu_sdk`` alone."""
    declared = sorted({line.strip() for line in raw.splitlines() if line.strip()})
    if declared != [TOP_LEVEL]:
        return [
            f"{kind} top_level.txt declares {declared}, expected [{TOP_LEVEL!r}] "
            "only; a second top-level package can collide with unrelated code"
        ]
    return []


def check_metadata(kind: str, raw: str, version: str) -> list[str]:
    headers = HeaderParser().parsestr(raw)
    problems = []
    expected = {
        "Name": "khipu-python-sdk",
        "Version": version,
        "License-Expression": "MIT",
        "License-File": "LICENSE",
    }
    for field, value in expected.items():
        if headers.get(field) != value:
            problems.append(f"{kind} metadata {field} is {headers.get(field)!r}, expected {value!r}")
    description = headers.get_payload()
    if "not affiliated with" not in description:
        problems.append(f"{kind} long description lost the independence disclaimer")
    for target in unportable_link_targets(description):
        problems.append(
            f"{kind} long description links {target!r}, which PyPI cannot "
            "resolve; use an absolute https:// URL or an in-document #fragment"
        )
    return problems


def publication_gate_problems(repo: Path = REPO) -> list[str]:
    """Why ``repo`` may not be published yet; empty when every gate is open."""
    problems = []

    if LICENSE_PLACEHOLDER in (repo / "LICENSE").read_text(encoding="utf-8"):
        problems.append(
            "LICENSE still contains the template placeholder "
            f"{LICENSE_PLACEHOLDER!r}; the copyright holder must be confirmed "
            "before publishing (Issue #18)"
        )

    blocked = (
        "Khipu redistribution permission is not approved; publication is "
        f"blocked by Issue #18 ({GATES_FILE} [khipu_redistribution])"
    )
    gates = repo / GATES_FILE
    table = REDISTRIBUTION_TABLE.search(
        gates.read_text(encoding="utf-8") if gates.is_file() else ""
    )
    approved = APPROVED_LINE.findall(table.group(1)) if table else []
    evidence = EVIDENCE_LINE.findall(table.group(1)) if table else []
    if len(approved) != 1 or approved[0][0] != "true":
        problems.append(blocked)
    elif len(evidence) != 1 or not evidence[0][0].strip():
        problems.append(f"{blocked}: approved = true but no evidence is recorded")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dist", nargs="?", default="dist", type=Path)
    parser.add_argument(
        "--tag",
        help="release tag being published; must be v<project.version>",
    )
    args = parser.parse_args()

    version = declared_version()
    problems: list[str] = []

    if args.tag is not None:
        if args.tag != f"v{version}":
            problems.append(
                f"tag {args.tag!r} does not match project.version {version!r} "
                f"(expected 'v{version}')"
            )
        problems += publication_gate_problems()

    wheels = sorted(args.dist.glob("*.whl"))
    sdists = sorted(args.dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        problems.append(
            f"{args.dist} must hold exactly one wheel and one sdist, found "
            f"{[p.name for p in wheels + sdists]}"
        )
    else:
        if wheels[0].name != f"khipu_python_sdk-{version}-py3-none-any.whl":
            problems.append(f"unexpected wheel name {wheels[0].name}")
        if sdists[0].name != f"khipu_python_sdk-{version}.tar.gz":
            problems.append(f"unexpected sdist name {sdists[0].name}")
        problems += check_wheel(wheels[0], version)
        problems += check_sdist(sdists[0], version)

    if problems:
        print("\n".join(f"FAIL: {p}" for p in problems))
        return 1
    for artifact in wheels + sdists:
        print(f"OK: {artifact.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
