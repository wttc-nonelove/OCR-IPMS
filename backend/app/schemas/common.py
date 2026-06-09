from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


def ok(data=None, message: str = "success") -> dict:
    return {"code": 200, "message": message, "data": data}


def paginated(items: list, total: int, page: int, page_size: int) -> dict:
    """返回分页格式的响应"""
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    })
