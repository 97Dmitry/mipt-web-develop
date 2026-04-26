from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product
from app.schemas import data_response

router = APIRouter(prefix="/internal", tags=["internal"])


class DecrementRequest(BaseModel):
    qty: int


@router.get("/products/{product_id}")
async def get_product_internal(product_id: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found", "details": {}})
    return data_response({
        "id": p.id,
        "name": p.name,
        "sku": p.sku,
        "priceMajor": p.price_minor,
        "stockQty": p.stock_qty,
        "baseType": p.base_type,
        "wattage": p.wattage,
        "colorTemperatureK": p.color_temperature_k,
        "isActive": p.is_active,
    })


@router.patch("/products/{product_id}/stock/decrement")
async def decrement_stock(product_id: int, body: DecrementRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.id == product_id).with_for_update()
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found", "details": {}})
    if p.stock_qty < body.qty:
        raise HTTPException(status_code=409, detail={
            "code": "INSUFFICIENT_STOCK",
            "message": "Not enough stock",
            "details": {"available": p.stock_qty, "requested": body.qty},
        })
    p.stock_qty -= body.qty
    await db.commit()
    return data_response({"id": p.id, "stockQty": p.stock_qty})
