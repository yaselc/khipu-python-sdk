from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    repo = Path(__file__).resolve().parents[1]

    specs = {
        "instant_payments": {
            "url": "https://docs.khipu.com/_bundle/apis/v3/instant-payments/openapi.yaml?download",
            "path": repo / "openapi" / "khipu-instant-payments.yaml",
        },
        "automatic_payments": {
            "url": "https://docs.khipu.com/_bundle/apis/v1/automatic-payments/openapi.yaml?download",
            "path": repo / "openapi" / "khipu-automatic-payments.yaml",
        },
    }

    out: dict[str, dict[str, str]] = {}
    for key, spec in specs.items():
        p: Path = spec["path"]
        if not p.exists():
            raise FileNotFoundError(
                f"Spec file not found: {p}. Run `make download-specs` first."
            )

        out[key] = {
            "url": spec["url"],
            "sha256": sha256(p),
            "downloaded_at": dt.date.today().isoformat(),
        }

    lock_path = repo / "OPENAPI_SPECS.lock.json"
    lock_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {lock_path}")


if __name__ == "__main__":
    main()
