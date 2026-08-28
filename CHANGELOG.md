# Changelog

All notable changes to this project will be documented in this file.

This project follows Semantic Versioning (SemVer):
https://semver.org/

## [Unreleased]

### Added
- _TBD_

## [0.2.0] - 2026-08-28

Production-hardening release. Contains **breaking changes** to the exception
taxonomy and to the result dataclasses.

### Fixed

- **Packaging (blocking).** `generated/` was excluded from the built
  distribution, so a wheel or Git install produced an SDK where every method
  raised "generated client is not available". `pyproject.toml` now includes
  `generated*`, and `generated/__init__.py` makes it a real package.
- **Missing runtime dependencies (blocking).** `attrs` and `python-dateutil`
  are required by the shipped generated code but were undeclared.
- **Khipu error bodies were discarded.** Non-success responses raised
  `"Empty response"` even when Khipu returned useful JSON. `KhipuApiError` now
  carries `payload` (parsed JSON), `body` (bounded raw text) and a message
  derived from Khipu's own diagnostics.
- **Exceptions could not be pickled**, breaking Celery result backends. The
  dataclass-based `KhipuApiError` was replaced with explicit `Exception`
  subclasses.
- **`create_charge` signature defect.** `error_response_url`, `custom` and
  `notify_url` are required by Khipu's `ChargeRequest` schema but were absent
  from the public signature, so calling the method as documented failed. They
  are now required parameters.
- `KhipuConfig` no longer exposes the API key through `repr()`.

### Added

- **`Decimal` money support.** `amount` / `max_amount` accept `Decimal`, `int`,
  `str` or `float`. `Decimal` is canonical; conversion to `float`/`int` happens
  only at the generated-model boundary (`khipu_sdk.money.amount_to_wire`).
- **Currency minor-unit validation.** Amounts are checked against the currency's
  ISO-4217 scale before serialisation and are never silently rounded. Fractional
  CLP (e.g. `Decimal("9700.5")`) now raises `KhipuValidationError` with no HTTP
  request made. New module `khipu_sdk.money`.
- **Exception taxonomy** under `KhipuError`: `KhipuConfigurationError`,
  `KhipuValidationError`, `KhipuTransportError` (with `KhipuTimeoutError` and
  `KhipuConnectionError`), `KhipuApiError` and `KhipuResponseError`. Transport
  errors expose `request_may_have_been_delivered`, derived from httpx's own
  taxonomy, so an ambiguous create-payment outcome is explicit.
- **Correlation and verification fields promoted** onto `InstantPaymentStatus`:
  `transaction_id`, `custom`, `status_detail`, `receiver_id`,
  `notification_token`, `expires_date`, `conciliation_date` and
  `out_of_date_conciliation`. Callers no longer need `.raw`.
- **All create-response URLs promoted** onto `InstantPaymentCreateResult`:
  `simplified_transfer_url`, `transfer_url`, `app_url`, `ready_for_terminal`.
- `py.typed` marker so downstream type checkers see the package as typed.
- Public exports from `khipu_sdk`: the client, config, every exception, every
  result dataclass, and `CURRENCY_MINOR_UNITS` / `SUPPORTED_CURRENCIES`.
- `httpx.Timeout` is accepted by `KhipuConfig.timeout` for per-phase control.
- **CI packaging regression guard**: a `package` job builds the wheel, asserts it
  contains the generated clients and `py.typed`, installs it into a clean
  virtualenv and creates/retrieves a payment against a mock server
  (`make build`, `make smoke-dist`, `tools/smoke_installed.py`).
- Real HTTP-boundary tests using `pytest-httpx`, replacing `SimpleNamespace`
  stubs of `sync_detailed`. Coverage added for the `x-api-key` header, 400/401/
  403/500/429 responses, timeouts, connection failures, malformed JSON, missing
  required fields, `Decimal` serialization, fractional-CLP rejection, the real
  `pending`/`verifying`/`done` status values, `status_detail == "reversed"`,
  correlation round-trip, exception pickling and credential-`repr` safety.
- `.env` / `.env.*` added to `.gitignore`.

### Changed

- **Breaking:** a missing generated client now raises `KhipuConfigurationError`
  instead of `KhipuApiError(500)`.
- **Breaking:** timeouts, connection failures, local validation errors and
  malformed responses no longer surface as `KhipuApiError(status_code=500)`.
  Catch `KhipuError` for a blanket handler.
- **Breaking:** `InstantPaymentCreateResult.status` was removed. It was always
  `None` — Khipu's create response carries no status.
- **Breaking:** `InstantPaymentStatus.amount` is now `Optional[Decimal]` instead
  of `Optional[float]`, and `status` is a plain `str` rather than a generated
  enum leaking through an `Optional[str]` annotation.
- `raw` is excluded from `repr()` on all result types; the underlying Khipu
  payment model carries payer PII.
- Removed the vestigial `types-requests` dev dependency (`requests` is unused);
  added `build`.

### Upstream API

- Adopted the Khipu OpenAPI specifications as published on 2026-08-28, replacing
  the 2025-12-26 snapshot, and refreshed `OPENAPI_SPECS.lock.json` and the
  generated clients accordingly.
- **Instant Payments.** `payment-get-payment.amount` and `.discount` changed from
  `number` to `string` upstream; the facade continues to expose
  `InstantPaymentStatus.amount` as `Optional[Decimal]` and accepts either
  representation. `status_detail` gained `partially-refunded` and
  `fully-refunded`, surfaced verbatim as plain strings. New optional fields
  `authorizer_operation_code` (response) and `psp_client_merchant_logo_url`
  (request). `POST /v3/payments/{id}/refunds` is now marked obsolete, takes no
  body and refunds the full amount only; `POST /v3/payments/{id}/void`,
  `POST /v3/refunds`, `GET /v3/refund-wallet/balance` and
  `GET /v3/receivers/children` are new. The receiver creation response now also
  returns an `api_key`.
- **Automatic Payments.** Documentation-URL change only; no schema change and no
  effect on `create_charge`.
- The new refund, void and receiver operations are generated but deliberately
  **not** exposed on `KhipuClient`. The facade stays small; promoting an
  operation is a separate decision.
- Pinned `openapi-python-client==0.28.0` exactly. The generator produces the
  committed contents of `generated/`, so a floating version could change that
  code with no change in this repository. Regeneration from the committed specs
  is byte-identical.

### Notes

Unchanged by design, because Khipu does not provide them:

- `create_instant_payment` is **not** idempotent, and `transaction_id` is **not**
  documented by Khipu as a deduplication key.
- There is **no** lookup-by-`transaction_id` endpoint.
- There is **no** pre-payment merchant-fee quotation in either vendored spec.
- There is **no** settlement/report API, and the SDK contains **no** webhook
  handling.
- The SDK still performs **no retries**, including on create-payment.

## [0.1.2] - 2026-01-01

### Fixed
- Corrected SDK imports to match generated client module paths.

### Added
- Mocked integration tests covering instant payments and automatic payment flows.
- Unit regression ensuring missing generated clients raise actionable errors.

## [0.1.1] - 2025-12-30

### Added
- Include generated code for Khipu clients.

## [0.1.0] - 2025-12-26

### Added
- Initial repository structure.
- `KhipuClient` high-level wrapper for Khipu Instant Payments (v3) and Automatic Payments / PAC (v1).
- OpenAPI download and client generation tasks.
- Unit/integration test scaffolding.
