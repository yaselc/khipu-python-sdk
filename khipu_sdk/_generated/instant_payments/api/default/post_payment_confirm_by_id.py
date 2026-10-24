from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.success import Success
from ...types import Response


def _get_kwargs(
    id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v3/payments/{id}/confirm".format(
            id=quote(str(id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | Success | None:
    if response.status_code == 200:
        response_200 = Success.from_dict(response.json())

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
) -> Response[Any | Success]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | Success]:
    """Confirm payment by Id

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Confirmar el pago. Al confirmar el pago, este será rendido al día hábil
    siguiente.

    Args:
        id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Success]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | Success | None:
    """Confirm payment by Id

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Confirmar el pago. Al confirmar el pago, este será rendido al día hábil
    siguiente.

    Args:
        id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Success
    """

    return sync_detailed(
        id=id,
        client=client,
    ).parsed


async def asyncio_detailed(
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | Success]:
    """Confirm payment by Id

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Confirmar el pago. Al confirmar el pago, este será rendido al día hábil
    siguiente.

    Args:
        id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Success]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | Success | None:
    """Confirm payment by Id

     **Advertencia: Esta función sólo está disponible para los clientes que la hayan contratado de forma
    independiente.
    Para utilizarla, póngase en contacto con nosotros en soporte@khipu.com**<br><br>
    Confirmar el pago. Al confirmar el pago, este será rendido al día hábil
    siguiente.

    Args:
        id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Success
    """

    return (
        await asyncio_detailed(
            id=id,
            client=client,
        )
    ).parsed
