from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Category, Product
from app.schemas import CategoryResponse, ProductResponse, data_response, list_response

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order, Category.id)
    )
    categories = result.scalars().all()
    return list_response(
        [CategoryResponse.from_orm_obj(category) for category in categories],
        page=1,
        limit=len(categories),
        total=len(categories),
    )


@router.get("/products")
async def list_products(
    search: str | None = None,
    categoryId: int | None = None,
    baseType: str | None = None,
    wattage: int | None = None,
    colorTemperatureK: int | None = None,
    inStock: bool | None = None,
    sortBy: str | None = Query(None, pattern="^(name|price)$"),
    sortDir: str | None = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.category))
        .where(Product.is_active == True)
    )

    if search:
        pattern = f"%{search}%"
        q = q.where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
    if categoryId is not None:
        q = q.where(Product.category_id == categoryId)
    if baseType is not None:
        q = q.where(Product.base_type == baseType)
    if wattage is not None:
        q = q.where(Product.wattage == wattage)
    if colorTemperatureK is not None:
        q = q.where(Product.color_temperature_k == colorTemperatureK)
    if inStock is True:
        q = q.where(Product.stock_qty > 0)
    elif inStock is False:
        q = q.where(Product.stock_qty == 0)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    if sortBy == "price":
        order_col = Product.price_minor
    else:
        order_col = Product.name
    if sortDir == "desc":
        order_col = order_col.desc()

    q = q.order_by(order_col).offset((page - 1) * limit).limit(limit)
    products = (await db.execute(q)).scalars().all()

    return list_response([ProductResponse.from_orm(product) for product in products], page=page, limit=limit, total=total)


@router.get("/products/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).options(selectinload(Product.images), selectinload(Product.category)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found", "details": {}})
    return data_response(ProductResponse.from_orm(product))
