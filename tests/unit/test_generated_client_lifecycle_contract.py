"""Pin the generated ``Client`` storage that ``KhipuClient.close()`` relies on (#54).

The generated wrappers build their ``httpx.Client`` lazily in
``get_httpx_client()``, so calling that method to close a pool would first
create one. ``KhipuClient`` therefore reads the private ``_client`` slot, which
is ``None`` until the pool exists. These tests fail if a regeneration renames
that slot, makes it a constructor argument, or stops caching the pool in it --
any of which would make ``close()`` miss a live pool or build an unused one.
"""

from __future__ import annotations

import importlib

import attrs
import httpx
import pytest

GENERATED_CLIENT_MODULES = [
    "generated.instant_payments.client",
    "generated.automatic_payments.client",
]


def _client_class(module_path: str) -> type:
    return importlib.import_module(module_path).Client


@pytest.mark.parametrize("module_path", GENERATED_CLIENT_MODULES)
def test_the_pool_slot_is_private_uninitialised_and_none_by_default(module_path):
    fields = {field.name: field for field in attrs.fields(_client_class(module_path))}

    slot = fields["_client"]
    assert slot.init is False, "the pool must not be injectable through the constructor"
    assert slot.default is None


@pytest.mark.parametrize("module_path", GENERATED_CLIENT_MODULES)
def test_a_new_wrapper_has_no_pool(module_path):
    wrapper = _client_class(module_path)(base_url="https://payment-api.khipu.com")

    assert wrapper._client is None


@pytest.mark.parametrize("module_path", GENERATED_CLIENT_MODULES)
def test_get_httpx_client_builds_once_and_caches_in_the_slot(module_path):
    wrapper = _client_class(module_path)(base_url="https://payment-api.khipu.com")

    first = wrapper.get_httpx_client()
    try:
        assert isinstance(first, httpx.Client)
        assert wrapper._client is first
        assert wrapper.get_httpx_client() is first
    finally:
        first.close()


@pytest.mark.parametrize("module_path", GENERATED_CLIENT_MODULES)
def test_get_httpx_client_does_not_reopen_a_closed_pool(module_path):
    # KhipuClient never calls get_httpx_client() after close(); this pins that
    # the generated layer would hand back the same, closed pool rather than a
    # fresh one, so the facade's own guard is what keeps it fail-closed.
    wrapper = _client_class(module_path)(base_url="https://payment-api.khipu.com")
    pool = wrapper.get_httpx_client()
    pool.close()

    assert wrapper.get_httpx_client() is pool
    assert pool.is_closed
