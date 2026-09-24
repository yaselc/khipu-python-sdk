"""Generation-time compatibility overlay for Khipu's published OpenAPI documents.

The files under ``openapi/`` are Khipu's documents, committed verbatim and
pinned by sha256. Occasionally the live API returns a value its own document
does not declare, and a client generated verbatim from that document then
refuses a response Khipu really sends. This tool is where such a gap is closed
*without* touching the committed snapshot: it reads the upstream document and
writes a derived copy, which ``make generate-instant`` feeds to the generator.

Every entry is deliberately narrow and strict:

* it names one schema, one property and the exact values to add;
* it records the exact enum Khipu publishes today, and refuses to run if the
  upstream enum is anything else. In particular, once Khipu publishes the added
  value itself, generation fails and says to delete the entry -- the overlay
  can never silently duplicate an upstream value or outlive its reason;
* the output differs from the input only by the inserted enum lines.

Usage::

    python tools/spec_compat.py SOURCE DEST   # write the derived document
    python tools/spec_compat.py --check SOURCE  # only verify the overlay applies
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnumAddition:
    schema: str
    property: str
    #: The enum exactly as Khipu publishes it, in document order.
    published: tuple[str, ...]
    added: tuple[str, ...]
    reason: str


#: Overlay entries for ``openapi/khipu-instant-payments.yaml``.
INSTANT_PAYMENTS: tuple[EnumAddition, ...] = (
    EnumAddition(
        schema="payment-get-payment",
        property="payment_method",
        published=("regular_transfer", "simplified_transfer", "not_available"),
        added=("direct_debit",),
        reason=(
            "GET /v3/payments/{id} returns payment_method=direct_debit for an "
            "Automatic Payments (PAC) charge, observed live in "
            "parle-cl/telemaco#377; Khipu's published document omits it. "
            "See parle-cl/khipu-python-sdk#15."
        ),
    ),
)


class OverlayError(Exception):
    """The upstream document no longer matches what an overlay entry expects."""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_end(lines: list[str], start: int) -> int:
    """Index just past the YAML block whose key sits on ``lines[start]``."""
    base = _indent(lines[start])
    for index in range(start + 1, len(lines)):
        if lines[index].strip() and _indent(lines[index]) <= base:
            return index
    return len(lines)


def _find_key(lines: list[str], key: str, start: int, end: int, what: str) -> int:
    """The single line in ``[start, end)`` declaring ``key:`` at the shallowest depth."""
    pattern = re.compile(rf"^( *){re.escape(key)}:\s*$")
    hits = [i for i in range(start, end) if pattern.match(lines[i].rstrip("\r\n"))]
    if not hits:
        raise OverlayError(f"{what} not found")
    shallowest = min(_indent(lines[i]) for i in hits)
    hits = [i for i in hits if _indent(lines[i]) == shallowest]
    if len(hits) != 1:
        raise OverlayError(f"{what} is declared {len(hits)} times")
    return hits[0]


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def _locate_enum(lines: list[str], entry: EnumAddition) -> tuple[int, list[str]]:
    """Return ``(end_of_items, values)`` for the entry's enum list."""
    label = f"{entry.schema}.{entry.property}"
    schemas = _find_key(lines, "schemas", 0, len(lines), "components.schemas")
    schema = _find_key(
        lines, entry.schema, schemas + 1, _block_end(lines, schemas), f"schema {entry.schema}"
    )
    schema_end = _block_end(lines, schema)
    properties = _find_key(lines, "properties", schema + 1, schema_end, f"{entry.schema}.properties")
    prop = _find_key(
        lines, entry.property, properties + 1, _block_end(lines, properties), f"property {label}"
    )
    enum = _find_key(lines, "enum", prop + 1, _block_end(lines, prop), f"{label}.enum")

    item = re.compile(r"^ *- (.*?)\s*$")
    end = enum + 1
    values: list[str] = []
    while end < len(lines) and (match := item.match(lines[end].rstrip("\r\n"))):
        values.append(_unquote(match.group(1)))
        end += 1
    if not values:
        raise OverlayError(f"{label}.enum is not a block list")
    return end, values


def apply(text: str, entries: tuple[EnumAddition, ...]) -> str:
    """Return ``text`` with every entry's values appended to its enum."""
    lines = text.splitlines(keepends=True)
    for entry in entries:
        label = f"{entry.schema}.{entry.property}"
        end, values = _locate_enum(lines, entry)

        already = [value for value in entry.added if value in values]
        if already:
            raise OverlayError(
                f"Khipu's document now declares {already} in {label}. The "
                f"compatibility overlay is obsolete: delete its entry from "
                f"tools/spec_compat.py and regenerate. ({entry.reason})"
            )
        if tuple(values) != entry.published:
            raise OverlayError(
                f"{label}.enum is now {values}, but the overlay was written "
                f"against {list(entry.published)}. Reconcile the entry with the "
                f"new document before regenerating. ({entry.reason})"
            )

        template = lines[end - 1]
        newline = template[len(template.rstrip("\r\n")):] or "\n"
        prefix = template[: template.index("- ") + 2]
        lines[end:end] = [f"{prefix}{value}{newline}" for value in entry.added]
    return "".join(lines)


def main(argv: list[str]) -> int:
    check = argv[:1] == ["--check"]
    args = argv[1:] if check else argv
    if len(args) != (1 if check else 2):
        print(__doc__, file=sys.stderr)
        return 2

    source = Path(args[0])
    text = source.read_text(encoding="utf-8")
    try:
        derived = apply(text, INSTANT_PAYMENTS)
    except OverlayError as exc:
        print(f"spec_compat: {source}: {exc}", file=sys.stderr)
        return 1

    if check:
        print(f"Compatibility overlay applies cleanly to {source}")
        return 0

    dest = Path(args[1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as handle:
        handle.write(derived)
    print(f"Wrote {dest} ({len(INSTANT_PAYMENTS)} compatibility overlay entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
