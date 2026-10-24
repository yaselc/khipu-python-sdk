from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.charge_error import ChargeError
from ...models.charge_request import ChargeRequest
from ...models.charge_result import ChargeResult
from ...types import Response


def _get_kwargs(
    *,
    body: ChargeRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/automatic-payment/charge-intent",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ChargeError | ChargeResult | None:
    if response.status_code == 201:
        response_201 = ChargeResult.from_dict(response.json())

        return response_201

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 403:
        response_403 = cast(Any, None)
        return response_403

    if response.status_code == 422:
        response_422 = ChargeError.from_dict(response.json())

        return response_422

    if response.status_code == 500:
        response_500 = cast(Any, None)
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | ChargeError | ChargeResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ChargeRequest,
) -> Response[Any | ChargeError | ChargeResult]:
    """Creación de intención de cobro

     Éste método crea una nueva solicitud de cargo para la suscripción especificada.

    Args:
        body (ChargeRequest): Objecto para enviar una solicitud de un nuevo cobro asociado a un id
            de suscripción.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ChargeError | ChargeResult]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: ChargeRequest,
) -> Any | ChargeError | ChargeResult | None:
    """Creación de intención de cobro

     Éste método crea una nueva solicitud de cargo para la suscripción especificada.

    Args:
        body (ChargeRequest): Objecto para enviar una solicitud de un nuevo cobro asociado a un id
            de suscripción.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ChargeError | ChargeResult
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ChargeRequest,
) -> Response[Any | ChargeError | ChargeResult]:
    """Creación de intención de cobro

     Éste método crea una nueva solicitud de cargo para la suscripción especificada.

    Args:
        body (ChargeRequest): Objecto para enviar una solicitud de un nuevo cobro asociado a un id
            de suscripción.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ChargeError | ChargeResult]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: ChargeRequest,
) -> Any | ChargeError | ChargeResult | None:
    """Creación de intención de cobro

     Éste método crea una nueva solicitud de cargo para la suscripción especificada.

    Args:
        body (ChargeRequest): Objecto para enviar una solicitud de un nuevo cobro asociado a un id
            de suscripción.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ChargeError | ChargeResult
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
