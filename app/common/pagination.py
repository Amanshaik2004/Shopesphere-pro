from typing import Generic, List, TypeVar
import math
from pydantic import BaseModel
from fastapi import Query

T = TypeVar("T")

class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Records fetched successfully"
    data: PaginatedData[T]

class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

def paginate_query(query, params: PaginationParams):
    total = query.count()
    items = query.offset(params.offset).limit(params.page_size).all()
    total_pages = math.ceil(total / params.page_size) if params.page_size > 0 else 0
    return PaginatedData(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages
    )
