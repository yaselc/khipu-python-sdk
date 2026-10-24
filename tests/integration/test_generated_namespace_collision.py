"""The SDK and a consumer's own ``generated`` package coexist (#56).

Until the generated clients moved to ``khipu_sdk._generated``, the SDK shipped
them as a top-level ``generated`` package, and both collisions below were
reproduced against the published wheel:

* a consumer project with a regular ``generated/`` package (one with an
  ``__init__.py``) shadowed the SDK's clients, so every call raised
  ``KhipuConfigurationError`` telling the user to reinstall;
* a consumer project with a namespace-style ``generated/`` directory (no
  ``__init__.py``) became unimportable once the SDK was installed, because the
  SDK's regular package hid it.

Each test runs a fresh interpreter from a synthetic consumer project, so its
``generated`` is first on ``sys.path`` exactly as it is for a script, ``manage.py``
or ``python -m`` started from a project root. The SDK under test comes from
this checkout. ``httpx.HTTPTransport.handle_request`` is replaced in that
interpreter, so the full facade path runs and nothing reaches the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: Runs inside the consumer project. Prints one JSON line describing what it saw.
CONSUMER_SCRIPT = """
import json
import sys

import httpx

PAYMENT_ID = "gqzdy6chjne9"
CREATED = {
    "payment_id": PAYMENT_ID,
    "payment_url": "https://khipu.com/payment/info/" + PAYMENT_ID,
    "simplified_transfer_url": "https://app.khipu.com/payment/simplified/" + PAYMENT_ID,
    "transfer_url": "https://khipu.com/payment/manual/" + PAYMENT_ID,
    "app_url": "khipu:///pos/" + PAYMENT_ID,
    "ready_for_terminal": False,
}
requests = []


def handle_request(self, request):
    requests.append((request.method, request.url.path))
    return httpx.Response(200, json=CREATED, request=request)


httpx.HTTPTransport.handle_request = handle_request

import generated.payroll_api

from khipu_sdk import KhipuClient, KhipuConfig

with KhipuClient(KhipuConfig(api_key="collision-test-key")) as client:
    created = client.create_instant_payment(
        amount=1000, currency="CLP", subject="Collision", transaction_id="ORDER-1"
    )

import generated

print(json.dumps({
    "payment_id": created.payment_id,
    "requests": requests,
    "consumer_marker": generated.payroll_api.MARKER,
    "generated_path": [str(p) for p in generated.__path__],
}))
"""


def run_in(project: Path, code: str) -> subprocess.CompletedProcess[str]:
    """Run ``code`` with ``project`` as the working directory and sys.path[0]."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [env.get("PYTHONPATH"), str(REPO)])
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def consumer_project(root: Path, *, regular: bool) -> Path:
    package = root / "generated"
    (package / "payroll_api").mkdir(parents=True)
    if regular:
        (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "payroll_api" / "__init__.py").write_text(
        'MARKER = "consumer"\n', encoding="utf-8"
    )
    return root


def run_consumer(project: Path) -> dict:
    result = run_in(project, CONSUMER_SCRIPT)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_a_consumer_regular_generated_package_does_not_shadow_the_sdk(tmp_path):
    project = consumer_project(tmp_path, regular=True)

    seen = run_consumer(project)

    assert seen["payment_id"] == "gqzdy6chjne9"
    assert seen["requests"] == [["POST", "/v3/payments"]]
    # The consumer's package really was the one named `generated`.
    assert seen["consumer_marker"] == "consumer"
    assert seen["generated_path"] == [str(project / "generated")]


def test_a_consumer_namespace_generated_directory_stays_importable(tmp_path):
    project = consumer_project(tmp_path, regular=False)

    seen = run_consumer(project)

    assert seen["payment_id"] == "gqzdy6chjne9"
    assert seen["requests"] == [["POST", "/v3/payments"]]
    assert seen["consumer_marker"] == "consumer"
    assert seen["generated_path"] == [str(project / "generated")]


def test_importing_khipu_sdk_does_not_import_the_generated_clients(tmp_path):
    """They load when a client is built, so ``import khipu_sdk`` stays cheap."""
    code = """
import json
import sys

def loaded():
    return sorted(m for m in sys.modules if m.split(".")[:2] == ["khipu_sdk", "_generated"])

import khipu_sdk
after_import = loaded()
khipu_sdk.KhipuClient(khipu_sdk.KhipuConfig(api_key="lazy-test-key"))
print(json.dumps({"after_import": after_import, "after_client": loaded()}))
"""
    result = run_in(tmp_path, code)
    assert result.returncode == 0, result.stderr
    seen = json.loads(result.stdout)

    assert seen["after_import"] == []
    # Proves the probe can see the package at all.
    assert "khipu_sdk._generated.instant_payments.client" in seen["after_client"]
    assert "khipu_sdk._generated.automatic_payments.client" in seen["after_client"]
