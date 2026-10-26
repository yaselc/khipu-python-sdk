# Changelog

All notable changes to this project will be documented in this file.

This project follows Semantic Versioning (SemVer):
https://semver.org/

## [Unreleased]

Target release: 0.4.0

A minor release with the remaining remediations of the audit of 0.3.4 (#41).
It rejects fractional amounts that would change on the way to Khipu (#48),
validates `KhipuConfig` on construction (#50), documents and tests the
`**extra_fields` contract (#52), adds `KhipuClient.close()` and context
management (#54), and moves the generated clients from the top-level
`generated` package into the private `khipu_sdk._generated` package (#56).
Everything imported from `khipu_sdk` keeps working. Code that imported
`generated.*` directly, which was never supported, breaks. Some inputs that
were accepted before now fail before any request: an invalid configuration
(including a set but empty `{prefix}TIMEOUT` or `{prefix}BASE_URL`) raises
`KhipuConfigurationError`, and an amount that cannot be sent exactly raises
`KhipuValidationError`. No OpenAPI spec or runtime dependency changes.

### Added

- **`KhipuClient.close()` and synchronous context management (#54).**
  `with KhipuClient(config) as client:` or an explicit `client.close()` now
  releases the HTTP connection pools the client created. Only pools that
  exist are closed: a client that never called an API, or called only one of
  Instant Payments and Automatic Payments, builds no pool just to close it.
  `close()` is idempotent. After it, every operation raises
  `KhipuConfigurationError` before any validation or request, and the pools
  are never reopened. If closing one pool fails, the other is still closed,
  each failure is logged by exception type, and the first is re-raised; an
  exception leaving a `with` block is never replaced by a cleanup failure.
  Behaviour before `close()`, including timeouts, error mapping and the
  no-retry policy, is unchanged. No generated client, OpenAPI spec or
  dependency changes.

### Changed

- **The generated clients moved into the private `khipu_sdk._generated`
  package (#56).** The OpenAPI-generated Instant Payments and Automatic
  Payments clients used to be installed as a generic top-level `generated`
  package. A consumer project with its own `generated` package then shadowed
  them, so every call raised `KhipuConfigurationError`; a consumer's
  namespace-style `generated/` directory became unimportable once the SDK was
  installed; and pip and uv silently overwrote files with any other
  distribution shipping a top-level `generated`. The distribution now installs
  `khipu_sdk` as its only top-level package, and the top-level `generated`
  package is no longer distributed. The supported public API, everything
  imported from `khipu_sdk`, is unchanged, and so are request and response
  behaviour, errors, timeouts and the no-retry policy. Importing `generated.*`
  directly was never supported and breaks from the next release on; no
  compatibility alias is provided, because one would keep the collision.
  `khipu_sdk._generated` is private as well. The generated files are moved
  unchanged, from the same specs and the same pinned generator. No public API,
  OpenAPI spec or dependency changes.
- **Invalid configuration is rejected when `KhipuConfig` is built (#50).**
  Direct construction now validates every field, not only `from_env()`, and
  `KhipuClient` checks the config again before creating its HTTP clients, so
  no request can be made with an invalid configuration. `api_key` must be a
  non-empty string of visible ASCII characters (whitespace is rejected, not
  stripped). `base_url` must be an absolute `http://` or `https://` URL with a
  valid hostname and no credentials, fragment, whitespace or non-ASCII
  characters; `http://` remains supported for local mocks. `timeout` must be
  a finite, positive `int` or `float`, or an `httpx.Timeout` whose four
  phases are all finite and positive; `None`, booleans, strings, zero,
  negative values, NaN, infinity and unbounded phases are rejected. In
  `from_env()`, a set but empty `{prefix}TIMEOUT` or `{prefix}BASE_URL` is now
  an error instead of falling back to the default. Every such failure raises
  `KhipuConfigurationError`, whose message never contains the rejected value
  and which chains no other exception.
- **`KhipuConfigurationError` is now also a `ValueError` (#50).**
  `from_env()` used to raise a bare `ValueError` for a missing key or a
  malformed timeout; it now raises `KhipuConfigurationError`, and existing
  `except ValueError` handlers still catch it. Valid configurations behave as
  before. No generated client, OpenAPI spec or dependency changes.

### Fixed

- **Fractional amounts are never changed on the way to Khipu (#48).** The
  generated clients send a non-integral amount as a JSON float, which keeps
  only about 15 to 17 significant digits, so an amount such as
  `Decimal("1234567890123.4567")` CLF used to be sent as
  `1234567890123.4568`. `amount_to_wire` now checks that the float is written
  back as the same decimal value and raises `KhipuValidationError` before any
  request when it is not, including on float overflow or underflow. Amounts
  are still never rounded. This applies to `create_instant_payment`,
  `create_subscription` and `create_charge` (also without `currency`).
  Ordinary amounts such as `Decimal("0.1")`, CLF with four decimals and USD
  with two are sent exactly as before, and whole amounts stay integers of any
  size. No public API, generated client, OpenAPI spec or dependency changes.

### Documentation

- **`**extra_fields` contract and Instant Payments `custom` (#52).** The README
  now documents `**extra_fields` on `create_instant_payment`,
  `create_subscription` and `create_charge` as a compatibility escape hatch for
  schema fields without an explicit parameter, not a general extension
  mechanism. Keys are forwarded verbatim: a field the schema declares is sent
  under its name, while an undeclared or misspelled key (including a misspelled
  explicit parameter) raises no error and is sent as its own top-level JSON key,
  so the intended field is not set and Khipu's handling of the extra key is
  undocumented. `None` under an extra key is sent as `null`. The Correlation
  section adds an Instant Payments example that passes `custom` for
  merchant-side correlation and distinguishes it from `transaction_id`;
  neither is an idempotency key. New offline HTTP tests pin the serialised JSON
  for recognized, unknown and misspelled extra fields on all three operations,
  and that named parameters such as `amount` and `currency` cannot be
  overridden through `**extra_fields`. Runtime behavior, public signatures,
  generated clients and OpenAPI specs are unchanged.

## [0.3.5] - 2026-10-21

A bug-fix release (#44, #46). Its runtime change is #42: the SDK keeps the
HTTP status and body of a response the generated clients cannot parse, and
classifies a non-2xx status as `KhipuApiError` before any parsing. It also
ships the repository maintenance of #37 and #39 and a reorganisation of the
release documentation (#46). No public API, generated client, OpenAPI spec or
runtime dependency changes.

### Added

- **Dependabot proposes GitHub Actions updates (#39).**
  `.github/dependabot.yml` checks the actions of all four workflows weekly
  and opens at most three update pull requests at a time, keeping each
  action pinned to a full commit SHA with its version comment. Updates are
  reviewed and merged by hand like any other change; no other ecosystem is
  enabled. Repository configuration only: nothing in the package changes.

### Changed

- **README installs 0.3.5; the release procedure moves to
  `docs/RELEASING.md` (#46).** The `pip install`, `requirements.txt`,
  `pyproject.toml` and Git (`@v0.3.5`) examples under Installation pin 0.3.5.
  The README "Releases" section no longer accumulates a paragraph per version:
  it links to this changelog, the GitHub Releases page and the maintainer
  procedure in
  [`docs/RELEASING.md`](https://github.com/yaselc/khipu-python-sdk/blob/master/docs/RELEASING.md).
  Unit tests now reject any README install reference, or any mention of
  another released version, that does not name the latest published release.
  Documentation and tests only: nothing in the package's code changes.
- **GitHub Actions run on Node 24 with pinned actions and runner (#37).**
  CI and the release workflows use `actions/checkout` v7.0.1,
  `actions/setup-python` v7.0.0, `actions/upload-artifact` v7.0.2 and
  `actions/download-artifact` v8.0.2, which run natively on Node 24 (GitHub
  no longer provides Node 20). Every action is pinned to a full commit SHA,
  every job runs on `ubuntu-24.04` instead of `ubuntu-latest` (which moves to
  Ubuntu 26.04 from 2026-10-19), and the CI checkouts no longer persist the
  job token. A unit test keeps actions, runners and checkouts that way.
  Workflow change only: nothing in the package changes.
- **README PyPI badge requests the `.svg` URL (#37).** GitHub kept serving
  a "package or version not found" image for the old badge URL, cached on
  2026-10-17 before 0.3.3 was first uploaded, although the PyPI JSON API and
  Shields.io both report the current version. The badge stays the same
  dynamic Shields.io badge, under the URL form the License badge already
  uses, so GitHub fetches it afresh. The PyPI project page shows this README
  only from the next release.

### Fixed

- **HTTP status and body survive a generated parsing failure (#42).** The
  generated clients parse the body before returning the response, so when that
  parsing failed the facade lost the status and the body (audit #41, F1 and
  F2). The facade now runs the generated request and parsing steps itself
  (`_get_kwargs`, a single request, `_build_response`), still sending exactly
  one request, and classifies the status before any parsing:
  - Every non-2xx status is a `KhipuApiError` with its real `status_code`, a
    bounded `body` and the JSON `payload` when there is one. A PAC
    `create_charge` refusal (`422`) whose `ChargeError` body is empty, not JSON
    or incomplete was previously reported as `KhipuResponseError` with no
    status; it is now the definite rejection it is. The same applies to any
    non-2xx status the generated clients cannot name, such as `599`.
  - A 2xx response whose body cannot be parsed is a `KhipuResponseError` that
    keeps `status_code` and a bounded `body`. For `create_instant_payment`
    this preserves the `payment_id` Khipu returned, when it falls within the
    500-character bound, as evidence for reconciliation; the SDK does not treat
    it as a successful or settled payment.
  - A request payload that cannot be serialised, for instance a `Decimal` or a
    `set` passed through `**extra_fields`, is now a `KhipuValidationError` with
    no request sent. It was previously reported as `KhipuResponseError`,
    although nothing had reached Khipu.

  Retries (none), transport error classification and
  `request_may_have_been_delivered`, the PAC charge success statuses (`201`,
  and `200` for compatibility) and the rejection of other 2xx statuses are
  unchanged. A unit test pins the shape of the generated `sync_detailed` the
  facade relies on, so a generator change cannot silently bypass it. The
  README documents what a `KhipuResponseError` on a create operation means for
  reconciliation and reads a `422` payload defensively. No public API,
  dependency or generated code changes.

## [0.3.4] - 2026-10-18

A documentation and package-metadata maintenance release (#33, #35). Its
purpose is to publish the corrected README below as the PyPI project
description; 0.3.3's published files and description cannot be replaced. No
change to the SDK's runtime behaviour, public API, generated clients, OpenAPI
specs or runtime dependencies.

### Changed

- **README installs 0.3.4 (#35).** The `pip install`, `requirements.txt`,
  `pyproject.toml` and Git (`@v0.3.4`) examples under Installation pin 0.3.4,
  the version this README is published with.

- **README explains CLP and CLF minor units with examples (#33).** "Currency
  minor units" now states that `Decimal("10000.0000")` is valid for CLP
  because its fractional part is zero, that CLP amounts with a nonzero
  fractional part such as `Decimal("9700.5")` are rejected, and that CLF
  accepts four decimal places (`Decimal("1.2345")`) but not five
  (`Decimal("1.23456")`). Documentation only: validation is unchanged.
- **README and CHANGELOG describe the published 0.3.3 release (#31).**
  Installation no longer says 0.3.3 is unpublished: `pip install
  khipu-python-sdk==0.3.3` and the `@v0.3.3` Git install are current, and the
  0.3.3 entries below moved from `[Unreleased]` into a dated section.
- **README links work on PyPI (#31).** The README is the package's long
  description, and PyPI cannot resolve links relative to the repository, so
  the links to `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md` and `CHANGELOG.md`
  are now absolute GitHub URLs. `tools/check_dist.py` rejects relative link
  and image targets in the built long description, and unit tests apply the
  same check to the README. The already published 0.3.3 description on PyPI
  is unchanged; the fix applies to distributions built from now on.

## [0.3.3] - 2026-10-17

First public release on PyPI. Tag `v0.3.3` and the GitHub Release were
published on 2026-10-17; the wheel and sdist were uploaded to TestPyPI and then
to PyPI by the release workflows with Trusted Publishing, and each upload was
installed back from its index and smoke-tested. The release candidate was
prepared on 2026-10-11.

No change to the SDK's runtime behaviour or supported public API: `khipu_sdk`,
retries (none), idempotency, success-status handling and every payment/PAC
operation are byte-for-byte the same code as 0.3.2. The generated Instant
Payments client changes only as described under
[Provider spec adoption](#provider-spec-adoption-instant-payments-20) below; the
generated Automatic Payments client is unchanged.

### Changed

- **Publication is now deliberate; merging to `master` releases nothing.** The
  `release-on-merge` workflow, which tagged and created a GitHub Release for
  `project.version` on every push to `master`, is removed. In its place:
  - `publish-testpypi.yml`: manual (`workflow_dispatch`), requires the selected
    commit to be already on `master`, and publishes to TestPyPI;
  - `publish-pypi.yml`: runs only when a GitHub Release is published, requires
    the tag to be exactly `v<project.version>` on a commit already on `master`,
    and publishes to PyPI from the `pypi` environment.

  Both build a fresh wheel and sdist, inspect and smoke-test them, upload with
  PyPI Trusted Publishing (OIDC, no stored token) and then install the uploaded
  release back from the index and smoke-test it. Both refuse to publish while
  either Issue #18 publication gate is closed: `LICENSE` still carries the
  template copyright placeholder, or the new `PUBLICATION_GATES.toml` does not
  approve (with evidence) redistribution of Khipu's OpenAPI documents and the
  generated clients. That gate was added as `approved = false` and was
  approved, with Khipu's written permission recorded in Issue #18 as its
  evidence, in Issue #26.
- **Package metadata for PyPI.** SPDX license expression (`MIT`) with
  `license-files`, maintainer, project URLs, classifiers (Python 3.10–3.12,
  `Typing :: Typed`) and keywords. The build backend floor moves to
  `setuptools>=77`, the first release that writes this license metadata.
- **README** states prominently that this is a community-maintained SDK, not
  affiliated with, endorsed by or maintained by Khipu; documents PyPI as the
  install path (from 0.3.3) with a Git tag install as the alternative, and
  points every link at `github.com/yaselc/khipu-python-sdk`. Until 0.3.3 was
  released, Installation said it was not yet published, that `v0.3.3` did not
  yet exist and that `v0.3.2` was the latest tag, and scoped both install
  commands to after the release.
- `make build` now builds the sdist and the wheel from that sdist; `make
  smoke-dist` checks both with the new `tools/check_dist.py` (exact package
  contents, allowlist, metadata) and smoke-tests each from a clean install.

### Added

- `SECURITY.md` (private vulnerability reporting) and a short
  `CONTRIBUTING.md`.

### Provider spec adoption (Instant Payments, #20)

Adopts the Instant Payments OpenAPI document Khipu published as of
2026-10-11 (`openapi/khipu-instant-payments.yaml`, sha256 `fdbc4c27…` →
`fed2ea62…`). Automatic Payments is unchanged. The supported `KhipuClient`
facade is unaffected: none of these changes touch payment create/get, refunds,
void, banks, receivers, security or any error response.

- **Generated-only: `GET /v3/predict/all` (`getPredictAll`).** New
  `generated.instant_payments.api.default.get_predict_all` with the
  `PredictGetPredictAll` / `PredictGetPredictAllBanksItem` models: one
  prediction per bank the collecting account can use, in `GET /v3/banks`
  order. Not exposed on `KhipuClient`.
- **Generated-only, breaking for direct `generated.*` users: prediction
  `result` values are now uppercase.** Khipu's document changed
  `predict-get-predict.result` from `ok`, `new_destinatary_amount_exceeded`,
  `max_amount_exceeded`, `new_destinatary_cool_down`, `not_available_account`
  to `OK`, `NEW_DESTINATARY_AMOUNT_EXCEEDED`, `MAX_AMOUNT_EXCEEDED`,
  `NEW_DESTINATARY_COOL_DOWN`, `NOT_AVAILABLE_ACCOUNT`.
  `PredictGetPredictResult` member *names* are unchanged, but their *values*
  follow the new wire vocabulary, so the generated parser now rejects the old
  lowercase strings. No lowercase aliases are kept: there is no evidence Khipu
  still sends them. Prediction is not part of the supported facade.
- The #15 `direct_debit` compatibility overlay is retained unchanged: the new
  document still publishes only `regular_transfer`, `simplified_transfer` and
  `not_available` for `payment-get-payment.payment_method`.

## [0.3.2] - 2026-09-23

### Added

- **`create_charge` accepts an explicit, optional `notify_api_version` (#14).**
  It selects the contract Khipu uses for the charge's `notify_url` callback.
  A supplied value is sent unchanged as `"notify_api_version"`; omitting it, or
  passing `None`, leaves the key out of the request entirely. The SDK does
  **not** default it to `"3.0"` or to anything else, and does not restrict the
  value beyond Khipu's own free-string schema. Applications that rely on signed
  JSON notifications should request `"3.0"` explicitly.

### Fixed

- `notify_api_version=None` passed through `**extra_fields` used to be sent as
  `"notify_api_version": null`. As a named parameter, `None` now means
  omission, like the other optional charge fields.

### Notes

- Callers already passing `notify_api_version="3.0"` through `**extra_fields`
  keep the same call shape and the same request body. `**extra_fields` is
  unchanged.
- Retry behaviour (none), success-status handling (`201`, plus `200` for
  compatibility) and charge correlation fields are unchanged. No generated code
  or OpenAPI document changed.

## [0.3.1] - 2026-09-23

### Fixed

- **A PAC payment could not be retrieved with `get_instant_payment` (#15).**
  Observed against the live developer-mode API in parle-cl/telemaco#377:
  `GET /v3/payments/{id}` for an Automatic Payments charge returned
  `payment_method: "direct_debit"`, which Khipu's published Instant Payments
  document does not declare (it still lists only `regular_transfer`,
  `simplified_transfer` and `not_available`). The generated parser raised
  `ValueError`, so the call failed with `KhipuResponseError` and none of the
  verification fields could be read.

  `direct_debit` is now accepted for that field on that endpoint only, as a
  typed `PaymentGetPaymentPaymentMethod.DIRECT_DEBIT` member reachable through
  `raw`. `InstantPaymentStatus` is unchanged. Any other undeclared
  `payment_method`, and any undeclared `status`, `status_detail` or
  `funds_source`, is still reported as `KhipuResponseError`.

### Added

- `tools/spec_compat.py`, a generation-time compatibility overlay.
  `make generate-instant` now generates from a derived copy of the Instant
  Payments spec under `build/openapi/`; the committed spec is still Khipu's
  document byte for byte and its sha256 lock is unchanged. The overlay's single
  entry is strict: generation fails if Khipu publishes `direct_debit` itself
  (the entry is then obsolete and must be deleted) or changes the enum in any
  other way. `make check-spec-compat` runs the same check without writing
  anything.
- CI fails when committed `generated/` differs from a fresh
  `make generate-all`, and the `spec-drift` watch checks the overlay against
  the freshly published spec.

### Notes

- This is a deliberate, temporary divergence from Khipu's published schema,
  kept only until Khipu documents `direct_debit`. No retry behaviour changed and
  nothing new is logged.

## [0.3.0] - 2026-09-22

Adopts the Automatic Payments OpenAPI document Khipu republished after the
2026-08-28 revision this SDK had pinned. One upstream document carries the
fixes for both #10 (subscription status contract) and #9
(`max_amount_per_charge`), so they land together.

Also re-syncs the Instant Payments document (#12), so both committed specs
match what Khipu publishes and the `spec-drift` watch is green for both.

Contains **breaking changes** to the Automatic Payments facade.

### Fixed

- **PAC subscription retrieval raised on valid provider responses (#10).**
  Observed against the live developer-mode API in parle-cl/telemaco#377:
  - a pre-signing subscription with `status: "PENDING"` raised
    `ValueError: 'PENDING' is not a valid SubscriptionStatusStatus`;
  - a post-signing subscription that omitted `customer_bank_code` raised
    `KhipuResponseError (KeyError: 'customer_bank_code')`.

  Khipu's current document resolves both: `PENDING` is a declared status, and
  `customer_bank_code` has been removed from the schema entirely. It also adds
  `DISCARDED`, which would have caused the identical enum failure on an
  unsubscribed mandate.
- **`create_charge` could not read a successful charge.** Khipu now documents
  `POST /v1/automatic-payment/charge-intent` as `201 Created`; the generated
  client parsed only `200`, so a successful charge surfaced as
  `KhipuResponseError: "success status with no usable body"`. This had not been
  hit in practice because no PAC charge had been attempted yet.

### Added

- **`max_amount_per_charge` (#9)** is now a required, typed parameter of
  `create_subscription`, matching Khipu's required field. It is validated
  against the currency's minor-unit scale like `max_amount`.
- `AutomaticSubscriptionStatus` now carries `developer` and
  `service_reference`. Khipu returns `service_reference` as an empty string
  until the customer signs; `""` is passed through unchanged and never rewritten
  to `None`.
- Charge rejections (`422`) are raised as `KhipuApiError` with Khipu's
  `error_message` as the message and `error_code` reachable through `payload`.
- The generated client now covers `DELETE /v1/automatic-payment/subscription/{id}`
  (unsubscribe). It is deliberately **not** exposed on `KhipuClient`: the
  operation is irreversible and exposing it is a separate API-design decision.
- A release-metadata regression (`tests/unit/test_release_metadata.py`) ties
  `project.version` to a dated CHANGELOG section and to the README's pinned
  install examples. Merging to master tags whatever version `pyproject.toml`
  declares, and silently does nothing when that tag already exists, so an
  un-bumped version is a defect this now catches before merge.

### Changed

- **`create_subscription` requires `max_amount_per_charge`.** Breaking for
  callers of 0.2.0.
- **`create_charge` makes `body`, `custom` and `transaction_id` optional**,
  matching Khipu's revised `ChargeRequest`, which no longer requires them. An
  omitted field is left out of the request entirely -- never sent as `null`,
  never given a fabricated value. Callers that pass them are unaffected. They
  remain the only merchant-side correlation fields Khipu echoes back, so an
  application reconciling charges against its own records should keep requiring
  them in its own service layer; that is application policy, not a constraint
  the SDK imposes on every consumer.
- `AutomaticSubscriptionStatus` gained `developer` and `service_reference`
  before `raw`. Keyword construction and attribute reads are unaffected;
  positional construction of this result type would be.
- `create_charge` accepts Khipu's documented `201` and, for compatibility with
  the contract Khipu published until 2026-09, a `200` carrying a usable
  `ChargeResult`. That allowance is a closed set of exactly those two statuses:
  any other 2xx -- `202 Accepted` most importantly -- is reported as
  `KhipuResponseError` rather than being given the meaning of a created charge.

### Instant Payments spec sync (#12)

Khipu's Instant Payments revision is **additive only**. No endpoint, response
status, required field, enum or security scheme changed; the `status`
(`pending` / `verifying` / `done`) and `status_detail` vocabularies are
identical to the previous document. Most of the diff is Spanish terminology
(*reversa* -> *devolución*) and added response examples.

- `payment-get-payment` gains three **optional** fields: `refunds`,
  `total_refunded` and `void_payout_date`. They refine *when money actually
  moved*, which `status_detail` alone cannot express: a refund with
  `status: expired` never pays out, and `total_refunded` excludes those.
- These are **not promoted onto `InstantPaymentStatus`** in this release.
  Promoting them is an API-design decision (`refunds` is a list of objects and
  would need a stable result type of its own), not a spec-sync one. They are
  reachable through `raw`, and are covered by regressions so promoting them
  later is a small step.
- No facade change was required, and none was made. Every Instant Payments
  invariant is unchanged: no idempotency primitive exists in the document (the
  word does not appear in it at all), `transaction_id` remains correlation
  only, there is still no automatic retry, `get_instant_payment` remains the
  authoritative retrieval primitive, incomplete success bodies remain
  `KhipuResponseError`, payer PII stays unpromoted and out of `repr`, and money
  stays exact `Decimal`.
- Instant Payments declares exactly `200` for both payment endpoints, and a
  regression now pins that the Automatic Payments charge compatibility
  allowance (201 plus 200) did not leak into them: `201`, `202` and `204` are
  rejected there.

### Notes

- Khipu's `ChargeError` vocabulary mentions `IDEMPOTENCY_KEY_REUSED`, but the
  published `ChargeRequest` defines no idempotency field or header. The SDK
  therefore sends none and treats no field as one -- `transaction_id` included.
  Retry guidance is unchanged: the SDK still performs no retries. Tracked for
  investigation in parle-cl/telemaco#377.

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
