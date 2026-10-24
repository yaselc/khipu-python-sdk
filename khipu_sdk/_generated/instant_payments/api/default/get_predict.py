from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.predict_get_predict import PredictGetPredict
from ...types import UNSET, Response


def _get_kwargs(
    *,
    payer_email: str,
    bank_id: str,
    amount: str,
    currency: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["payer_email"] = payer_email

    params["bank_id"] = bank_id

    params["amount"] = amount

    params["currency"] = currency

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v3/predict",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | PredictGetPredict | None:
    if response.status_code == 200:
        response_200 = PredictGetPredict.from_dict(response.json())

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
) -> Response[Any | PredictGetPredict]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    payer_email: str,
    bank_id: str,
    amount: str,
    currency: str,
) -> Response[Any | PredictGetPredict]:
    """Get payment prediction

     Predicción acerca del resultado de un pago, si podrá o no funcionar. Información adicional como
    máximo posible de transferir a un nuevo destinatario.

    Args:
        payer_email (str):
        bank_id (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PredictGetPredict]
    """

    kwargs = _get_kwargs(
        payer_email=payer_email,
        bank_id=bank_id,
        amount=amount,
        currency=currency,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    payer_email: str,
    bank_id: str,
    amount: str,
    currency: str,
) -> Any | PredictGetPredict | None:
    """Get payment prediction

     Predicción acerca del resultado de un pago, si podrá o no funcionar. Información adicional como
    máximo posible de transferir a un nuevo destinatario.

    Args:
        payer_email (str):
        bank_id (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PredictGetPredict
    """

    return sync_detailed(
        client=client,
        payer_email=payer_email,
        bank_id=bank_id,
        amount=amount,
        currency=currency,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    payer_email: str,
    bank_id: str,
    amount: str,
    currency: str,
) -> Response[Any | PredictGetPredict]:
    """Get payment prediction

     Predicción acerca del resultado de un pago, si podrá o no funcionar. Información adicional como
    máximo posible de transferir a un nuevo destinatario.

    Args:
        payer_email (str):
        bank_id (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PredictGetPredict]
    """

    kwargs = _get_kwargs(
        payer_email=payer_email,
        bank_id=bank_id,
        amount=amount,
        currency=currency,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    payer_email: str,
    bank_id: str,
    amount: str,
    currency: str,
) -> Any | PredictGetPredict | None:
    """Get payment prediction

     Predicción acerca del resultado de un pago, si podrá o no funcionar. Información adicional como
    máximo posible de transferir a un nuevo destinatario.

    Args:
        payer_email (str):
        bank_id (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PredictGetPredict
    """

    return (
        await asyncio_detailed(
            client=client,
            payer_email=payer_email,
            bank_id=bank_id,
            amount=amount,
            currency=currency,
        )
    ).parsed
