from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr


# ---------- Cart ----------

class AddToCartRequest(BaseModel):
    productId: int
    qty: int


class UpdateCartItemRequest(BaseModel):
    qty: int


class CartItemResponse(BaseModel):
    id: int
    productId: int
    productName: str
    sku: str
    unitPrice: int
    qty: int
    lineTotal: int


class CartResponse(BaseModel):
    sessionId: str
    items: list[CartItemResponse]
    total: int


# ---------- Orders ----------

class CreateOrderRequest(BaseModel):
    sessionId: str
    customerName: str
    phone: str
    email: EmailStr
    deliveryType: str
    address: str | None = None
    comment: str | None = None


class OrderItemResponse(BaseModel):
    id: int
    productId: int
    sku: str
    productName: str
    baseType: str
    wattage: int
    colorTemperatureK: int
    unitPrice: int
    qty: int
    lineTotal: int


class StatusHistoryEntry(BaseModel):
    id: int
    fromStatus: str | None
    toStatus: str
    changedBy: str
    comment: str | None
    createdAt: datetime


class OrderResponse(BaseModel):
    id: int
    orderNumber: str
    sessionId: str
    customerName: str
    phone: str
    email: str
    deliveryType: str
    address: str | None
    comment: str | None
    status: str
    itemsCount: int
    total: int
    items: list[OrderItemResponse]
    history: list[StatusHistoryEntry]
    createdAt: datetime
    updatedAt: datetime


class OrderListItem(BaseModel):
    id: int
    orderNumber: str
    customerName: str
    phone: str
    email: str
    status: str
    total: int
    itemsCount: int
    createdAt: datetime


class UpdateStatusRequest(BaseModel):
    status: str
    comment: str | None = None


# ---------- Response wrappers ----------

def data_response(data: Any) -> dict:
    return {"data": data}


def list_response(data: list, page: int, limit: int, total: int) -> dict:
    return {"data": data, "meta": {"page": page, "limit": limit, "total": total}}
