from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Order, OrderStatusHistory
from app.schemas import (
    UpdateStatusRequest, OrderResponse, OrderListItem,
    OrderItemResponse, StatusHistoryEntry,
    data_response, list_response,
)
from app.services.order_logic import validate_transition

router = APIRouter(prefix="/admin/orders", tags=["admin"])


def _build_order_response(order: Order) -> OrderResponse:
    items = [
        OrderItemResponse(
            id=i.id,
            productId=i.product_id,
            sku=i.sku,
            productName=i.product_name,
            baseType=i.base_type,
            wattage=i.wattage,
            colorTemperatureK=i.color_temperature_k,
            unitPrice=i.unit_price_minor,
            qty=i.qty,
            lineTotal=i.line_total_minor,
        )
        for i in order.items
    ]
    history = [
        StatusHistoryEntry(
            id=h.id,
            fromStatus=h.from_status,
            toStatus=h.to_status,
            changedBy=h.changed_by,
            comment=h.comment,
            createdAt=h.created_at,
        )
        for h in order.history
    ]
    return OrderResponse(
        id=order.id,
        orderNumber=order.order_number,
        sessionId=order.session_id,
        customerName=order.customer_name,
        phone=order.phone,
        email=order.email,
        deliveryType=order.delivery_type,
        address=order.address,
        comment=order.comment,
        status=order.status,
        itemsCount=order.items_count,
        total=order.total_minor,
        items=items,
        history=history,
        createdAt=order.created_at,
        updatedAt=order.updated_at,
    )


@router.get("")
async def list_orders(
    status: str | None = None,
    dateFrom: datetime | None = None,
    dateTo: datetime | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Order)
    if status:
        q = q.where(Order.status == status)
    if dateFrom:
        q = q.where(Order.created_at >= dateFrom)
    if dateTo:
        q = q.where(Order.created_at <= dateTo)
    if search:
        pattern = f"%{search}%"
        q = q.where(or_(
            Order.order_number.ilike(pattern),
            Order.phone.ilike(pattern),
            Order.email.ilike(pattern),
        ))

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit)
    orders = (await db.execute(q)).scalars().all()

    items = [
        OrderListItem(
            id=o.id,
            orderNumber=o.order_number,
            customerName=o.customer_name,
            phone=o.phone,
            email=o.email,
            status=o.status,
            total=o.total_minor,
            itemsCount=o.items_count,
            createdAt=o.created_at,
        )
        for o in orders
    ]
    return list_response(items, page=page, limit=limit, total=total)


@router.get("/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.items), selectinload(Order.history))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order not found", "details": {}})
    return data_response(_build_order_response(order))


@router.patch("/{order_id}/status")
async def update_status(order_id: int, body: UpdateStatusRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.history)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order not found", "details": {}})

    validate_transition(order.status, body.status)

    from_status = order.status
    order.status = body.status
    db.add(OrderStatusHistory(
        order_id=order.id,
        from_status=from_status,
        to_status=body.status,
        changed_by="admin",
        comment=body.comment,
    ))
    await db.commit()
    return data_response({"id": order.id, "status": order.status})
