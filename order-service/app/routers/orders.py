from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from app.schemas import (
    CreateOrderRequest, OrderResponse, OrderItemResponse,
    StatusHistoryEntry, data_response,
)
from app.services.product_client import get_product, decrement_stock
from app.services.order_logic import generate_order_number

router = APIRouter(prefix="/orders", tags=["orders"])


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


@router.post("", status_code=201)
async def create_order(body: CreateOrderRequest, db: AsyncSession = Depends(get_db)):
    if body.deliveryType not in ("pickup", "courier"):
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_DELIVERY_TYPE",
            "message": "deliveryType must be 'pickup' or 'courier'",
            "details": {},
        })
    if body.deliveryType == "courier" and not body.address:
        raise HTTPException(status_code=400, detail={
            "code": "ADDRESS_REQUIRED",
            "message": "Address is required for courier delivery",
            "details": {},
        })

    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.session_id == body.sessionId)
    )
    cart = result.scalar_one_or_none()

    if cart is None or len(cart.items) == 0:
        raise HTTPException(status_code=400, detail={
            "code": "EMPTY_CART",
            "message": "Cart is empty",
            "details": {},
        })

    product_snapshots = []
    for item in cart.items:
        product = await get_product(item.product_id)
        if product["stockQty"] < item.qty:
            raise HTTPException(status_code=409, detail={
                "code": "INSUFFICIENT_STOCK",
                "message": f"Not enough stock for product {item.sku}",
                "details": {"sku": item.sku, "available": product["stockQty"], "requested": item.qty},
            })
        product_snapshots.append((item, product))

    total = sum(item.line_total_minor for item in cart.items)
    order = Order(
        order_number="TMP",
        session_id=body.sessionId,
        customer_name=body.customerName,
        phone=body.phone,
        email=body.email,
        delivery_type=body.deliveryType,
        address=body.address,
        comment=body.comment,
        status="new",
        items_count=len(cart.items),
        total_minor=total,
    )
    db.add(order)
    await db.flush()

    order.order_number = generate_order_number(order.id)

    for item, product in product_snapshots:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            sku=item.sku,
            product_name=item.product_name,
            base_type=product["baseType"],
            wattage=product["wattage"],
            color_temperature_k=product["colorTemperatureK"],
            unit_price_minor=item.unit_price_minor,
            qty=item.qty,
            line_total_minor=item.line_total_minor,
        ))

    db.add(OrderStatusHistory(
        order_id=order.id,
        from_status=None,
        to_status="new",
        changed_by="system",
        comment="Order created",
    ))

    for item in cart.items:
        await db.delete(item)

    await db.commit()

    for item, _ in product_snapshots:
        await decrement_stock(item.product_id, item.qty)

    result = await db.execute(
        select(Order).options(selectinload(Order.items), selectinload(Order.history))
        .where(Order.id == order.id)
    )
    order = result.scalar_one()
    return data_response(_build_order_response(order))


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
