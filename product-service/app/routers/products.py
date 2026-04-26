from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from slugify import slugify

from app.database import get_db
from app.models import Product, ProductImage, Category
from app.schemas import (
    ProductCreate, ProductUpdate, StockUpdate,
    ProductResponse, data_response, list_response,
)

router = APIRouter(prefix="/products", tags=["products"])


async def _get_or_404(db: AsyncSession, product_id: int) -> Product:
    result = await db.execute(
        select(Product).options(selectinload(Product.images), selectinload(Product.category))
        .where(Product.id == product_id)
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found", "details": {}})
    return p


async def _check_unique(db: AsyncSession, sku: str | None, slug: str | None, exclude_id: int | None = None):
    if sku:
        q = select(Product).where(Product.sku == sku)
        if exclude_id:
            q = q.where(Product.id != exclude_id)
        if (await db.execute(q)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail={"code": "PRODUCT_DUPLICATE_SKU", "message": "SKU already exists", "details": {}})
    if slug:
        q = select(Product).where(Product.slug == slug)
        if exclude_id:
            q = q.where(Product.id != exclude_id)
        if (await db.execute(q)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail={"code": "PRODUCT_DUPLICATE_SLUG", "message": "Slug already exists", "details": {}})


@router.get("")
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

    return list_response([ProductResponse.from_orm(p) for p in products], page=page, limit=limit, total=total)


@router.get("/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    p = await _get_or_404(db, product_id)
    return data_response(ProductResponse.from_orm(p))


@router.post("", status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    if body.price <= 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PRICE", "message": "Price must be > 0", "details": {}})
    if body.stockQty < 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STOCK", "message": "Stock must be >= 0", "details": {}})

    slug = body.slug or slugify(body.name)
    await _check_unique(db, body.sku, slug)

    cat = await db.get(Category, body.categoryId)
    if cat is None:
        raise HTTPException(status_code=400, detail={"code": "CATEGORY_NOT_FOUND", "message": "Category not found", "details": {}})

    p = Product(
        sku=body.sku,
        name=body.name,
        slug=slug,
        description=body.description,
        category_id=body.categoryId,
        price_minor=body.price,
        stock_qty=body.stockQty,
        base_type=body.baseType,
        wattage=body.wattage,
        color_temperature_k=body.colorTemperatureK,
        luminous_flux_lm=body.luminousFluxLm,
        is_active=body.isActive,
    )
    db.add(p)
    await db.flush()

    for i, img in enumerate(body.images):
        db.add(ProductImage(
            product_id=p.id,
            image_url=img.imageUrl,
            alt_text=img.altText,
            sort_order=img.sortOrder if img.sortOrder else i,
        ))

    await db.commit()

    result = await db.execute(
        select(Product).options(selectinload(Product.images), selectinload(Product.category))
        .where(Product.id == p.id)
    )
    p = result.scalar_one()
    return data_response(ProductResponse.from_orm(p))


@router.patch("/{product_id}")
async def update_product(product_id: int, body: ProductUpdate, db: AsyncSession = Depends(get_db)):
    p = await _get_or_404(db, product_id)

    new_slug = body.slug
    await _check_unique(db, None, new_slug, exclude_id=product_id)

    if body.name is not None:
        p.name = body.name
        if new_slug is None and body.slug is None:
            pass  # keep existing slug
    if body.slug is not None:
        p.slug = body.slug
    if body.description is not None:
        p.description = body.description
    if body.categoryId is not None:
        cat = await db.get(Category, body.categoryId)
        if cat is None:
            raise HTTPException(status_code=400, detail={"code": "CATEGORY_NOT_FOUND", "message": "Category not found", "details": {}})
        p.category_id = body.categoryId
    if body.price is not None:
        if body.price <= 0:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PRICE", "message": "Price must be > 0", "details": {}})
        p.price_minor = body.price
    if body.stockQty is not None:
        if body.stockQty < 0:
            raise HTTPException(status_code=400, detail={"code": "INVALID_STOCK", "message": "Stock must be >= 0", "details": {}})
        p.stock_qty = body.stockQty
    if body.baseType is not None:
        p.base_type = body.baseType
    if body.wattage is not None:
        p.wattage = body.wattage
    if body.colorTemperatureK is not None:
        p.color_temperature_k = body.colorTemperatureK
    if body.luminousFluxLm is not None:
        p.luminous_flux_lm = body.luminousFluxLm
    if body.isActive is not None:
        p.is_active = body.isActive

    if body.images is not None:
        for img in p.images:
            await db.delete(img)
        await db.flush()
        for i, img in enumerate(body.images):
            db.add(ProductImage(
                product_id=p.id,
                image_url=img.imageUrl,
                alt_text=img.altText,
                sort_order=img.sortOrder if img.sortOrder else i,
            ))

    await db.commit()

    result = await db.execute(
        select(Product).options(selectinload(Product.images), selectinload(Product.category))
        .where(Product.id == product_id)
    )
    p = result.scalar_one()
    return data_response(ProductResponse.from_orm(p))


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    p = await _get_or_404(db, product_id)
    p.is_active = False
    await db.commit()


@router.patch("/{product_id}/stock")
async def update_stock(product_id: int, body: StockUpdate, db: AsyncSession = Depends(get_db)):
    p = await _get_or_404(db, product_id)
    if body.stockQty < 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STOCK", "message": "Stock must be >= 0", "details": {}})
    p.stock_qty = body.stockQty
    await db.commit()
    return data_response({"id": p.id, "stockQty": p.stock_qty})
