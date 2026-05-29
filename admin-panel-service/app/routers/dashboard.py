from fastapi import APIRouter, Depends

from app.auth import AdminSession, require_current_admin
from app.schemas import data_response
from app.service_clients import forward_json


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _total_orders_for_status(session: AdminSession, status: str) -> int:
    envelope = await forward_json(
        "order",
        "GET",
        "/admin/orders",
        token=session.token,
        query={"status": status, "page": 1, "limit": 1},
    )
    if not isinstance(envelope, dict):
        return 0
    meta = envelope.get("meta") or {}
    return int(meta.get("total") or 0)


@router.get("/summary")
async def dashboard_summary(session: AdminSession = Depends(require_current_admin)):
    products_envelope = await forward_json(
        "product",
        "GET",
        "/products",
        token=session.token,
        query={"page": 1, "limit": 100},
    )
    products = products_envelope.get("data", []) if isinstance(products_envelope, dict) else []
    active_products = [p for p in products if p.get("isActive")]
    low_stock_products = [p for p in active_products if int(p.get("stockQty") or 0) <= 10]
    new_orders = await _total_orders_for_status(session, "new")
    processing_orders = (
        await _total_orders_for_status(session, "confirmed")
        + await _total_orders_for_status(session, "packing")
    )

    return data_response(
        {
            "activeProducts": len(active_products),
            "lowStockProducts": len(low_stock_products),
            "newOrders": new_orders,
            "processingOrders": processing_orders,
        }
    )
