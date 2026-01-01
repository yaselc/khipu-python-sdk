# Copilot Project Instructions

## Project overview
- This repository implements a high-level Python SDK for Khipu APIs.
- Generated OpenAPI client code lives under `generated/` (both automatic payments and instant payments clients).
- Hand-written SDK surface lives under `khipu_sdk/` alongside configuration, error types, and helpers.

## Rules for generated code
- Never modify files under `generated/` directly. They are produced by `openapi-python-client` and must stay untouched.
- When changes are needed for generated code, update the OpenAPI specs in `openapi/` and regenerate using `make generate-all`.
- Keep commit history clean: generated changes should be isolated from manual SDK edits whenever possible.

## Hand-written code guidelines
- Place all business logic, abstractions, and documentation in `khipu_sdk/` or other non-generated folders.
- Prefer adding types, wrappers, or utilities instead of altering generated request/response models.
- Maintain compatibility with Python 3.10+ and follow existing code style (black-compatible formatting, Ruff lint rules if enabled).

## Testing and releases
- Use `make test` for the default test suite; enable integration tests only when required by exporting `KHIPU_RUN_INTEGRATION_TESTS`.
- Versioning lives in `pyproject.toml`; update it together with `CHANGELOG.md` when shipping releases.
- Release automation relies on Git tags; ensure new tags follow the `vX.Y.Z` pattern.

Following these instructions keeps the generated clients reproducible and the SDK layer stable.
