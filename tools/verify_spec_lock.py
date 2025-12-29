from __future__ import annotations

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
    lock_path = repo / "OPENAPI_SPECS.lock.json"

    if not lock_path.exists():
        raise FileNotFoundError(
            f"Lock file not found: {lock_path}. Run `make lock-specs`."
        )

    lock = json.loads(lock_path.read_text(encoding="utf-8"))

    checks = {
        "instant_payments": repo / "openapi" / "khipu-instant-payments.yaml",
        "automatic_payments": repo / "openapi" / "khipu-automatic-payments.yaml",
    }

    errors: list[str] = []
    for key, path in checks.items():
        if not path.exists():
            errors.append(f"Spec file not found: {path} (run `make download-specs`).")
            continue

        current = sha256(path)
        expected = lock.get(key, {}).get("sha256")

        if expected != current:
            errors.append(
                f"Mismatch for {key}: expected {expected}, got {current} (file: {path})"
            )

    if errors:
        raise SystemExit("Spec lock verification failed:\n- " + "\n- ".join(errors))

    print("OpenAPI spec lock verified")


if __name__ == "__main__":
    main()
