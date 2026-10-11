# Copilot Project Instructions

## Project overview
- This repository implements a high-level Python SDK for Khipu APIs.
- Generated OpenAPI client code lives under `generated/` (both automatic payments and instant payments clients).
- Hand-written SDK surface lives under `khipu_sdk/` alongside configuration, error types, and helpers.

## Rules for generated code
- Never modify files under `generated/` directly. They are produced by `openapi-python-client` and must stay untouched.
- When changes are needed for generated code, update the OpenAPI specs in `openapi/` and regenerate using `make generate-all`.
- The specs in `openapi/` are Khipu's published documents, committed verbatim and pinned by sha256. When the live API returns a value its document omits, add a narrow, strict entry to the generation-time overlay in `tools/spec_compat.py` instead of editing the spec (see README "Compatibility overlay").
- Keep commit history clean: generated changes should be isolated from manual SDK edits whenever possible.

## Hand-written code guidelines
- Place all business logic, abstractions, and documentation in `khipu_sdk/` or other non-generated folders.
- Prefer adding types, wrappers, or utilities instead of altering generated request/response models.
- Maintain compatibility with Python 3.10+ and follow existing code style (black-compatible formatting, Ruff lint rules if enabled).

## Testing and releases
- Use `make test` for the default test suite; enable integration tests only when required by exporting `KHIPU_RUN_INTEGRATION_TESTS`.
- Versioning lives in `pyproject.toml`; update it together with `CHANGELOG.md` when shipping releases.
- Merging to `master` releases nothing. PyPI publication happens only when the maintainer publishes a GitHub Release tagged exactly `vX.Y.Z` = `project.version` (see README "Releases"); never add workflows that tag, release or publish on push.

Following these instructions keeps the generated clients reproducible and the SDK layer stable.
