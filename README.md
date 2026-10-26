# Khipu Python SDK

[![CI](https://github.com/yaselc/khipu-python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/yaselc/khipu-python-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/khipu-python-sdk.svg)](https://pypi.org/project/khipu-python-sdk/)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/yaselc/khipu-python-sdk/blob/master/LICENSE)

> **Community-maintained Python SDK for the Khipu API.** This project is
> independently maintained and is **not affiliated with, endorsed by, or
> maintained by Khipu**. "Khipu" refers to the payment service whose public API
> this SDK calls. For questions about your Khipu account, contract or API
> credentials, contact Khipu directly; for problems with this SDK, use this
> repository's [issues](https://github.com/yaselc/khipu-python-sdk/issues).

High-level Python SDK for integrating with **Khipu Instant Payments (v3)** and
**Khipu Automatic Payments / PAC (v1)**, generated from the OpenAPI
specifications Khipu publishes on its documentation site.

The SDK is a thin, typed boundary around what Khipu actually publishes. It
validates money before anything is serialised, maps every failure onto a precise
exception, and promotes the fields you need to verify a payment onto stable
result types. It deliberately does **not** paper over the guarantees Khipu does
not offer — see [Idempotency](#idempotency-read-this-before-you-retry).

---

## Key principles

- All hand-written source code is **in English**.
- **Never edit generated code** under `khipu_sdk/_generated/`.
- Regeneration is **repeatable and automated** (`make generate-all`).
- Your application imports only `khipu_sdk`, never `khipu_sdk._generated.*`.
- Money is **`Decimal`** end to end; `float` appears only at the final wire boundary.
- **No retries anywhere.** Retry policy belongs to the caller.

## Repository structure

```text
khipu-python-sdk/
  openapi/
    khipu-instant-payments.yaml
    khipu-automatic-payments.yaml

  khipu_sdk/
    _generated/            # private; not a supported import path
      __init__.py          # recreated by `make generate-all`
      instant_payments/    # OpenAPI generated client (do not edit)
      automatic_payments/  # OpenAPI generated client (do not edit)
    client.py              # KhipuClient (high-level wrapper)
    config.py              # KhipuConfig
    errors.py              # SDK exception taxonomy
    money.py               # Decimal handling + currency minor-unit validation
    types.py               # stable result dataclasses
    py.typed               # PEP 561 marker

  tools/
    check_dist.py          # wheel/sdist content and metadata check (pre-publish gate)
    smoke_installed.py     # smoke test run against the *installed* wheel or sdist

  tests/
    unit/
    integration/

  Makefile
  pyproject.toml
```

## Khipu API documentation

Khipu's own API documentation: https://docs.khipu.com/

This repository uses the OpenAPI specifications Khipu publishes there,
downloaded directly from its documentation site and pinned by sha256 in
`OPENAPI_SPECS.lock.json`. It is not the source of truth for Khipu's API; when
this README and Khipu's documentation disagree, Khipu's documentation wins.

## Requirements

- Python **3.10+**
- (for regeneration only) `openapi-python-client`

Runtime dependencies are `httpx`, `attrs` and `python-dateutil`; they are
installed automatically.

## Installation

### From PyPI

The SDK is published on PyPI as
[`khipu-python-sdk`](https://pypi.org/project/khipu-python-sdk/). The import
name is `khipu_sdk`.

```bash
pip install khipu-python-sdk==0.4.0
```

In `requirements.txt`:

```text
khipu-python-sdk==0.4.0
```

Or in `pyproject.toml`:

```toml
[project]
dependencies = [
  "khipu-python-sdk==0.4.0",
]
```

Pin an exact version so an upstream release cannot silently alter payment
behaviour in your application, and read the
[changelog](https://github.com/yaselc/khipu-python-sdk/blob/master/CHANGELOG.md)
before moving the pin.

### From source with Git

Each PyPI release corresponds to a `vX.Y.Z` tag in this repository. The wheel
built from a tag contains both `khipu_sdk` and the generated clients, so a Git
install is equally functional:

```text
khipu-python-sdk @ git+https://github.com/yaselc/khipu-python-sdk.git@v0.4.0
```

Pin a tag rather than `@master`: `master` is not a release.

### From a local checkout (SDK development)

```bash
python3 -m venv .venv
source .venv/bin/activate
make install-dev
```

### Verifying an install

`make smoke-dist` builds the wheel and sdist, checks their contents with
`tools/check_dist.py`, installs each into a throwaway virtualenv and creates and
retrieves a payment against a local mock server. It fails if a distribution is
missing the generated clients, ships anything outside its allowlist, installs
any top-level package other than `khipu_sdk`, or has a long description (this
README, as shown on PyPI) with a link or image that is relative to the
repository. CI runs it on every push.

## Configuration

Environment variables:

- `KHIPU_API_KEY` (required)
- `KHIPU_BASE_URL` (optional, default `https://payment-api.khipu.com`)
- `KHIPU_TIMEOUT` (optional, default `10.0` seconds)

`KhipuConfig.from_env(prefix="SHOP_")` reads `SHOP_API_KEY`, `SHOP_BASE_URL`
and `SHOP_TIMEOUT` instead. An unset `BASE_URL` or `TIMEOUT` uses the default.
A variable that is set but empty is an error, not a silent fallback to the
default.

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

### Validation

`KhipuConfig` checks its values when it is constructed, whether directly or
through `from_env()`, and `KhipuClient` checks them again before building its
HTTP clients. An invalid value raises `KhipuConfigurationError` before any
request can be made:

- `api_key` must be a non-empty string of visible ASCII characters. Whitespace,
  including a trailing newline from a secrets file, is rejected, not stripped.
- `base_url` must be an absolute `https://` or `http://` URL with a valid
  hostname (a DNS name, IPv4 address or bracketed IPv6 address) and an
  optional port and path. It must not contain credentials (`user:pass@`), a
  fragment (`#`), whitespace or non-ASCII characters; write an
  internationalised hostname in its `xn--` form. `http://` stays supported
  for local mock servers and tests; use `https://` for Khipu itself. The URL
  is never rewritten.
- `timeout` must be an `int` or `float` number of seconds that is finite and
  greater than zero, or an `httpx.Timeout` whose connect, read, write and pool
  phases all are. `None`, booleans, strings, zero, negative values, NaN and
  infinity are rejected, and so is an `httpx.Timeout` with any phase left
  unbounded (`None`). An accepted `httpx.Timeout` is kept as the same object.
  The SDK adds no upper limit of its own.

`KhipuConfigurationError` is also a `ValueError`, so code that caught the bare
`ValueError` `from_env()` used to raise keeps working. Its message names the
setting that was rejected but never its value, so an API key, or a URL or
variable that holds one by mistake, does not reach your logs.

### Client lifecycle

A `KhipuClient` holds up to two HTTP connection pools, one for Instant
Payments and one for Automatic Payments. Each pool is created on the first
request to its API and kept for reuse. Release them when you are done with the
client, either with a `with` block:

```python
from khipu_sdk import KhipuClient, KhipuConfig

with KhipuClient(KhipuConfig.from_env()) as client:
    status = client.get_instant_payment(payment_id=payment_id)
```

or by calling `close()` yourself:

```python
client = KhipuClient(KhipuConfig.from_env())
try:
    status = client.get_instant_payment(payment_id=payment_id)
finally:
    client.close()
```

Which one fits depends on how long the client lives:

- **Scripts, management commands and one-off jobs:** use a `with` block, so the
  pools are closed when the block ends, including when it ends with an
  exception.
- **Long-lived processes** such as a Django or Flask web worker or a Celery
  worker: create one client per process and reuse it, so connections are
  pooled across requests, and call `close()` from your shutdown hook (for
  example `atexit`, or Celery's `worker_process_shutdown` signal). Create the
  client in the process that uses it, after any fork; do not share one client,
  or its pools, across processes. The SDK makes no thread-safety promise
  beyond what httpx itself provides, and none for `close()` running while
  another thread is making a request.

The lifecycle contract:

- `close()` closes only the pools that exist. A client that never called an
  API, or called only one of them, does not build a pool just to close it.
- `close()` is idempotent: calling it again, or leaving a `with` block after
  an explicit `close()`, does nothing.
- A closed client stays closed. Every operation on it raises
  `KhipuConfigurationError` before any validation or request, and entering a
  closed client in a `with` block raises the same error. Create a new
  `KhipuClient` instead; pools are never reopened.
- `close()` does not cancel or interrupt a request that is already in
  progress.
- If closing one pool raises, the other is still closed, each failure is
  logged on the `khipu_sdk.client` logger (exception type only), and the first
  failure is re-raised. The client counts as closed even then. When a `with`
  block exits because of an exception, that exception always propagates: a
  cleanup failure is logged and never replaces it, so for example a
  `KhipuTimeoutError` with its ambiguity flag is not lost.

The same rules apply whether you call `close()` or use `with`.

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

The check is on the amount's value, not on how many digits it is written with.
An amount is valid when it has no nonzero digit beyond the currency's scale, so
trailing zeros after the decimal point never make an amount invalid.

CLP has no minor unit, so a CLP amount must be a whole number of pesos.
`Decimal("10000.0000")` is valid for CLP: it is written with four decimal places,
but its fractional part is zero, so it is exactly the integer 10000 (and is sent
to Khipu as `10000`). A CLP amount with a nonzero fractional part, such as
`Decimal("9700.5")`, is rejected:

```python
client.create_instant_payment(amount=Decimal("10000"),      currency="CLP", ...)  # ok
client.create_instant_payment(amount=Decimal("10000.0000"), currency="CLP", ...)  # ok: fractional part is zero
client.create_instant_payment(amount=Decimal("9700.5"),     currency="CLP", ...)  # KhipuValidationError
```

CLF (Unidad de Fomento) has four decimal places, so a CLF amount may carry up
to four nonzero decimal digits and no more:

```python
client.create_instant_payment(amount=Decimal("1.2345"),  currency="CLF", ...)  # ok: four decimal places
client.create_instant_payment(amount=Decimal("1.23456"), currency="CLF", ...)  # KhipuValidationError
```

A rejected amount raises `KhipuValidationError` and **no HTTP request is made**.
The SDK never rounds it to fit the currency: round it yourself, deliberately,
if that is what your application means.

### Exactness on the wire

Khipu's API schemas carry amounts as JSON numbers, and the generated clients
type them as `float`. Whole amounts are sent as integers, exact at any size.
An amount with a fractional part is sent as a float, which Python writes as the
shortest decimal that reads back as the same float, so ordinary amounts such as
`Decimal("0.1")`, `Decimal("19.99")` or `Decimal("1.2345")` reach Khipu
exactly as written.

A float holds only about 15 to 17 significant digits. A fractional amount that
would reach the wire as a different decimal value, such as
`Decimal("1234567890123.4567")`, is rejected with `KhipuValidationError` before
any request, never rounded. This also applies to PAC charges sent without a
`currency`, where no minor-unit check is possible. It is a limit of the wire
format, not a statement about which amounts Khipu accepts: Khipu applies its
own limits to every amount.

## Errors

All exceptions derive from `KhipuError` and are picklable, so they survive Celery
result backends.

| Exception | Meaning | Reached Khipu? |
|---|---|---|
| `KhipuConfigurationError` | Invalid `KhipuConfig` value, generated clients missing / SDK unusable as configured. Also a `ValueError` | No |
| `KhipuValidationError` | Invalid input rejected locally (currency, fractional CLP, unserialisable payload) | **No** |
| `KhipuTimeoutError` | Request timed out | **Unknown** — see below |
| `KhipuConnectionError` | DNS / TCP / TLS / broken stream | Usually no; check the flag |
| `KhipuApiError` | Khipu answered with a non-success status | **Yes** |
| `KhipuResponseError` | Success status, but the body was malformed, incomplete or came with an undocumented status | **Yes** — on a create, Khipu may have acted; see below |

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

Every non-2xx status is a `KhipuApiError` with its real `status_code`, even when
the body is empty, is not JSON, or does not match the error schema Khipu
documents. `payload` is then `None` (or whatever JSON Khipu did send), so read it
defensively rather than indexing into it.

`KhipuResponseError` means Khipu answered with a 2xx the SDK could not use: the
body was malformed or incomplete, or the status is not one Khipu documents for
that operation. It keeps what Khipu sent:

```python
except KhipuResponseError as exc:
    exc.status_code   # 200
    exc.body          # bounded raw body text, or None when it was empty
```

Bodies are truncated (to 500 characters plus a marker) before they reach an
exception, and request headers are never touched, so the API key cannot leak
through an exception.

### What a partial response does and does not tell you

- **A `KhipuApiError` is a definite answer.** Khipu received the request and
  refused it, whatever the body looked like. It is not a transport ambiguity.
- **A `KhipuResponseError` on a create operation (`create_instant_payment`,
  `create_subscription`, `create_charge`) is an outcome to reconcile, not a
  failure.** Khipu answered with a success-range status, so it may have created
  the payment, subscription or charge even though the SDK could not read the
  answer. Treat it like an ambiguous timeout: do not retry blindly.
- **An identifier in `exc.body` is evidence, not proof.** If the bounded body
  contains a `payment_id`, store it and re-fetch with `get_instant_payment()`
  before deciding anything. It does not show that the payment was created
  correctly, was paid or settled, and the SDK does not extract it for you
  because the body failed validation. A body longer than the bound may not
  contain it at all.
- **A 2xx status alone means nothing more.** The SDK never infers success from
  the status code: only a body that parses into the documented result does.

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
> live payment for the same order. The same holds for a `KhipuResponseError`
> on create-payment: Khipu answered with a success-range status the SDK could
> not read (see [Errors](#errors)).

What a consuming application should do:

1. Persist a payment-intent row (your reference, amount, currency, state) and
   **commit it before** calling `create_instant_payment`.
2. Enforce uniqueness on your own reference locally — Khipu will not.
3. On an ambiguous failure (`KhipuTimeoutError`, `KhipuConnectionError` with
   `request_may_have_been_delivered`, or `KhipuResponseError`), mark the intent
   *unknown*, not *failed*, and reconcile. Keep `exc.status_code` and `exc.body`
   of a `KhipuResponseError` with the intent: a `payment_id` in the body is the
   only lookup key Khipu offers. Do not auto-retry.
4. If you must create again after an ambiguous attempt, use a **new**
   `transaction_id` so both attempts stay distinguishable.
5. Before recognising money, re-fetch with `get_instant_payment()` and verify
   `transaction_id`, `amount`, `currency`, `status` and `status_detail` against
   your own record. Do not trust a notification body alone.

## Correlation

Two opaque merchant fields are sent on creation and echoed back by
`get_instant_payment()`:

- `transaction_id` — your own reference for the payment, such as an order or
  invoice number. It is a required parameter of `create_instant_payment`.
- `custom` — free-form data you attach to the payment, such as a cart summary
  or an internal correlation token. Khipu's schema types it as a string.

Use `transaction_id` for the reference you look the payment up by in your own
records, and `custom` for any extra context you want back with it. Khipu
documents no deduplication or other merchant-visible processing for either;
the SDK treats both as opaque strings.

`create_instant_payment` has no explicit `custom` parameter. Pass it as a
keyword argument and it goes through
[`**extra_fields`](#additional-request-fields-extra_fields), which the
generated `PaymentPostPayment` model declares and sends as `"custom"`:

```python
from decimal import Decimal

created = client.create_instant_payment(
    amount=Decimal("10000"),
    currency="CLP",
    subject="Order 123",
    transaction_id="ORDER-123",
    # Merchant-side correlation data; sent as the JSON field "custom".
    custom="order=ORDER-123;cart=42;channel=web",
    return_url="https://your-app.example.com/payments/return/",
    cancel_url="https://your-app.example.com/payments/cancel/",
    notify_url="https://your-app.example.com/payments/webhook/khipu/",
)

fetched = client.get_instant_payment(payment_id=created.payment_id)
assert fetched.transaction_id == "ORDER-123"
assert fetched.custom == "order=ORDER-123;cart=42;channel=web"
```

Again: correlation, **not** idempotency. Neither `transaction_id` nor `custom`
prevents a second payment from being created; see
[Idempotency](#idempotency-read-this-before-you-retry).

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
| `partially-refunded` | part of the amount was **marked for return** to the payer through partial refunds |
| `fully-refunded` | the full amount was **marked for return** to the payer through one or more refunds |

Two points of precision:

- Khipu's wording for the last three is *marked for return* to the payer, not
  *returned*. `status_detail` does not tell you the money moved.
- **`status == "done"` is not final forever.** A payment that reads `done` /
  `normal` today can later read `done` / `partially-refunded` or
  `done` / `fully-refunded`, because a payment can be reversed after it
  settles. Treating `done` as a terminal state is unsafe.

#### Whether a refund actually paid out

Khipu's 2026-09 revision added three optional fields to the payment body that
answer the settlement question `status_detail` cannot:

| Field | Meaning |
|---|---|
| `refunds[]` | each refund on the payment, with `status` of `pending`, `authorized`, `paid` or `expired`, plus `request_date` / `authorization_date` / `payout_date` / `expiration_date` |
| `total_refunded` | total returned to the payer. **Expired refunds are not counted.** |
| `void_payout_date` | when a voided payment's funds actually reached the payer |

A refund that reads `expired` was never confirmed within 15 business days and
will not be paid. So a payment can read `status_detail: partially-refunded`
while some of that amount never left — which is exactly why
`total_refunded` and `refunds[].status` exist.

These three are **optional**, and the facade does not promote them onto
`InstantPaymentStatus` yet: `refunds` is a list of objects and deserves a
stable result type rather than leaking generated models. Read them through
`raw` for now:

```python
status = client.get_instant_payment(payment_id=payment_id)

# Khipu omits these fields entirely when a payment has no refunds, so the
# generated model reports them as UNSET rather than as a value.
refunds = getattr(status.raw, "refunds", None)
if isinstance(refunds, list):
    paid_out = [r for r in refunds if r.status.value == "paid"]
```

`status == "done"` alone is therefore not sufficient to recognise money. The SDK
reports provider state verbatim and makes no business decision about it:
deciding what a refund or reversal means for your own records is the consuming
application's job.

This vocabulary is Khipu's and can grow. The facade passes `status_detail`
through as a plain string rather than an SDK enum, so a value Khipu adds later
reaches you unchanged instead of raising.

#### `payment_method` and PAC charges

A PAC charge (`create_charge`) is itself a Khipu payment, read back with
`get_instant_payment(payment_id=...)`. For those, the live API returns
`payment_method: "direct_debit"`, a value Khipu's published Instant Payments
document does **not** declare: it lists only `regular_transfer`,
`simplified_transfer` and `not_available`. A client generated verbatim from that
document could not read a PAC payment at all
([#15](https://github.com/yaselc/khipu-python-sdk/issues/15)).

The SDK therefore carries one deliberate, narrow compatibility allowance:
`direct_debit` is accepted for `payment_method` on `GET /v3/payments/{id}` and
nowhere else. `payment_method` is not promoted onto `InstantPaymentStatus`; it is
reachable through `raw` as the typed `PaymentGetPaymentPaymentMethod` enum, which
now includes `DIRECT_DEBIT`. Any *other* undeclared `payment_method` value, and
any undeclared value in `status`, `status_detail` or `funds_source`, still
raises `KhipuResponseError`, because that is provider-contract drift someone
should look at. See [Compatibility overlay](#compatibility-overlay) for how
the allowance is built and when it goes away.

### Automatic Payments (PAC)

```python
subscription = client.create_subscription(
    name="Jane Doe",
    email="jane.doe@example.com",
    max_amount=Decimal("50000"),          # monthly cap
    max_amount_per_charge=Decimal("20000"),  # per-charge cap; required by Khipu
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
    # Required by Khipu's ChargeRequest schema:
    error_response_url="https://your-app.example.com/pac/error/",
    notify_url="https://your-app.example.com/pac/notify/",
    # Optional in Khipu's schema; omitted fields are left out of the request:
    body="Subscription monthly charge",
    transaction_id="INVOICE-2026-0001",
    custom="INVOICE-2026-0001",
    # Optional; selects Khipu's notification contract. No SDK default:
    notify_api_version="3.0",
    # Optional, local validation only; never sent to Khipu:
    currency="CLP",
)
```

The charge payload carries no currency — it is inherited from the subscription —
so pass `currency` if you want minor-unit validation applied to `amount`.

`body`, `custom` and `transaction_id` are optional because Khipu's schema makes
them optional. Omitting one leaves the field out of the request entirely: the
SDK never sends `null` and never invents a value. They are still the only
merchant-side fields Khipu echoes back, so if you reconcile charges against your
own records, require them in **your** service layer — that is your policy to
enforce, not one the SDK imposes on every consumer.

`notify_api_version` selects the notification contract Khipu uses when it
calls `notify_url` for this charge. It is optional, as in Khipu's schema, and
the SDK **does not choose a default**: a value is sent exactly as given, and
omitting it (or passing `None`) leaves the field out of the request, so Khipu
applies whatever it does for an unspecified version. Khipu's schema types it as
a free string, so the SDK does not restrict the value either. If your
application relies on signed JSON notifications (Khipu's notification API
3.0), request `"3.0"` explicitly rather than depending on the unspecified
behaviour, and verify the callbacks your own merchant account receives.

`transaction_id` is **not** an idempotency key. Khipu's `ChargeError` vocabulary
mentions `IDEMPOTENCY_KEY_REUSED`, but the published `ChargeRequest` defines no
idempotency field or header, so the SDK sends none and treats no field as one.
The no-retry policy described above is unchanged.

#### Subscription ids are opaque

`subscription_id` is an **opaque provider string**. Khipu's schema example shows
a UUID, but the live API issues short mixed-case alphanumeric tokens such as
`7Kp2R9xTmQ4b`. The SDK imposes no syntax on it, and neither should you: store
it as text, and never validate, normalise or parse it as a UUID.

#### Subscription lifecycle

`get_subscription` returns Khipu's own `status` as a plain string:

| `status` | Meaning |
|---|---|
| `PENDING` | Created; the customer has not signed the bank mandate yet. |
| `SIGNED` | The mandate was signed. |
| `ENABLED` | The mandate is active. **Only this state permits a charge.** |
| `DISABLED` | The mandate is not usable. |
| `DISCARDED` | The subscription was unsubscribed. Not reversible. |

```python
status = client.get_subscription(subscription_id=subscription.subscription_id)

if status.status == "ENABLED":
    ...  # safe to charge
```

Two things to know about this endpoint:

- **`service_reference` comes back empty until the customer signs.** Khipu
  returns `""`, not `null` and not a missing key. The SDK passes that through
  unchanged: `""` is a value Khipu sent, and is never rewritten to `None`.
- **Khipu's `notify_url` callback is not authoritative.** The POST Khipu sends
  when the customer signs — or when a subscription is unsubscribed — carries
  `subscription_id` and a lowercase `status` (`"enabled"` / `"discarded"`),
  with no signature, no token and no provider-authenticated field. Anyone can
  send it. Treat it as a hint to call `get_subscription`, which is
  authenticated, and decide on that result.

#### Charge rejections

`create_charge` succeeds on Khipu's documented `201 Created`, and also on a
`200` carrying a usable `ChargeResult` — the contract Khipu published until
2026-09, kept for compatibility. That allowance is exactly those two statuses:
any other `2xx`, `202 Accepted` above all, raises `KhipuResponseError` rather
than being read as a created charge.

A refused charge comes back as `422` with Khipu's own reason, raised as
`KhipuApiError`. A `422` is a definite refusal even when its body is empty, is
not JSON or lacks `error_code`; `payload` is then `None` or incomplete, so read
it defensively:

```python
try:
    charge = client.create_charge(...)
except KhipuApiError as exc:
    if exc.status_code == 422:
        payload = exc.payload if isinstance(exc.payload, dict) else {}
        code = payload.get("error_code")  # e.g. MAX_AMOUNT_PER_CHARGE_EXCEEDED, or None
```

Khipu documents `MAX_AMOUNT_PER_CHARGE_EXCEEDED`, `MAX_MONTHLY_AMOUNT_EXCEEDED`,
`SUBSCRIPTION_NOT_CHARGEABLE`, `CURRENCY_MISMATCH`, `INVALID_AMOUNT`,
`IDEMPOTENCY_KEY_REUSED`, `INVALID_PAYLOAD` and `MERCHANT_ID_NOT_RESOLVED`.
`exc.message` carries Khipu's `error_message` text when there is one, and
`exc.body` the bounded raw body in every case.

### Additional request fields (extra_fields)

`create_instant_payment`, `create_subscription` and `create_charge` accept
extra keyword arguments. They are a **compatibility escape hatch** for request
fields that Khipu's published schema declares but the facade does not expose as
explicit parameters, for example `custom`, `bank_id`, `payer_email` or
`expires_date` on Instant Payments, and `service_reference`, `description` or
`image_url` on `create_subscription`. Every field of `create_charge`'s
`ChargeRequest` is already an explicit parameter, so there `**extra_fields`
only ever carries fields the schema does not declare.

`**extra_fields` is **not** a general request extension mechanism, and it does
not guarantee that Khipu accepts or acts on a field. What happens to a key:

- **The SDK wrapper forwards it verbatim.** It does not validate, convert,
  rename or drop extra fields. Unlike the explicit optional parameters, a
  value of `None` is sent as JSON `null` rather than omitted, so leave the key out
  instead of passing `None`. Values must already be JSON-ready: a
  `Decimal` or `datetime` under an undeclared key raises
  `KhipuValidationError` before anything is sent.
- **A field the schema declares** is parsed by the generated request model
  and sent under its declared name. The model does not check types or lengths
  (`custom=123` is sent as the number `123`); `date-time` fields such as
  `expires_date` take an ISO-8601 string, and a `datetime` object raises
  `KhipuValidationError` before anything is sent.
- **A field the schema does not declare, including a misspelling**, is kept by
  the generated model and sent as a top-level JSON key **without any error or
  warning**. `costum="..."` sends `"costum"` and does not set `custom`.
  Khipu's documentation does not say how it treats undeclared fields: it may
  ignore them, reject the request, or something else. Either way the field you
  meant to set was not set, and nothing in the SDK tells you.

So a typo in an extra field name is **not** prevented. To reduce that risk:

- Prefer explicit parameters where they exist, and spell them carefully:
  because of the catch-all, a misspelled explicit parameter such as
  `return_ulr=` is not a `TypeError` either. It becomes an extra field and is
  sent as `"return_ulr"`, while `return_url` stays unset.
- Use the field names exactly as they appear in the request schema of the
  [Khipu API documentation](#khipu-api-documentation) or in the committed specs
  under `openapi/`.
- Check the JSON body your code actually sends, for example with an offline
  test against a mock transport such as `pytest-httpx`, before relying on a
  field in production.

Extra fields cannot replace or bypass a named parameter: passing `amount`,
`currency` or any other named parameter twice is a `TypeError` raised by
Python before any validation or request. The minor-unit checks therefore
always apply to the amounts the SDK sends, and the currency the SDK sends is
always the validated `currency` argument (`create_charge` sends none). A
look-alike key such as `Amount` or `currency_code` is an undeclared field: it
is forwarded alongside the validated values and does not change them.

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

The generated clients under `khipu_sdk/_generated/` cover more of Khipu's
surface than the facade deliberately exposes: unsubscribing a PAC subscription
(`DELETE /v1/automatic-payment/subscription/{id}`, an irreversible operation),
cancelling a payment, `POST /v3/payments/{id}/void`,
`POST /v3/refunds`, `GET /v3/refund-wallet/balance`, `GET /v3/banks`,
`GET /v3/merchants/{id}/paymentMethods`, `GET /v3/predict`,
`GET /v3/predict/all`, and the receiver endpoints. They are regenerated and kept
in sync, but are not part of the supported API and may change shape when the
specs are refreshed. Promoting any of them onto `KhipuClient` is a deliberate
decision, not something to do because the generated code exists.

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
  is created.* `GET /v3/predict` and `GET /v3/predict/all` return payer
  transfer limits, not fees; `integrator_fee` is a commission you send, not one
  you read. This SDK does not invent a fee formula. If you need to show a fee
  before the payer commits, that number has to come from your commercial
  agreement with Khipu, reconciled later against actual settlement.
- **Retries.** See [Idempotency](#idempotency-read-this-before-you-retry).

## OpenAPI specifications and regeneration

Specs live under `openapi/` and are pinned by sha256:

```bash
make download-specs   # refresh from docs.khipu.com
make lock-specs       # update OPENAPI_SPECS.lock.json
make verify-spec-lock # CI check
make generate-all     # regenerate both clients
```

`make generate-all` writes the clients to `khipu_sdk/_generated/` and also
recreates `khipu_sdk/_generated/__init__.py`, which packaging depends on, so the
file survives regeneration. The generated clients are a private subpackage of
`khipu_sdk`, so the distribution installs `khipu_sdk` as its only top-level
package and cannot collide with an unrelated top-level `generated` package.

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
`khipu_sdk/_generated/`, so a floating version would let a generator release
change that code with no change in this repository. Bumping it is a deliberate
step: change the pin, run `make generate-all`, and review the diff.

Never edit files under `khipu_sdk/_generated/`. If behaviour needs to change,
change the `khipu_sdk` facade.

### Compatibility overlay

Rarely, the live API returns a value Khipu's own document does not declare.
The committed spec must stay Khipu's document byte for byte, and
`khipu_sdk/_generated/` must stay reproducible, so neither is edited. Instead,
`make generate-instant` runs `tools/spec_compat.py`, which writes a derived copy
of the Instant Payments spec to `build/openapi/` and generates from that.

The overlay currently has one entry: `direct_debit` is added to
`payment-get-payment.payment_method` (#15). The derived copy differs from
Khipu's document by exactly that one enum line, and `khipu_sdk/_generated/` by
exactly one enum member.

Each entry records the exact enum Khipu publishes today and refuses to apply
to anything else:

- if Khipu publishes the value itself, `make generate-all` fails and says the
  entry is obsolete. Delete the entry, regenerate, and remove the
  `TestUpstreamStillOmitsDirectDebit` guard in
  `tests/unit/test_instant_payments_spec_compat.py`;
- if the enum changes any other way, generation fails until the entry is
  reconciled with the new document;
- the non-blocking `spec-drift` job runs `make check-spec-compat` against the
  freshly published spec, so either case is reported before anyone adopts it.

CI also fails when committed `khipu_sdk/_generated/` differs from a fresh
`make generate-all`, so the overlay can be neither bypassed nor hand-applied.

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

`ruff` and `mypy` also skip `khipu_sdk/_generated/` (see `[tool.ruff]` and
`[tool.mypy]`), because that code is machine-produced and must never be
hand-edited, so findings there could only be silenced rather than fixed. Every
hand-written module is still linted and type-checked.

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

## Releases

Merging to `master` does **not** release anything: it creates no tag, no GitHub
Release and no package upload. A version is published only when the maintainer
publishes a GitHub Release tagged `vX.Y.Z` on a reviewed commit already on
`master`. The release workflows then build a fresh wheel and sdist, check and
smoke-test them, and upload them with PyPI
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC). No PyPI
API token is stored in this repository.

- What changed in each version:
  [CHANGELOG.md](https://github.com/yaselc/khipu-python-sdk/blob/master/CHANGELOG.md).
- Tags and release notes:
  [GitHub Releases](https://github.com/yaselc/khipu-python-sdk/releases).
- How a release is prepared, cut, rehearsed and published:
  [docs/RELEASING.md](https://github.com/yaselc/khipu-python-sdk/blob/master/docs/RELEASING.md).

## License

MIT; see [LICENSE](https://github.com/yaselc/khipu-python-sdk/blob/master/LICENSE). The OpenAPI documents under `openapi/` are
Khipu's publications and are not covered by that license.

Security issues: see [SECURITY.md](https://github.com/yaselc/khipu-python-sdk/blob/master/SECURITY.md). Contributions: see
[CONTRIBUTING.md](https://github.com/yaselc/khipu-python-sdk/blob/master/CONTRIBUTING.md).
