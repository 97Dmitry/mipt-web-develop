from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=None)

    @classmethod
    def _to_camel(cls, s: str) -> str:
        parts = s.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ---------- Category ----------

class CategoryBase(BaseModel):
    name: str
    slug: str | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    name: str
    slug: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------- Product Image ----------

class ImageIn(BaseModel):
    imageUrl: str
    altText: str | None = None
    sortOrder: int = 0


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    imageUrl: str
    altText: str | None
    sortOrder: int

    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            imageUrl=obj.image_url,
            altText=obj.alt_text,
            sortOrder=obj.sort_order,
        )


# ---------- Product ----------

class ProductCreate(BaseModel):
    sku: str
    name: str
    slug: str | None = None
    description: str
    categoryId: int
    price: int
    stockQty: int = 0
    baseType: str
    wattage: int
    colorTemperatureK: int
    luminousFluxLm: int
    isActive: bool = True
    images: list[ImageIn] = []


class ProductUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    categoryId: int | None = None
    price: int | None = None
    stockQty: int | None = None
    baseType: str | None = None
    wattage: int | None = None
    colorTemperatureK: int | None = None
    luminousFluxLm: int | None = None
    isActive: bool | None = None
    images: list[ImageIn] | None = None


class StockUpdate(BaseModel):
    stockQty: int
    reason: str | None = None


class CategoryShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    slug: str
    description: str
    category: CategoryShort
    price: int
    stockQty: int
    baseType: str
    wattage: int
    colorTemperatureK: int
    luminousFluxLm: int
    isActive: bool
    images: list[ImageResponse]
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_orm(cls, p):
        return cls(
            id=p.id,
            sku=p.sku,
            name=p.name,
            slug=p.slug,
            description=p.description,
            category=CategoryShort.model_validate(p.category),
            price=p.price_minor,
            stockQty=p.stock_qty,
            baseType=p.base_type,
            wattage=p.wattage,
            colorTemperatureK=p.color_temperature_k,
            luminousFluxLm=p.luminous_flux_lm,
            isActive=p.is_active,
            images=[ImageResponse.from_orm_obj(img) for img in p.images],
            createdAt=p.created_at,
            updatedAt=p.updated_at,
        )


# ---------- Pagination Meta ----------

class Meta(BaseModel):
    page: int
    limit: int
    total: int


# ---------- Response wrappers ----------

def data_response(data: Any) -> dict:
    return {"data": data}


def list_response(data: list, page: int, limit: int, total: int) -> dict:
    return {"data": data, "meta": {"page": page, "limit": limit, "total": total}}
