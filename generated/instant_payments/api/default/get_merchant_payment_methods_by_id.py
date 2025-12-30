from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.merchant_get_payment_methods import MerchantGetPaymentMethods
from ...types import Response


def _get_kwargs(
    id: float,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v3/merchants/{id}/paymentMethods".format(
            id=quote(str(id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | MerchantGetPaymentMethods | None:
    if response.status_code == 200:
        response_200 = MerchantGetPaymentMethods.from_dict(response.json())

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
) -> Response[Any | MerchantGetPaymentMethods]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    id: float,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | MerchantGetPaymentMethods]:
    """Get payment methods

     Obtiene el listado de medios de pago disponible para una cuenta de cobrador.

    Args:
        id (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | MerchantGetPaymentMethods]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: float,
    *,
    client: AuthenticatedClient | Client,
) -> Any | MerchantGetPaymentMethods | None:
    """Get payment methods

     Obtiene el listado de medios de pago disponible para una cuenta de cobrador.

    Args:
        id (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | MerchantGetPaymentMethods
    """

    return sync_detailed(
        id=id,
        client=client,
    ).parsed


async def asyncio_detailed(
    id: float,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | MerchantGetPaymentMethods]:
    """Get payment methods

     Obtiene el listado de medios de pago disponible para una cuenta de cobrador.

    Args:
        id (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | MerchantGetPaymentMethods]
    """

    kwargs = _get_kwargs(
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: float,
    *,
    client: AuthenticatedClient | Client,
) -> Any | MerchantGetPaymentMethods | None:
    """Get payment methods

     Obtiene el listado de medios de pago disponible para una cuenta de cobrador.

    Args:
        id (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | MerchantGetPaymentMethods
    """

    return (
        await asyncio_detailed(
            id=id,
            client=client,
        )
    ).parsed
