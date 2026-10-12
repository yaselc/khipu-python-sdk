"""Smoke test for the *installed* distribution.

This script must be run from a clean virtual environment that has the built
wheel or sdist installed, and from a working directory that is NOT the repository
checkout. It proves that the packaged SDK ships the generated clients and can
perform the full facade call path against a local mock HTTP server.

It deliberately imports only from the public ``khipu_sdk`` surface and never
touches the repository sources.
"""

from __future__ import annotations

import json
import sys
import threading
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CREATE_RESPONSE = {
    "payment_id": "gqzdy6chjne9",
    "payment_url": "https://khipu.com/payment/info/gqzdy6chjne9",
    "simplified_transfer_url": "https://app.khipu.com/payment/simplified/gqzdy6chjne9",
    "transfer_url": "https://khipu.com/payment/manual/gqzdy6chjne9",
    "app_url": "khipu:///pos/gqzdy6chjne9",
    "ready_for_terminal": False,
}

GET_RESPONSE = {
    **CREATE_RESPONSE,
    "notification_token": "9dec8aa176c5223026919b3b5579a4776923e646ff3be686b9e6b62ec042e91f",
    "receiver_id": 985101,
    "conciliation_date": "2026-03-01T13:00:00.000Z",
    "subject": "Smoke test",
    "amount": 10000,
    "currency": "CLP",
    "status": "done",
    "status_detail": "normal",
    "body": "Smoke test body",
    "picture_url": "",
    "receipt_url": "",
    "return_url": "",
    "cancel_url": "",
    "notify_url": "",
    "notify_api_version": "3.0",
    "expires_date": "2026-12-31T15:45:00-04:00",
    "attachment_urls": [],
    "bank": "Banco Estado",
    "bank_id": "SDdGj",
    "payer_name": "",
    "payer_email": "",
    "personal_identifier": "",
    "bank_account_number": "",
    "out_of_date_conciliation": False,
    "transaction_id": "SMOKE-TX-1",
    "custom": "SMOKE-CUSTOM",
    "responsible_user_email": "",
    "send_reminders": False,
    "send_email": False,
    "payment_method": "simplified_transfer",
    "funds_source": "debit",
}

received: dict[str, object] = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # silence stderr noise
        pass

    def _respond(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("Content-Length", "0"))
        received["request_body"] = json.loads(self.rfile.read(length))
        received["api_key_sent"] = self.headers.get("x-api-key") is not None
        self._respond(CREATE_RESPONSE)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._respond(GET_RESPONSE)


def main() -> int:
    # Fail loudly if the repository checkout leaked onto sys.path.
    import khipu_sdk

    origin = khipu_sdk.__file__ or ""
    if "site-packages" not in origin:
        print(f"FAIL: khipu_sdk imported from {origin}, not from site-packages")
        return 1

    from khipu_sdk import KhipuClient, KhipuConfig

    # Proves generated/ is present in the distribution.
    import generated.instant_payments.client  # noqa: F401

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        client = KhipuClient(
            KhipuConfig(api_key="smoke-key", base_url=f"http://127.0.0.1:{port}")
        )

        created = client.create_instant_payment(
            amount=Decimal("10000"),
            currency="CLP",
            subject="Smoke test",
            transaction_id="SMOKE-TX-1",
            custom="SMOKE-CUSTOM",
        )
        assert created.payment_id == "gqzdy6chjne9", created
        assert created.payment_url.endswith("gqzdy6chjne9"), created
        assert created.simplified_transfer_url.endswith("gqzdy6chjne9"), created

        assert received["api_key_sent"] is True, "x-api-key header was not sent"
        assert received["request_body"] == {
            "amount": 10000,
            "currency": "CLP",
            "subject": "Smoke test",
            "transaction_id": "SMOKE-TX-1",
            "custom": "SMOKE-CUSTOM",
        }, received["request_body"]

        fetched = client.get_instant_payment(payment_id=created.payment_id)
        assert fetched.payment_id == "gqzdy6chjne9", fetched
        assert fetched.transaction_id == "SMOKE-TX-1", fetched
        assert fetched.custom == "SMOKE-CUSTOM", fetched
        assert fetched.status == "done", fetched
        assert fetched.status_detail == "normal", fetched
        assert fetched.amount == Decimal("10000"), fetched
        assert fetched.currency == "CLP", fetched
        assert fetched.receiver_id == 985101, fetched
    finally:
        server.shutdown()

    print("OK: installed distribution created and retrieved a payment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
