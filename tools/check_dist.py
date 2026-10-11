"""Inspect the built wheel and sdist before anything is published.

Usage: ``python tools/check_dist.py [DIST_DIR] [--tag vX.Y.Z]``

Run against a freshly built ``dist/`` (``make build``). It fails when:

- ``dist/`` does not hold exactly one wheel and one sdist;
- either artifact's version differs from ``project.version`` in
  ``pyproject.toml`` (or from ``--tag``, which must be ``v<version>``);
- the wheel does not ship ``khipu_sdk`` and ``generated`` exactly as they are
  in the source tree, plus ``khipu_sdk/py.typed``;
- either artifact contains anything outside the explicit allowlist below --
  the specs, tests, tools, CI config, local environment files, caches,
  credentials or certificates are not part of the distribution;
- the license placeholder is still in ``LICENSE`` while ``--tag`` is given,
  i.e. while building something that is about to be published.

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

REPO = Path(__file__).resolve().parents[1]

#: Same approach as tests/unit/test_release_metadata.py: a regex instead of
#: ``tomllib``, which only exists from Python 3.11 while 3.10 is supported.
PROJECT_TABLE = re.compile(r"^\[project\]$(.*?)(?=^\[)", re.M | re.S)
VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)

#: The unfilled MIT template line. Publishing with it would ship a license
#: that names no copyright holder (Issue #18, license gate).
LICENSE_PLACEHOLDER = "<COPYRIGHT HOLDER>"

#: Packages the wheel must ship, mirrored file for file from the source tree.
PACKAGES = ("khipu_sdk", "generated")

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
        if PurePosixPath(name).parts[0] not in PACKAGES:
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

    if pkg_info is None:
        problems.append("sdist has no PKG-INFO")
    else:
        problems += check_metadata("sdist", pkg_info, version)
    return problems


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
    if "not affiliated with" not in headers.get_payload():
        problems.append(f"{kind} long description lost the independence disclaimer")
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
        if LICENSE_PLACEHOLDER in (REPO / "LICENSE").read_text(encoding="utf-8"):
            problems.append(
                "LICENSE still contains the template placeholder "
                f"{LICENSE_PLACEHOLDER!r}; the copyright holder must be confirmed "
                "before publishing (Issue #18)"
            )

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
