from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.predict_get_predict_all import PredictGetPredictAll
from ...types import UNSET, Response


def _get_kwargs(
    *,
    payer_email: str,
    amount: str,
    currency: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["payer_email"] = payer_email

    params["amount"] = amount

    params["currency"] = currency

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v3/predict/all",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | PredictGetPredictAll | None:
    if response.status_code == 200:
        response_200 = PredictGetPredictAll.from_dict(response.json())

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
) -> Response[Any | PredictGetPredictAll]:
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
    amount: str,
    currency: str,
) -> Response[Any | PredictGetPredictAll]:
    """Get payment prediction for all banks

     Predicción acerca del resultado de un pago para cada uno de los bancos disponibles para la cuenta de
    cobro, sin necesidad de indicar un banco. Permite ofrecerle al pagador solo los bancos con los que
    el pago podría funcionar.

    Los bancos incluidos son los mismos que devuelve `GET /v3/banks`, en el mismo orden. La respuesta
    incluye todos los bancos, no solo aquellos cuyo resultado es `OK`; el integrador debe filtrar por el
    campo `result`. Si la cuenta de cobro no tiene bancos disponibles, el arreglo `banks` viene vacío.

    Se realiza una predicción por banco, por lo que el tiempo de respuesta crece con la cantidad de
    bancos disponibles.

    Args:
        payer_email (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PredictGetPredictAll]
    """

    kwargs = _get_kwargs(
        payer_email=payer_email,
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
    amount: str,
    currency: str,
) -> Any | PredictGetPredictAll | None:
    """Get payment prediction for all banks

     Predicción acerca del resultado de un pago para cada uno de los bancos disponibles para la cuenta de
    cobro, sin necesidad de indicar un banco. Permite ofrecerle al pagador solo los bancos con los que
    el pago podría funcionar.

    Los bancos incluidos son los mismos que devuelve `GET /v3/banks`, en el mismo orden. La respuesta
    incluye todos los bancos, no solo aquellos cuyo resultado es `OK`; el integrador debe filtrar por el
    campo `result`. Si la cuenta de cobro no tiene bancos disponibles, el arreglo `banks` viene vacío.

    Se realiza una predicción por banco, por lo que el tiempo de respuesta crece con la cantidad de
    bancos disponibles.

    Args:
        payer_email (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PredictGetPredictAll
    """

    return sync_detailed(
        client=client,
        payer_email=payer_email,
        amount=amount,
        currency=currency,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    payer_email: str,
    amount: str,
    currency: str,
) -> Response[Any | PredictGetPredictAll]:
    """Get payment prediction for all banks

     Predicción acerca del resultado de un pago para cada uno de los bancos disponibles para la cuenta de
    cobro, sin necesidad de indicar un banco. Permite ofrecerle al pagador solo los bancos con los que
    el pago podría funcionar.

    Los bancos incluidos son los mismos que devuelve `GET /v3/banks`, en el mismo orden. La respuesta
    incluye todos los bancos, no solo aquellos cuyo resultado es `OK`; el integrador debe filtrar por el
    campo `result`. Si la cuenta de cobro no tiene bancos disponibles, el arreglo `banks` viene vacío.

    Se realiza una predicción por banco, por lo que el tiempo de respuesta crece con la cantidad de
    bancos disponibles.

    Args:
        payer_email (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | PredictGetPredictAll]
    """

    kwargs = _get_kwargs(
        payer_email=payer_email,
        amount=amount,
        currency=currency,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    payer_email: str,
    amount: str,
    currency: str,
) -> Any | PredictGetPredictAll | None:
    """Get payment prediction for all banks

     Predicción acerca del resultado de un pago para cada uno de los bancos disponibles para la cuenta de
    cobro, sin necesidad de indicar un banco. Permite ofrecerle al pagador solo los bancos con los que
    el pago podría funcionar.

    Los bancos incluidos son los mismos que devuelve `GET /v3/banks`, en el mismo orden. La respuesta
    incluye todos los bancos, no solo aquellos cuyo resultado es `OK`; el integrador debe filtrar por el
    campo `result`. Si la cuenta de cobro no tiene bancos disponibles, el arreglo `banks` viene vacío.

    Se realiza una predicción por banco, por lo que el tiempo de respuesta crece con la cantidad de
    bancos disponibles.

    Args:
        payer_email (str):
        amount (str):
        currency (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | PredictGetPredictAll
    """

    return (
        await asyncio_detailed(
            client=client,
            payer_email=payer_email,
            amount=amount,
            currency=currency,
        )
    ).parsed
