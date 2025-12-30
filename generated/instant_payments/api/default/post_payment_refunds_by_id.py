from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.payment_post_payment_refunds import PaymentPostPaymentRefunds
from ...models.success import Success
from ...types import UNSET, Response, Unset


def _get_kwargs(
    id: str,
    *,
    body: PaymentPostPaymentRefunds | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v3/payments/{id}/refunds".format(
            id=quote(str(id), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
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
    body: PaymentPostPaymentRefunds | Unset = UNSET,
) -> Response[Any | Success]:
    """Refund payment by Id

     Reembolsa total o parcialmente el monto de un pago. Esta operación solo se puede realizar en los
    comercios que recauden en cuenta Khipu y antes de la rendición de los fondos correspondientes.

    Args:
        id (str):
        body (PaymentPostPaymentRefunds | Unset): Reembolsa total o parcialmente el monto de un
            pago. Esta operación solo se puede realizar en los comercios que recauden en cuenta Khipu
            y antes de la rendición de los fondos correspondientes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Success]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: str,
    *,
    client: AuthenticatedClient | Client,
    body: PaymentPostPaymentRefunds | Unset = UNSET,
) -> Any | Success | None:
    """Refund payment by Id

     Reembolsa total o parcialmente el monto de un pago. Esta operación solo se puede realizar en los
    comercios que recauden en cuenta Khipu y antes de la rendición de los fondos correspondientes.

    Args:
        id (str):
        body (PaymentPostPaymentRefunds | Unset): Reembolsa total o parcialmente el monto de un
            pago. Esta operación solo se puede realizar en los comercios que recauden en cuenta Khipu
            y antes de la rendición de los fondos correspondientes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Success
    """

    return sync_detailed(
        id=id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    id: str,
    *,
    client: AuthenticatedClient | Client,
    body: PaymentPostPaymentRefunds | Unset = UNSET,
) -> Response[Any | Success]:
    """Refund payment by Id

     Reembolsa total o parcialmente el monto de un pago. Esta operación solo se puede realizar en los
    comercios que recauden en cuenta Khipu y antes de la rendición de los fondos correspondientes.

    Args:
        id (str):
        body (PaymentPostPaymentRefunds | Unset): Reembolsa total o parcialmente el monto de un
            pago. Esta operación solo se puede realizar en los comercios que recauden en cuenta Khipu
            y antes de la rendición de los fondos correspondientes.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Success]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: str,
    *,
    client: AuthenticatedClient | Client,
    body: PaymentPostPaymentRefunds | Unset = UNSET,
) -> Any | Success | None:
    """Refund payment by Id

     Reembolsa total o parcialmente el monto de un pago. Esta operación solo se puede realizar en los
    comercios que recauden en cuenta Khipu y antes de la rendición de los fondos correspondientes.

    Args:
        id (str):
        body (PaymentPostPaymentRefunds | Unset): Reembolsa total o parcialmente el monto de un
            pago. Esta operación solo se puede realizar en los comercios que recauden en cuenta Khipu
            y antes de la rendición de los fondos correspondientes.

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
            body=body,
        )
    ).parsed
