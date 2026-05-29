from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.auth import AdminSession, require_current_admin
from app.service_clients import forward_json


router = APIRouter(prefix="/catalog", tags=["catalog"])


def query_dict(request: Request) -> dict[str, str]:
    return dict(request.query_params)


@router.get("/products")
async def list_products(
    request: Request,
    session: AdminSession = Depends(require_current_admin),
):
    return await forward_json("product", "GET", "/products", token=session.token, query=query_dict(request))


@router.get("/products/{product_id}")
async def get_product(product_id: int, session: AdminSession = Depends(require_current_admin)):
    return await forward_json("product", "GET", f"/products/{product_id}", token=session.token)


@router.post("/products", status_code=201)
async def create_product(body: dict[str, Any], session: AdminSession = Depends(require_current_admin)):
    return await forward_json("product", "POST", "/products", token=session.token, body=body)


@router.patch("/products/{product_id}")
async def update_product(
    product_id: int,
    body: dict[str, Any],
    session: AdminSession = Depends(require_current_admin),
):
    return await forward_json("product", "PATCH", f"/products/{product_id}", token=session.token, body=body)


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int, session: AdminSession = Depends(require_current_admin)):
    await forward_json("product", "DELETE", f"/products/{product_id}", token=session.token)
    return Response(status_code=204)


@router.patch("/products/{product_id}/stock")
async def update_product_stock(
    product_id: int,
    body: dict[str, Any],
    session: AdminSession = Depends(require_current_admin),
):
    return await forward_json("product", "PATCH", f"/products/{product_id}/stock", token=session.token, body=body)


@router.get("/categories")
async def list_categories(session: AdminSession = Depends(require_current_admin)):
    return await forward_json("product", "GET", "/categories", token=session.token)


@router.post("/categories", status_code=201)
async def create_category(body: dict[str, Any], session: AdminSession = Depends(require_current_admin)):
    return await forward_json("product", "POST", "/categories", token=session.token, body=body)


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: int,
    body: dict[str, Any],
    session: AdminSession = Depends(require_current_admin),
):
    return await forward_json("product", "PATCH", f"/categories/{category_id}", token=session.token, body=body)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int, session: AdminSession = Depends(require_current_admin)):
    await forward_json("product", "DELETE", f"/categories/{category_id}", token=session.token)
    return Response(status_code=204)
