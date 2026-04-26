from datetime import datetime, timezone
from fastapi import HTTPException

TRANSITIONS: dict[str, list[str]] = {
    "new": ["confirmed", "cancelled"],
    "confirmed": ["packing", "cancelled"],
    "packing": ["shipped", "cancelled"],
    "shipped": ["completed"],
    "completed": [],
    "cancelled": [],
}

VALID_STATUSES = set(TRANSITIONS.keys())


def validate_transition(from_status: str, to_status: str) -> None:
    if to_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_STATUS",
            "message": f"Unknown status '{to_status}'",
            "details": {"valid_statuses": list(VALID_STATUSES)},
        })
    allowed = TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_STATUS_TRANSITION",
            "message": f"Cannot transition from '{from_status}' to '{to_status}'",
            "details": {"from": from_status, "to": to_status, "allowed": allowed},
        })


def generate_order_number(order_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ORD-{today}-{order_id:06d}"
