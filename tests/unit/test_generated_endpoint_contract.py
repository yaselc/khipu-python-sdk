"""Pin the generated endpoint shape the facade relies on (#42).

``KhipuClient._invoke`` does not call a generated ``sync_detailed``. It runs the
same three steps itself -- ``_get_kwargs``, one request on the client's httpx
client, ``_build_response`` -- so that the HTTP response is still available
when the generated parser raises. That is only correct while ``sync_detailed``
is exactly those three steps. These tests read the committed generated source
and fail if a regeneration changes that shape, adds a step, or renames a hook.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
import textwrap
from pathlib import Path

import pytest

import khipu_sdk.client

#: Every generated endpoint module the facade calls.
FACADE_ENDPOINTS = [
    "generated.instant_payments.api.default.post_payment",
    "generated.instant_payments.api.default.get_payment_by_id",
    "generated.automatic_payments.api.default.create_subscription_1",
    "generated.automatic_payments.api.default.fetch_subscription_status_1",
    "generated.automatic_payments.api.default.create_charge_1",
]


def test_the_list_covers_every_endpoint_the_facade_imports():
    source = Path(khipu_sdk.client.__file__).read_text(encoding="utf-8")
    imported = set(re.findall(r'"(generated\.[a-z_]+\.api\.default\.[a-z0-9_]+)"', source))
    assert imported == set(FACADE_ENDPOINTS)


def _function_body(func) -> list[ast.stmt]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    (definition,) = tree.body
    assert isinstance(definition, ast.FunctionDef)
    body = definition.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # docstring
    return body


@pytest.mark.parametrize("module_path", FACADE_ENDPOINTS)
def test_sync_detailed_is_exactly_get_kwargs_request_build_response(module_path):
    module = importlib.import_module(module_path)
    body = _function_body(module.sync_detailed)

    assert [ast.unparse(statement) for statement in body][1:] == [
        "response = client.get_httpx_client().request(**kwargs)",
        "return _build_response(client=client, response=response)",
    ]

    first = body[0]
    assert isinstance(first, ast.Assign)
    assert ast.unparse(first.targets[0]) == "kwargs"
    call = first.value
    assert isinstance(call, ast.Call) and ast.unparse(call.func) == "_get_kwargs"
    assert not call.args
    # Every argument of sync_detailed except ``client`` is forwarded unchanged.
    forwarded = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}
    parameters = [
        name for name in inspect.signature(module.sync_detailed).parameters if name != "client"
    ]
    assert forwarded == {name: name for name in parameters}


@pytest.mark.parametrize("module_path", FACADE_ENDPOINTS)
def test_the_hooks_have_the_signatures_the_facade_calls(module_path):
    module = importlib.import_module(module_path)

    sync_parameters = inspect.signature(module.sync_detailed).parameters
    kwargs_parameters = inspect.signature(module._get_kwargs).parameters
    assert list(kwargs_parameters) == [name for name in sync_parameters if name != "client"]
    # The facade passes them by keyword.
    assert all(
        p.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for p in kwargs_parameters.values()
    )

    build_parameters = inspect.signature(module._build_response).parameters
    assert list(build_parameters) == ["client", "response"]
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in build_parameters.values())


@pytest.mark.parametrize("module_path", FACADE_ENDPOINTS)
def test_build_response_only_wraps_parse_response(module_path):
    """``_build_response`` adds nothing the facade would need to replicate."""
    module = importlib.import_module(module_path)
    (statement,) = _function_body(module._build_response)

    assert ast.unparse(statement) == (
        "return Response(status_code=HTTPStatus(response.status_code), "
        "content=response.content, headers=response.headers, "
        "parsed=_parse_response(client=client, response=response))"
    )
