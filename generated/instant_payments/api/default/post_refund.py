from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.refund_post_refund import RefundPostRefund
from ...models.refund_post_refund_2 import RefundPostRefund2
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: RefundPostRefund | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v3/refunds",
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | RefundPostRefund2 | None:
    if response.status_code == 200:
        response_200 = RefundPostRefund2.from_dict(response.json())

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
) -> Response[Any | RefundPostRefund2]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RefundPostRefund | Unset = UNSET,
) -> Response[Any | RefundPostRefund2]:
    """Refund payment

     Devolución total o parcial del monto de un pago. Con `type=full` el monto completo disponible para
    devolver queda marcado para devolución al pagador; con `type=partial` queda marcada la parte
    indicada en `amount`. Se pueden realizar varias devoluciones parciales mientras la billetera de
    devoluciones tenga saldo y el pago mantenga monto disponible para devolver.

    Esta operación requiere habilitación previa: el comercio debe solicitarla a soporte@khipu.com. El
    comercio gestiona una billetera de devoluciones que debe mantener con saldo suficiente
    (recargándola) para concretar las devoluciones; el saldo se puede consultar con [*Get refund wallet
    balance*](#operation/getRefundWalletBalance). Solo se pueden devolver pagos conciliados, hasta 180
    días después de su conciliación.

    Args:
        body (RefundPostRefund | Unset): Datos para solicitar la devolución de un pago.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | RefundPostRefund2]
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
    body: RefundPostRefund | Unset = UNSET,
) -> Any | RefundPostRefund2 | None:
    """Refund payment

     Devolución total o parcial del monto de un pago. Con `type=full` el monto completo disponible para
    devolver queda marcado para devolución al pagador; con `type=partial` queda marcada la parte
    indicada en `amount`. Se pueden realizar varias devoluciones parciales mientras la billetera de
    devoluciones tenga saldo y el pago mantenga monto disponible para devolver.

    Esta operación requiere habilitación previa: el comercio debe solicitarla a soporte@khipu.com. El
    comercio gestiona una billetera de devoluciones que debe mantener con saldo suficiente
    (recargándola) para concretar las devoluciones; el saldo se puede consultar con [*Get refund wallet
    balance*](#operation/getRefundWalletBalance). Solo se pueden devolver pagos conciliados, hasta 180
    días después de su conciliación.

    Args:
        body (RefundPostRefund | Unset): Datos para solicitar la devolución de un pago.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | RefundPostRefund2
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RefundPostRefund | Unset = UNSET,
) -> Response[Any | RefundPostRefund2]:
    """Refund payment

     Devolución total o parcial del monto de un pago. Con `type=full` el monto completo disponible para
    devolver queda marcado para devolución al pagador; con `type=partial` queda marcada la parte
    indicada en `amount`. Se pueden realizar varias devoluciones parciales mientras la billetera de
    devoluciones tenga saldo y el pago mantenga monto disponible para devolver.

    Esta operación requiere habilitación previa: el comercio debe solicitarla a soporte@khipu.com. El
    comercio gestiona una billetera de devoluciones que debe mantener con saldo suficiente
    (recargándola) para concretar las devoluciones; el saldo se puede consultar con [*Get refund wallet
    balance*](#operation/getRefundWalletBalance). Solo se pueden devolver pagos conciliados, hasta 180
    días después de su conciliación.

    Args:
        body (RefundPostRefund | Unset): Datos para solicitar la devolución de un pago.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | RefundPostRefund2]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: RefundPostRefund | Unset = UNSET,
) -> Any | RefundPostRefund2 | None:
    """Refund payment

     Devolución total o parcial del monto de un pago. Con `type=full` el monto completo disponible para
    devolver queda marcado para devolución al pagador; con `type=partial` queda marcada la parte
    indicada en `amount`. Se pueden realizar varias devoluciones parciales mientras la billetera de
    devoluciones tenga saldo y el pago mantenga monto disponible para devolver.

    Esta operación requiere habilitación previa: el comercio debe solicitarla a soporte@khipu.com. El
    comercio gestiona una billetera de devoluciones que debe mantener con saldo suficiente
    (recargándola) para concretar las devoluciones; el saldo se puede consultar con [*Get refund wallet
    balance*](#operation/getRefundWalletBalance). Solo se pueden devolver pagos conciliados, hasta 180
    días después de su conciliación.

    Args:
        body (RefundPostRefund | Unset): Datos para solicitar la devolución de un pago.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | RefundPostRefund2
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
