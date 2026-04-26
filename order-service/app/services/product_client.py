import os
import httpx
from fastapi import HTTPException

PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://localhost:3001")


async def get_product(product_id: int) -> dict:
    async with httpx.AsyncClient(base_url=PRODUCT_SERVICE_URL, timeout=10.0) as client:
        resp = await client.get(f"/internal/products/{product_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail={
                "code": "PRODUCT_NOT_FOUND",
                "message": f"Product {product_id} not found in catalog",
                "details": {},
            })
        resp.raise_for_status()
        return resp.json()["data"]


async def decrement_stock(product_id: int, qty: int) -> None:
    async with httpx.AsyncClient(base_url=PRODUCT_SERVICE_URL, timeout=10.0) as client:
        resp = await client.patch(
            f"/internal/products/{product_id}/stock/decrement",
            json={"qty": qty},
        )
        if resp.status_code == 409:
            detail = resp.json()
            raise HTTPException(status_code=409, detail=detail)
        resp.raise_for_status()
