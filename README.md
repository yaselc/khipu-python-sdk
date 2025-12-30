# Khipu Python SDK

[![CI](https://github.com/parle-cl/khipu-python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/parle-cl/khipu-python-sdk/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/parle-cl/khipu-python-sdk?include_prereleases)](https://github.com/parle-cl/khipu-python-sdk/releases)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

High-level Python SDK for integrating with **Khipu Instant Payments (v3)** and
**Khipu Automatic Payments / PAC (v1)**, built from official OpenAPI specifications.

---

- **Instant Payments API (v3)**
- **Automatic Payments / PAC API (v1)**

This repository is structured to support **automatic OpenAPI client regeneration** without ever editing generated code.
All SDK logic and tests live outside the generated folders.

## Key principles

- All hand-written source code is **in English**.
- **Never edit generated code** under `generated/`.
- Regeneration should be **repeatable and automated** (`make generate-all`).
- Your Django app imports only `khipu_sdk`, not `generated.*`.

## Repository structure

```text
khipu-python-sdk/
  openapi/
    khipu-instant-payments.yaml
    khipu-automatic-payments.yaml

  generated/
    instant_payments/      # OpenAPI generated client (do not edit)
    automatic_payments/    # OpenAPI generated client (do not edit)

  khipu_sdk/
    client.py              # KhipuClient (high-level wrapper)
    config.py              # KhipuConfig
    errors.py              # SDK exceptions
    types.py               # stable result dataclasses

  tests/
    unit/
    integration/

  Makefile
  pyproject.toml
  .gitignore
```

## Khipu API documentation

Official Khipu API documentation is available at:

https://docs.khipu.com/

This repository uses the official OpenAPI specifications published by Khipu
and downloaded directly from their documentation site.

## Requirements

- Python **3.10+**
- `pip`
- (for generation) `openapi-python-client`

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

Install the SDK in editable mode:

```bash
make install
```

Install with dev tooling (tests, lint, generator):

```bash
make install-dev
```


## OpenAPI specifications

The OpenAPI specifications used by this SDK are downloaded directly from Khipu's
official documentation site.

Current sources:

- Instant Payments (v3):
  https://docs.khipu.com/_bundle/apis/v3/instant-payments/openapi.yaml?download

- Automatic Payments / PAC (v1):
  https://docs.khipu.com/_bundle/apis/v1/automatic-payments/openapi.yaml?download

The downloaded files are stored under the `openapi/` directory using stable,
canonical filenames:

```text
openapi/
  khipu-instant-payments.yaml
  khipu-automatic-payments.yaml
```

## Generating clients from OpenAPI specs

The OpenAPI specs are located under `openapi/`.

Generate both clients:

To fully refresh the SDK from the latest Khipu specifications:

```bash
make download-specs
make generate-all
```

Or individually:

```bash
make download-specs
make generate-instant
make generate-automatic
```

Clean generated code:

```bash
make clean-generated
```

## OpenAPI spec lock file

This repository includes a lock file that records the exact upstream OpenAPI specifications used to generate the clients:

- `OPENAPI_SPECS.lock.json` (sha256 + download date)

After downloading/updating the specs, refresh the lock file:

```bash
make download-specs
make lock-specs
```

In CI, the lock file is verified to ensure reproducible generation:

```bash
make verify-spec-lock
```

## Configuration

The SDK reads configuration from environment variables:

- `KHIPU_API_KEY` (required)
- `KHIPU_BASE_URL` (optional, default: `https://payment-api.khipu.com`)
- `KHIPU_TIMEOUT` (optional, default: `10.0`)

Example:

```bash
export KHIPU_API_KEY="your-api-key"
export KHIPU_BASE_URL="https://payment-api.khipu.com"
export KHIPU_TIMEOUT="10"
```

In Python:

```python
from khipu_sdk import KhipuClient, KhipuConfig

cfg = KhipuConfig.from_env()
client = KhipuClient(cfg)
```

## Usage

### Instant Payments (v3)

```python
result = client.create_instant_payment(
    amount=1000.0,
    currency="CLP",
    subject="Test payment",
    transaction_id="ORDER-123",
    return_url="https://your-app.com/payments/return/",
    cancel_url="https://your-app.com/payments/cancel/",
    notify_url="https://your-app.com/payments/webhook/khipu/",
)

print(result.payment_id)
print(result.payment_url)

payment = client.get_instant_payment(payment_id=result.payment_id)
print(payment.status)
```

### Automatic Payments (PAC)

```python
subscription = client.create_subscription(
    name="Jane Doe",
    email="jane.doe@example.com",
    max_amount=50000.0,
    currency="CLP",
    notify_url="https://your-app.com/pac/notify/",
    return_url="https://your-app.com/pac/return/",
    cancel_url="https://your-app.com/pac/cancel/",
)

print(subscription.subscription_id)
print(subscription.redirect_url)

status = client.get_subscription(subscription_id=subscription.subscription_id)
print(status.status)

charge = client.create_charge(
    subscription_id=subscription.subscription_id,
    amount=20000.0,
    subject="Monthly fee",
    body="Subscription monthly charge",
    transaction_id="INVOICE-2025-0001",
)

print(charge.payment_id)
```

## Testing

Run unit tests:

```bash
make test
```

Integration tests are **disabled by default**. Enable them explicitly:

```bash
export KHIPU_RUN_INTEGRATION_TESTS=1
export KHIPU_API_KEY="..."
make test
```

## Using this SDK from a Django project (without publishing to PyPI)

If this SDK lives in a separate repository and is not published to a package index, you have two common options.

### Option A: Editable install from a local checkout

```bash
git clone git@github.com:your-org/khipu-python-sdk.git
cd khipu-python-sdk
make install-dev
```

Then, in your Django project's virtualenv:

```bash
pip install -e /path/to/khipu-python-sdk
```

### Option B: Install directly from Git (recommended for CI)

In your Django project's `requirements.txt`:

```text
git+ssh://git@github.com/parle-cl/khipu-python-sdk.git@master#egg=khipu-python-sdk
```

Or in `pyproject.toml`:

```toml
[project]
dependencies = [
  "khipu-python-sdk @ git+ssh://git@github.com/parle-cl/khipu-python-sdk.git@master",
]
```

## Notes

- `khipu_sdk.client` assumes the typical layout generated by `openapi-python-client`.
  If the generator outputs different module/function names, update only the SDK layer
  (never the generated code).
