# Releasing khipu-python-sdk

This is the maintainer procedure for publishing a version of
`khipu-python-sdk` to TestPyPI and PyPI. It is the only publication process:
there is no other path to an index, and none may be added.

The version history itself lives in
[CHANGELOG.md](https://github.com/yaselc/khipu-python-sdk/blob/master/CHANGELOG.md)
and on [GitHub Releases](https://github.com/yaselc/khipu-python-sdk/releases).
This document describes the procedure only; it never names a particular
version, so it does not need to change from one release to the next.
`X.Y.Z` below stands for the version being released.

## Invariants

These hold for every release. `tests/unit/test_release_metadata.py` and
`tests/unit/test_publication_gates.py` enforce them offline.

- **Merging to `master` releases nothing.** No workflow tags, creates a GitHub
  Release or uploads a package on a merge or push. No workflow has
  `contents: write`, and none approves or merges pull requests.
- **Publication is a deliberate maintainer action.** Only the maintainer
  dispatches the TestPyPI workflow, creates the `vX.Y.Z` tag and publishes the
  GitHub Release.
- **Only reviewed code on `master` is built.** The shared build
  (`.github/workflows/build-dist.yml`) builds the triggering event's own commit
  and refuses it unless it is already on `master`, before any code from the
  checked-out tree runs. No caller can choose another commit or skip the check.
- **Only checked artifacts are uploaded.** The shared build creates a fresh
  wheel and sdist, runs `make smoke-dist`, `tools/check_dist.py dist --tag
  vX.Y.Z` and `twine check --strict`, and only then uploads the artifact the
  publish job downloads. The publish jobs never build anything themselves.
- **The tag matches the package.** `tools/check_dist.py --tag` refuses a tag
  that is not exactly `v<project.version>`.
- **Trusted Publishing only.** Both publish jobs authenticate with OIDC
  through the GitHub environments `testpypi` and `pypi`. `id-token: write` is
  granted to the publish job alone. No PyPI API token is stored in this
  repository.
- **Publication gates (Issue #18).** `tools/check_dist.py --tag` refuses to
  publish unless `LICENSE` names its confirmed copyright holder (not the
  template placeholder) and `PUBLICATION_GATES.toml` records `approved = true`
  with evidence for redistributing Khipu's OpenAPI documents and the clients
  generated from them. Changing either is an owner decision in its own
  reviewed pull request. Both are resolved: `LICENSE` carries the confirmed
  copyright holder (Issue #24), and Khipu's written permission is recorded in
  Issue #18 (Issue #26). The check still refuses the template placeholder,
  `approved = false` or an approval without evidence should any of them
  return. Resolving the gates publishes nothing.
- **Index files are immutable.** A version uploaded to TestPyPI or PyPI can
  never be uploaded again with different files, and its project description
  (this repository's README as it was when the version was built) cannot be
  changed. A fix merged later reaches an index only with a new version.

## Release state in the repository

Publication cannot be observed offline, so the release state is recorded in
the repository and the tests keep it consistent:

- `project.version` in `pyproject.toml` is the declared version.
- In `tests/unit/test_release_metadata.py`:
  - `LATEST_PUBLISHED_RELEASE` is the newest version on PyPI and its
    publication date. It is the newest dated CHANGELOG section, and every
    install reference in the README names it.
  - `RELEASE_CANDIDATE` is the declared version while it is prepared but not
    yet tagged or uploaded, or `None` when the declared version is the latest
    published release.

The README never mentions any other released version: the version history
belongs to the CHANGELOG.

## 1. Release candidate

In a reviewed pull request:

1. Bump `project.version` in `pyproject.toml` to `X.Y.Z`.
2. Add a `Target release: X.Y.Z` line directly under `## [Unreleased]` in
   `CHANGELOG.md`, with no date. Keep the pending entries there.
3. Set `RELEASE_CANDIDATE = "X.Y.Z"`. Leave `LATEST_PUBLISHED_RELEASE`
   unchanged.

The README install commands keep naming the newest version already on PyPI,
so nothing on `master` offers a version that cannot be installed. A candidate
must be newer than every dated release.

## 2. Release cut

In its own reviewed pull request, planned for the day of publication:

1. Move the `## [Unreleased]` entries into a new `## [X.Y.Z] - YYYY-MM-DD`
   section dated with the intended publication date (UTC), and remove the
   `Target release:` line. Leave `## [Unreleased]` in place, empty, above it.
   Earlier sections are never edited.
2. Point every install reference in the README at `X.Y.Z`: the `pip install`
   command, the `requirements.txt` and `pyproject.toml` examples, and the Git
   install `@vX.Y.Z`.
3. Set `LATEST_PUBLISHED_RELEASE = ("X.Y.Z", "YYYY-MM-DD")`, with the same
   date as the CHANGELOG heading, and `RELEASE_CANDIDATE = None`.

The release cut is merged *before* anything is uploaded, because the README it
freezes becomes the PyPI project description. From that merge until the
upload, the dated section and `LATEST_PUBLISHED_RELEASE` record the intended
publication, not evidence that the index already has it, and the README's
install commands name a version that does not resolve yet. Keep that window
short.

## 3. TestPyPI rehearsal (optional)

Run the *Publish to TestPyPI* workflow
(`.github/workflows/publish-testpypi.yml`) manually with `workflow_dispatch`
from `master`, entering `X.Y.Z` as the version. It builds the selected commit
only if it is already on `master`, publishes from the `testpypi` environment,
then installs the upload back from TestPyPI (its dependencies from PyPI) and
smoke-tests it.

Rehearse the release-cut merge commit, the exact commit that will be tagged.
A TestPyPI upload consumes `X.Y.Z` there permanently.

## 4. PyPI

Create the tag `vX.Y.Z` on the same reviewed commit on `master` and publish a
GitHub Release for it. Publishing the release is the only trigger of the
*Publish to PyPI* workflow (`.github/workflows/publish-pypi.yml`). It refuses a
tag that does not match `project.version` or that is not on `master`, then
publishes from the `pypi` environment and installs the upload back from PyPI
and smoke-tests it.

The release builds the commit the tag pointed at when the release was
published; moving the tag afterwards changes nothing that is built.

## 5. Verification

After the workflow succeeds:

- `https://pypi.org/pypi/khipu-python-sdk/X.Y.Z/json` lists exactly one wheel
  and one sdist, with `Version: X.Y.Z`, `License-Expression: MIT` and the
  expected upload date.
- The PyPI project description shows the release-cut README: install commands
  pinned to `X.Y.Z`, the independence disclaimer, and working absolute links.
- The files carry Trusted Publishing provenance for this repository and the
  `publish-pypi.yml` workflow.
- `pip install khipu-python-sdk==X.Y.Z` works in a clean virtual environment
  and `import khipu_sdk` succeeds.
- Post-merge CI on `master` is green.

## When the date slips or a step fails

- **Publication will not happen on the dated day.** Before tagging or
  uploading anything, correct the date in a reviewed pull request: change the
  `## [X.Y.Z]` heading date and `LATEST_PUBLISHED_RELEASE` together. The
  tests require them to agree. Then rehearse and tag the new merge commit.
- **The release is abandoned or postponed indefinitely.** Revert the release
  cut in a reviewed pull request: move the entries back under
  `## [Unreleased]` with `Target release: X.Y.Z`, restore the previous README
  pins and `LATEST_PUBLISHED_RELEASE`, and set `RELEASE_CANDIDATE` again.
- **The TestPyPI rehearsal fails.** Nothing has reached PyPI. Fix the cause in a
  reviewed pull request. If the failure happened after the upload, `X.Y.Z` is
  consumed on TestPyPI; a further rehearsal needs a new version.
- **The PyPI workflow fails before the upload.** Fix the cause in a reviewed
  pull request, then publish a release for a new tag on the fixed commit. Do
  not move an existing tag.
- **A published version is wrong.** It cannot be replaced. Yank it on PyPI if
  installing it is harmful, and publish a new version with the fix.

Never bypass a gate, an ancestry check or a failed check to get a release out.
