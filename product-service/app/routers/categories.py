from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify

from app.database import get_db
from app.models import Category, Product
from app.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, data_response, list_response

router = APIRouter(prefix="/categories", tags=["categories"])


async def _get_or_404(db: AsyncSession, cat_id: int) -> Category:
    cat = await db.get(Category, cat_id)
    if cat is None:
        raise HTTPException(status_code=404, detail={"code": "CATEGORY_NOT_FOUND", "message": "Category not found", "details": {}})
    return cat


async def _check_unique(db: AsyncSession, name: str | None, slug: str | None, exclude_id: int | None = None):
    if name:
        q = select(Category).where(Category.name == name)
        if exclude_id:
            q = q.where(Category.id != exclude_id)
        if (await db.execute(q)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail={"code": "CATEGORY_DUPLICATE_NAME", "message": "Category name already exists", "details": {}})
    if slug:
        q = select(Category).where(Category.slug == slug)
        if exclude_id:
            q = q.where(Category.id != exclude_id)
        if (await db.execute(q)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail={"code": "CATEGORY_DUPLICATE_SLUG", "message": "Category slug already exists", "details": {}})


@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order, Category.id)
    )
    cats = result.scalars().all()
    return list_response([CategoryResponse.model_validate(c) for c in cats], page=1, limit=len(cats), total=len(cats))


@router.post("", status_code=201)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    slug = body.slug or slugify(body.name)
    await _check_unique(db, body.name, slug)
    cat = Category(
        name=body.name,
        slug=slug,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return data_response(CategoryResponse.model_validate(cat))


@router.patch("/{cat_id}")
async def update_category(cat_id: int, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    cat = await _get_or_404(db, cat_id)
    await _check_unique(db, body.name, body.slug, exclude_id=cat_id)
    if body.name is not None:
        cat.name = body.name
    if body.slug is not None:
        cat.slug = body.slug
    if body.sort_order is not None:
        cat.sort_order = body.sort_order
    if body.is_active is not None:
        cat.is_active = body.is_active
    await db.commit()
    await db.refresh(cat)
    return data_response(CategoryResponse.model_validate(cat))


@router.delete("/{cat_id}", status_code=204)
async def delete_category(cat_id: int, db: AsyncSession = Depends(get_db)):
    cat = await _get_or_404(db, cat_id)
    count = (await db.execute(select(func.count()).select_from(Product).where(Product.category_id == cat_id))).scalar_one()
    if count > 0:
        raise HTTPException(status_code=409, detail={"code": "CATEGORY_IN_USE", "message": "Category has associated products", "details": {"product_count": count}})
    await db.delete(cat)
    await db.commit()
