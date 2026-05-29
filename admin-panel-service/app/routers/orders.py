from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth import AdminSession, require_current_admin
from app.service_clients import forward_json


router = APIRouter(prefix="/orders", tags=["orders"])


def query_dict(request: Request) -> dict[str, str]:
    return dict(request.query_params)


@router.get("")
async def list_orders(
    request: Request,
    session: AdminSession = Depends(require_current_admin),
):
    return await forward_json("order", "GET", "/admin/orders", token=session.token, query=query_dict(request))


@router.get("/{order_id}")
async def get_order(order_id: int, session: AdminSession = Depends(require_current_admin)):
    return await forward_json("order", "GET", f"/admin/orders/{order_id}", token=session.token)


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    body: dict[str, Any],
    session: AdminSession = Depends(require_current_admin),
):
    return await forward_json("order", "PATCH", f"/admin/orders/{order_id}/status", token=session.token, body=body)
