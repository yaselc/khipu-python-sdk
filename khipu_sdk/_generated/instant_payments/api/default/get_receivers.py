from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.get_receivers_order import GetReceiversOrder
from ...models.get_receivers_sort import GetReceiversSort
from ...models.receiver_get_receivers import ReceiverGetReceivers
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    offset: int | Unset = 0,
    max_: int | Unset = 100,
    sort: GetReceiversSort | Unset = GetReceiversSort.ID,
    order: GetReceiversOrder | Unset = GetReceiversOrder.ASC,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["offset"] = offset

    params["max"] = max_

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    json_order: str | Unset = UNSET
    if not isinstance(order, Unset):
        json_order = order.value

    params["order"] = json_order

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v3/receivers/children",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ReceiverGetReceivers | None:
    if response.status_code == 200:
        response_200 = ReceiverGetReceivers.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 403:
        response_403 = cast(Any, None)
        return response_403

    if response.status_code == 404:
        response_404 = cast(Any, None)
        return response_404

    if response.status_code == 500:
        response_500 = cast(Any, None)
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | ReceiverGetReceivers]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    offset: int | Unset = 0,
    max_: int | Unset = 100,
    sort: GetReceiversSort | Unset = GetReceiversSort.ID,
    order: GetReceiversOrder | Unset = GetReceiversOrder.ASC,
) -> Response[Any | ReceiverGetReceivers]:
    """Get receivers

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Obtener la lista de cuentas de cobro asociadas a un integrador.

    Args:
        offset (int | Unset):  Default: 0.
        max_ (int | Unset):  Default: 100. Example: 100.
        sort (GetReceiversSort | Unset):  Default: GetReceiversSort.ID. Example: name.
        order (GetReceiversOrder | Unset):  Default: GetReceiversOrder.ASC. Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ReceiverGetReceivers]
    """

    kwargs = _get_kwargs(
        offset=offset,
        max_=max_,
        sort=sort,
        order=order,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    offset: int | Unset = 0,
    max_: int | Unset = 100,
    sort: GetReceiversSort | Unset = GetReceiversSort.ID,
    order: GetReceiversOrder | Unset = GetReceiversOrder.ASC,
) -> Any | ReceiverGetReceivers | None:
    """Get receivers

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Obtener la lista de cuentas de cobro asociadas a un integrador.

    Args:
        offset (int | Unset):  Default: 0.
        max_ (int | Unset):  Default: 100. Example: 100.
        sort (GetReceiversSort | Unset):  Default: GetReceiversSort.ID. Example: name.
        order (GetReceiversOrder | Unset):  Default: GetReceiversOrder.ASC. Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ReceiverGetReceivers
    """

    return sync_detailed(
        client=client,
        offset=offset,
        max_=max_,
        sort=sort,
        order=order,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    offset: int | Unset = 0,
    max_: int | Unset = 100,
    sort: GetReceiversSort | Unset = GetReceiversSort.ID,
    order: GetReceiversOrder | Unset = GetReceiversOrder.ASC,
) -> Response[Any | ReceiverGetReceivers]:
    """Get receivers

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Obtener la lista de cuentas de cobro asociadas a un integrador.

    Args:
        offset (int | Unset):  Default: 0.
        max_ (int | Unset):  Default: 100. Example: 100.
        sort (GetReceiversSort | Unset):  Default: GetReceiversSort.ID. Example: name.
        order (GetReceiversOrder | Unset):  Default: GetReceiversOrder.ASC. Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ReceiverGetReceivers]
    """

    kwargs = _get_kwargs(
        offset=offset,
        max_=max_,
        sort=sort,
        order=order,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    offset: int | Unset = 0,
    max_: int | Unset = 100,
    sort: GetReceiversSort | Unset = GetReceiversSort.ID,
    order: GetReceiversOrder | Unset = GetReceiversOrder.ASC,
) -> Any | ReceiverGetReceivers | None:
    """Get receivers

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Obtener la lista de cuentas de cobro asociadas a un integrador.

    Args:
        offset (int | Unset):  Default: 0.
        max_ (int | Unset):  Default: 100. Example: 100.
        sort (GetReceiversSort | Unset):  Default: GetReceiversSort.ID. Example: name.
        order (GetReceiversOrder | Unset):  Default: GetReceiversOrder.ASC. Example: asc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ReceiverGetReceivers
    """

    return (
        await asyncio_detailed(
            client=client,
            offset=offset,
            max_=max_,
            sort=sort,
            order=order,
        )
    ).parsed
