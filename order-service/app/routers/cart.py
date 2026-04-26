from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Cart, CartItem
from app.schemas import (
    AddToCartRequest, UpdateCartItemRequest,
    CartResponse, CartItemResponse, data_response,
)
from app.services.product_client import get_product

router = APIRouter(prefix="/cart", tags=["cart"])


def _build_cart_response(cart: Cart) -> CartResponse:
    items = [
        CartItemResponse(
            id=i.id,
            productId=i.product_id,
            productName=i.product_name,
            sku=i.sku,
            unitPrice=i.unit_price_minor,
            qty=i.qty,
            lineTotal=i.line_total_minor,
        )
        for i in cart.items
    ]
    total = sum(i.line_total_minor for i in cart.items)
    return CartResponse(sessionId=cart.session_id, items=items, total=total)


async def _get_or_create_cart(session_id: str, db: AsyncSession) -> Cart:
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.session_id == session_id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(session_id=session_id)
        db.add(cart)
        await db.flush()
        result = await db.execute(
            select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id)
        )
        cart = result.scalar_one()
    return cart


@router.get("/{session_id}")
async def get_cart(session_id: str, db: AsyncSession = Depends(get_db)):
    cart = await _get_or_create_cart(session_id, db)
    await db.commit()
    return data_response(_build_cart_response(cart))


@router.post("/{session_id}/items", status_code=201)
async def add_item(session_id: str, body: AddToCartRequest, db: AsyncSession = Depends(get_db)):
    if body.qty <= 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_QTY", "message": "Qty must be > 0", "details": {}})

    product = await get_product(body.productId)

    cart = await _get_or_create_cart(session_id, db)

    existing = next((i for i in cart.items if i.product_id == body.productId), None)
    if existing:
        new_qty = existing.qty + body.qty
        if new_qty > product["stockQty"]:
            raise HTTPException(status_code=409, detail={
                "code": "INSUFFICIENT_STOCK",
                "message": "Not enough stock",
                "details": {"available": product["stockQty"], "requested": new_qty},
            })
        existing.qty = new_qty
        existing.line_total_minor = existing.unit_price_minor * new_qty
    else:
        if body.qty > product["stockQty"]:
            raise HTTPException(status_code=409, detail={
                "code": "INSUFFICIENT_STOCK",
                "message": "Not enough stock",
                "details": {"available": product["stockQty"], "requested": body.qty},
            })
        item = CartItem(
            cart_id=cart.id,
            product_id=body.productId,
            product_name=product["name"],
            sku=product["sku"],
            unit_price_minor=product["priceMajor"],
            qty=body.qty,
            line_total_minor=product["priceMajor"] * body.qty,
        )
        db.add(item)
        cart.items.append(item)

    await db.commit()
    await db.refresh(cart)
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id)
    )
    cart = result.scalar_one()
    return data_response(_build_cart_response(cart))


@router.patch("/{session_id}/items/{item_id}")
async def update_item(session_id: str, item_id: int, body: UpdateCartItemRequest, db: AsyncSession = Depends(get_db)):
    if body.qty <= 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_QTY", "message": "Qty must be > 0", "details": {}})

    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.session_id == session_id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=404, detail={"code": "CART_NOT_FOUND", "message": "Cart not found", "details": {}})

    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "ITEM_NOT_FOUND", "message": "Cart item not found", "details": {}})

    product = await get_product(item.product_id)
    if body.qty > product["stockQty"]:
        raise HTTPException(status_code=409, detail={
            "code": "INSUFFICIENT_STOCK",
            "message": "Not enough stock",
            "details": {"available": product["stockQty"], "requested": body.qty},
        })

    item.qty = body.qty
    item.line_total_minor = item.unit_price_minor * body.qty
    await db.commit()
    return data_response({"id": item.id, "qty": item.qty, "lineTotal": item.line_total_minor})


@router.delete("/{session_id}/items/{item_id}", status_code=204)
async def remove_item(session_id: str, item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.session_id == session_id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=404, detail={"code": "CART_NOT_FOUND", "message": "Cart not found", "details": {}})

    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "ITEM_NOT_FOUND", "message": "Cart item not found", "details": {}})

    await db.delete(item)
    await db.commit()


@router.delete("/{session_id}", status_code=204)
async def clear_cart(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.session_id == session_id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        return
    for item in cart.items:
        await db.delete(item)
    await db.commit()
