# Khipu Python SDK

[![CI](https://github.com/parle-cl/khipu-python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/parle-cl/khipu-python-sdk/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/parle-cl/khipu-python-sdk?include_prereleases)](https://github.com/parle-cl/khipu-python-sdk/releases)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

High-level Python SDK for integrating with **Khipu Instant Payments (v3)** and
**Khipu Automatic Payments / PAC (v1)**, built from official OpenAPI specifications.

The SDK is a thin, typed boundary around what Khipu actually publishes. It
validates money before anything is serialised, maps every failure onto a precise
exception, and promotes the fields you need to verify a payment onto stable
result types. It deliberately does **not** paper over the guarantees Khipu does
not offer — see [Idempotency](#idempotency-read-this-before-you-retry).

---

## Key principles

- All hand-written source code is **in English**.
- **Never edit generated code** under `generated/`.
- Regeneration is **repeatable and automated** (`make generate-all`).
- Your application imports only `khipu_sdk`, never `generated.*`.
- Money is **`Decimal`** end to end; `float` appears only at the final wire boundary.
- **No retries anywhere.** Retry policy belongs to the caller.

## Repository structure

```text
khipu-python-sdk/
  openapi/
    khipu-instant-payments.yaml
    khipu-automatic-payments.yaml

  generated/
    __init__.py            # makes generated/ a real package so it ships in the wheel
    instant_payments/      # OpenAPI generated client (do not edit)
    automatic_payments/    # OpenAPI generated client (do not edit)

  khipu_sdk/
    client.py              # KhipuClient (high-level wrapper)
    config.py              # KhipuConfig
    errors.py              # SDK exception taxonomy
    money.py               # Decimal handling + currency minor-unit validation
    types.py               # stable result dataclasses
    py.typed               # PEP 561 marker

  tools/
    smoke_installed.py     # smoke test run against the *installed* wheel

  tests/
    unit/
    integration/

  Makefile
  pyproject.toml
```

## Khipu API documentation

Official Khipu API documentation: https://docs.khipu.com/

This repository uses the official OpenAPI specifications published by Khipu,
downloaded directly from their documentation site and pinned by sha256 in
`OPENAPI_SPECS.lock.json`.

## Requirements

- Python **3.10+**
- (for regeneration only) `openapi-python-client`

Runtime dependencies are `httpx`, `attrs` and `python-dateutil`; they are
installed automatically.

## Installation

### From Git (recommended)

The published wheel contains both `khipu_sdk` and the generated clients, so a
plain Git install is fully functional.

In `requirements.txt`:

```text
khipu-python-sdk @ git+ssh://git@github.com/parle-cl/khipu-python-sdk.git@v0.2.0
```

Or in `pyproject.toml`:

```toml
[project]
dependencies = [
  "khipu-python-sdk @ git+ssh://git@github.com/parle-cl/khipu-python-sdk.git@v0.2.0",
]
```

Pin a tag rather than `@master` so an upstream change cannot silently alter
payment behaviour in your application.

### From a local checkout (SDK development)

```bash
python3 -m venv .venv
source .venv/bin/activate
make install-dev
```

### Verifying an install

`make smoke-dist` builds the wheel, installs it into a throwaway virtualenv and
creates and retrieves a payment against a local mock server. It fails if the
distribution is missing the generated clients. CI runs it on every push.

## Configuration

Environment variables:

- `KHIPU_API_KEY` (required)
- `KHIPU_BASE_URL` (optional, default `https://payment-api.khipu.com`)
- `KHIPU_TIMEOUT` (optional, default `10.0` seconds)

```python
from khipu_sdk import KhipuClient, KhipuConfig

client = KhipuClient(KhipuConfig.from_env())
```

Or explicitly, which is what you want when the values come from your framework's
settings rather than the process environment:

```python
import httpx
from khipu_sdk import KhipuClient, KhipuConfig

client = KhipuClient(
    KhipuConfig(
        api_key=settings.KHIPU_API_KEY,
        base_url=settings.KHIPU_BASE_URL,
        # A float applies to connect/read/write/pool alike. Pass an
        # httpx.Timeout to control the phases independently.
        timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0),
    )
)
```

`KhipuConfig.api_key` is excluded from `repr()`, so the credential cannot leak
through logging, Sentry local-variable capture or a debug page. The timeout is
never `None`: an unbounded default would let a stalled request pin a worker.

## Money

`Decimal` is the canonical representation. The SDK performs no financial
arithmetic in binary floating point.

```python
from decimal import Decimal

client.create_instant_payment(amount=Decimal("10000"), currency="CLP", ...)
```

`amount` accepts `Decimal`, `int`, `str` or `float`. `float` is converted through
`Decimal(str(value))` so the SDK adds no floating-point noise of its own, but any
imprecision already present in your float survives — pass `Decimal` when
exactness matters.

Amounts returned by `get_instant_payment()` are `Decimal`, so you never have to
compare a `Decimal` against a `float`.

### Currency minor units

Every amount is validated against the currency's ISO-4217 minor-unit scale
**before** serialisation, and amounts are **never silently rounded**:

| Currency | Decimals | | Currency | Decimals |
|---|---|---|---|---|
| CLP | 0 | | EUR | 2 |
| CLF | 4 | | MXN | 2 |
| ARS | 2 | | PEN | 2 |
| BOB | 2 | | USD | 2 |
| COP | 2 | | | |

```python
client.create_instant_payment(amount=Decimal("10000"),   currency="CLP", ...)  # ok
client.create_instant_payment(amount=Decimal("10000.0000"), currency="CLP", ...)  # ok
client.create_instant_payment(amount=Decimal("9700.5"),  currency="CLP", ...)  # KhipuValidationError
```

A rejected amount raises `KhipuValidationError` and **no HTTP request is made**.

## Errors

All exceptions derive from `KhipuError` and are picklable, so they survive Celery
result backends.

| Exception | Meaning | Reached Khipu? |
|---|---|---|
| `KhipuConfigurationError` | Generated clients missing / SDK unusable as configured | No |
| `KhipuValidationError` | Invalid input rejected locally (currency, fractional CLP, unserialisable payload) | **No** |
| `KhipuTimeoutError` | Request timed out | **Unknown** — see below |
| `KhipuConnectionError` | DNS / TCP / TLS / broken stream | Usually no; check the flag |
| `KhipuApiError` | Khipu answered with a non-success status | **Yes** |
| `KhipuResponseError` | Success status, but the body was malformed or incomplete | Yes |

`KhipuTimeoutError` and `KhipuConnectionError` share a base,
`KhipuTransportError`, and carry:

```python
except KhipuTransportError as exc:
    if exc.request_may_have_been_delivered:
        ...  # ambiguous: Khipu may have processed the request
    else:
        ...  # the connection was never established; nothing reached Khipu
```

That flag is derived from httpx's own exception taxonomy. It is `False` only
when the transport can prove the connection was never established. The SDK never
claims certainty httpx does not provide.

`KhipuApiError` preserves Khipu's diagnostics instead of discarding them:

```python
except KhipuApiError as exc:
    exc.status_code   # 400
    exc.message       # "Monto inválido"      (derived from Khipu's body)
    exc.payload       # {"message": "Monto inválido", "code": 42}  (parsed JSON, or None)
    exc.body          # bounded raw body text
```

Bodies are truncated before they reach a message, and request headers are never
touched, so the API key cannot leak through an exception.

## Idempotency (read this before you retry)

> **`create_instant_payment` is NOT idempotent.**
>
> - Khipu publishes **no idempotency key** for payment creation.
> - `transaction_id` is a merchant **correlation** field. Khipu documents **no
>   deduplication** on it. Do not treat it as a uniqueness guarantee.
> - Khipu publishes **no endpoint to look a payment up by `transaction_id`** —
>   `get_instant_payment()` takes Khipu's `payment_id` only.
> - The SDK performs **no automatic retries** and keeps **no duplicate-request
>   cache**.
>
> **A `KhipuTimeoutError` on create-payment is an ambiguous outcome: Khipu may
> have created a live, payable payment.** Blindly retrying can produce a second
> live payment for the same order.

What a consuming application should do:

1. Persist a payment-intent row (your reference, amount, currency, state) and
   **commit it before** calling `create_instant_payment`.
2. Enforce uniqueness on your own reference locally — Khipu will not.
3. On an ambiguous failure, mark the intent *unknown*, not *failed*, and
   reconcile. Do not auto-retry.
4. If you must create again after an ambiguous attempt, use a **new**
   `transaction_id` so both attempts stay distinguishable.
5. Before recognising money, re-fetch with `get_instant_payment()` and verify
   `transaction_id`, `amount`, `currency`, `status` and `status_detail` against
   your own record. Do not trust a notification body alone.

## Correlation

Two opaque merchant fields are sent on creation and echoed back by
`get_instant_payment()`:

- `transaction_id` — your own reference (invoice, order or contribution id).
- `custom` — free-form extra payload.

```python
created = client.create_instant_payment(
    amount=Decimal("10000"),
    currency="CLP",
    subject="Order 123",
    transaction_id="ORDER-123",
    custom="ORDER-123-extra",
    return_url="https://your-app.example.com/payments/return/",
    cancel_url="https://your-app.example.com/payments/cancel/",
    notify_url="https://your-app.example.com/payments/webhook/khipu/",
)

fetched = client.get_instant_payment(payment_id=created.payment_id)
assert fetched.transaction_id == "ORDER-123"
```

Again: correlation, **not** idempotency.

## Usage

### Instant Payments (v3)

```python
from decimal import Decimal
from khipu_sdk import KhipuClient, KhipuConfig

client = KhipuClient(KhipuConfig.from_env())

created = client.create_instant_payment(
    amount=Decimal("10000"),
    currency="CLP",
    subject="Test payment",
    transaction_id="ORDER-123",
    body="Order #123",
    return_url="https://your-app.example.com/payments/return/",
    cancel_url="https://your-app.example.com/payments/cancel/",
    notify_url="https://your-app.example.com/payments/webhook/khipu/",
)
```

`create_instant_payment` returns `InstantPaymentCreateResult` with exactly what
Khipu's create response contains — no more:

| Field | Notes |
|---|---|
| `payment_id` | 12-char Khipu identifier |
| `payment_url` | main redirect URL |
| `simplified_transfer_url` | |
| `transfer_url` | |
| `app_url` | Khipu mobile app deep link |
| `ready_for_terminal` | |
| `raw` | escape hatch; excluded from `repr` |

Khipu's create response carries **no** status, amount, currency, expiry or
merchant reference. Those come from a follow-up fetch:

```python
payment = client.get_instant_payment(payment_id=created.payment_id)
```

`InstantPaymentStatus` promotes every field needed for verification, so you
never need to touch `raw`:

| Field | Type |
|---|---|
| `payment_id` | `str` |
| `transaction_id` | `Optional[str]` |
| `custom` | `Optional[str]` |
| `status` | `Optional[str]` — `pending`, `verifying`, `done` |
| `status_detail` | `Optional[str]` — see the table below |
| `amount` | `Optional[Decimal]` — Khipu publishes it as a decimal string; the facade converts |
| `currency` | `Optional[str]` |
| `receiver_id` | `Optional[int]` |
| `notification_token` | `Optional[str]` |
| `expires_date` | `Optional[datetime]` |
| `conciliation_date` | `Optional[datetime]` |
| `out_of_date_conciliation` | `Optional[bool]` |
| `raw` | escape hatch; excluded from `repr` |

`raw` is kept out of `repr` on purpose: the underlying Khipu model carries payer
PII (name, email, personal identifier, bank account number).

#### `status_detail` vocabulary

The values Khipu currently publishes, with its own semantics:

| Value | Khipu's meaning |
|---|---|
| `pending` | the payer has not started paying |
| `normal` | the payment was verified and settled through a standard payment method |
| `marked-paid-by-receiver` | the collector marked the charge as paid by other means |
| `rejected-by-payer` | the payer declared they will not pay |
| `marked-as-abuse` | the payer declared they will not pay and that the charge was unsolicited |
| `reversed` | the payment was voided by the merchant and the amount was **marked for return** to the payer |
| `partially-refunded` | part of the amount was **marked for return** to the payer through partial reversals |
| `fully-refunded` | the full amount was **marked for return** to the payer through one or more reversals |

Two points of precision:

- Khipu's wording for the last three is *marked for return* to the payer, not
  *returned*. Whether the money has actually moved back is a settlement
  question, and the SDK does not answer it.
- **`status == "done"` is not final forever.** A payment that reads `done` /
  `normal` today can later read `done` / `partially-refunded` or
  `done` / `fully-refunded`, because a payment can be reversed after it
  settles. Treating `done` as a terminal state is unsafe.

`status == "done"` alone is therefore not sufficient to recognise money. The SDK
reports provider state verbatim and makes no business decision about it:
deciding what a refund or reversal means for your own records is the consuming
application's job.

This vocabulary is Khipu's and can grow. The facade passes `status_detail`
through as a plain string rather than an SDK enum, so a value Khipu adds later
reaches you unchanged instead of raising.

### Automatic Payments (PAC)

```python
subscription = client.create_subscription(
    name="Jane Doe",
    email="jane.doe@example.com",
    max_amount=Decimal("50000"),
    currency="CLP",
    notify_url="https://your-app.example.com/pac/notify/",
    return_url="https://your-app.example.com/pac/return/",
    cancel_url="https://your-app.example.com/pac/cancel/",
)

status = client.get_subscription(subscription_id=subscription.subscription_id)

charge = client.create_charge(
    subscription_id=subscription.subscription_id,
    amount=Decimal("20000"),
    subject="Monthly fee",
    body="Subscription monthly charge",
    transaction_id="INVOICE-2026-0001",
    # Required by Khipu's ChargeRequest schema:
    error_response_url="https://your-app.example.com/pac/error/",
    custom="INVOICE-2026-0001",
    notify_url="https://your-app.example.com/pac/notify/",
    # Optional, local validation only; never sent to Khipu:
    currency="CLP",
)
```

The charge payload carries no currency — it is inherited from the subscription —
so pass `currency` if you want minor-unit validation applied to `amount`.

## Implemented operations

| Method | HTTP | Endpoint |
|---|---|---|
| `create_instant_payment` | POST | `/v3/payments` |
| `get_instant_payment` | GET | `/v3/payments/{id}` |
| `create_subscription` | POST | `/v1/automatic-payment/subscription` |
| `get_subscription` | GET | `/v1/automatic-payment/subscription/{id}` |
| `create_charge` | POST | `/v1/automatic-payment/charge-intent` |

Authentication is a single static API key sent as the `x-api-key` header on
every request. Khipu API v3 uses no request signing.

The generated clients under `generated/` cover more of Khipu's surface than the
facade deliberately exposes: cancelling a payment, `POST /v3/payments/{id}/void`,
`POST /v3/refunds`, `GET /v3/refund-wallet/balance`, `GET /v3/banks`,
`GET /v3/merchants/{id}/paymentMethods`, `GET /v3/predict`, and the receiver
endpoints. They are regenerated and kept in sync, but are not part of the
supported API and may change shape when the specs are refreshed. Promoting any
of them onto `KhipuClient` is a deliberate decision, not something to do because
the generated code exists.

Note that Khipu marks `POST /v3/payments/{id}/refunds` as obsolete in favour of
`POST /v3/payments/{id}/void`, and that it now refunds the full amount only.

## Out of scope

These are deliberate boundaries, not gaps waiting to be filled:

- **Webhooks.** The SDK sends `notify_url` but does not receive, verify or parse
  inbound Khipu notifications. That is framework-specific work (routing, CSRF,
  raw-body access, replay handling across Khipu's two-day retry window) and
  belongs in the consuming application.
- **Settlement / reconciliation.** Neither vendored spec exposes a settlement,
  report or payout endpoint. Khipu delivers settlement out of band. The closest
  per-payment evidence is `conciliation_date` / `out_of_date_conciliation` on
  `get_instant_payment()`.
- **Fee quotation.** *No currently implemented Khipu operation, and no endpoint
  in either vendored spec, returns the merchant processing fee before a payment
  is created.* `GET /v3/predict` returns payer transfer limits, not fees;
  `integrator_fee` is a commission you send, not one you read. This SDK does not
  invent a fee formula. If you need to show a fee before the payer commits, that
  number has to come from your commercial agreement with Khipu, reconciled later
  against actual settlement.
- **Retries.** See [Idempotency](#idempotency-read-this-before-you-retry).

## OpenAPI specifications and regeneration

Specs live under `openapi/` and are pinned by sha256:

```bash
make download-specs   # refresh from docs.khipu.com
make lock-specs       # update OPENAPI_SPECS.lock.json
make verify-spec-lock # CI check
make generate-all     # regenerate both clients
```

`make generate-all` also recreates `generated/__init__.py`, which packaging
depends on, so the file survives regeneration.

CI verifies the lock against the **committed** specs, which is what makes
generation reproducible. It deliberately does not download specs in the blocking
path: `make download-specs` overwrites the committed files, so verifying
afterwards would compare upstream against the pin rather than checking this
repository, and any Khipu documentation edit would turn unrelated pull requests
red. Upstream drift is watched by a separate non-blocking `spec-drift` job that
reports the diff.

Adopting a newer published spec is therefore a deliberate change:

```bash
make download-specs
make lock-specs
make generate-all
make check          # review the generated diff and adjust the facade if needed
```

The code generator is pinned exactly (`openapi-python-client==0.28.0`) in the
`dev` extra. It is the build tool that produces the committed contents of
`generated/`, so a floating version would let a generator release change that
code with no change in this repository. Bumping it is a deliberate step:
change the pin, run `make generate-all`, and review the diff.

Never edit files under `generated/`. If behaviour needs to change, change the
`khipu_sdk` facade.

## Development

```bash
make check        # ruff + mypy + pytest
make test         # pytest
make lint         # ruff
make typecheck    # mypy
make build        # build the wheel
make smoke-dist   # build, install into a clean venv, smoke test the installed artifact
```

The test suite performs no network access; HTTP is intercepted with
`pytest-httpx` at the transport layer, so tests exercise the real path from the
facade through serialization, httpx and generated response parsing.

### Pinned tooling

`ruff`, `mypy` and `openapi-python-client` are pinned exactly in the `dev`
extra. All three decide what CI accepts, and all three change their verdict on
unchanged code as they release: a linter adds rules, a type checker tightens
inference, a generator emits different output. Left floating, `make check`
passes locally and fails in CI purely because the runner resolved a newer
version.

`ruff` also skips `generated/` (see `[tool.ruff]`), because that code is
machine-produced and must never be hand-edited, so findings there could only be
silenced rather than fixed.

Bumping any of the three is a deliberate maintenance step: change the pin, run
`make check` (or `make generate-all` for the generator), and deal with whatever
the new version reports. At the time of writing, moving to a current `ruff`
would surface roughly 70 style findings in this repository's own code, mostly
`Optional[X]` to `X | None` modernisation -- a migration worth doing on its own,
not as a side effect of an unrelated build.

The live integration test is **disabled by default**:

```bash
export KHIPU_RUN_INTEGRATION_TESTS=1
export KHIPU_API_KEY="..."
make test
```
