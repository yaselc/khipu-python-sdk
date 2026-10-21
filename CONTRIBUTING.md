# Contributing

Thanks for helping. This is a community-maintained SDK, not affiliated with,
endorsed by, or maintained by Khipu. Security issues go through
[SECURITY.md](SECURITY.md), not public issues.

## Setup and checks

```bash
python3 -m venv .venv && source .venv/bin/activate
make install-dev
make check        # ruff + mypy + pytest; must pass before a pull request
make smoke-dist   # if you touch packaging
```

The test suite makes no network calls and needs no Khipu credentials. Never
commit real API keys, merchant secrets, payer data or `.env` files; use
obviously fake values in fixtures.

## Ground rules

- Hand-written code lives in `khipu_sdk/`. Never edit `generated/`; it must
  equal a fresh `make generate-all` (CI enforces this).
- `openapi/` holds Khipu's published specs byte for byte, pinned in
  `OPENAPI_SPECS.lock.json`. Adopting a newer spec is its own reviewed change
  (see "OpenAPI specifications and regeneration" in the README).
- Payment semantics are deliberate: no retries, no idempotency assumptions,
  `Decimal` money. Changes there need an issue explaining why first.
- Add a line under `## [Unreleased]` in `CHANGELOG.md` for user-visible
  changes.

Merging a pull request does not release it. Releases are cut by the maintainer
as described in [docs/RELEASING.md](docs/RELEASING.md).
