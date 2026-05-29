import os
from typing import Any

import httpx
from fastapi import HTTPException, Response


PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")


def _base_url(service: str) -> str:
    if service == "product":
        return PRODUCT_SERVICE_URL
    if service == "order":
        return ORDER_SERVICE_URL
    raise ValueError(f"Unknown service: {service}")


def _error_detail(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        return {
            "code": f"UPSTREAM_{response.status_code}",
            "message": response.text or response.reason_phrase,
            "details": {},
        }
    if isinstance(payload, dict) and {"code", "message"}.issubset(payload.keys()):
        return payload
    return {
        "code": f"UPSTREAM_{response.status_code}",
        "message": response.reason_phrase,
        "details": payload,
    }


async def forward_json(
    service: str,
    method: str,
    path: str,
    *,
    token: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> dict | Response:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=_base_url(service), timeout=10.0) as client:
        response = await client.request(method, path, params=query, json=body, headers=headers)

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_error_detail(response))
    if response.status_code == 204:
        return Response(status_code=204)
    return response.json()
