import math
from typing import Any

def paginate_response(items: list[Any], page: int = 1, size: int = 20) -> dict:
    return {
        "items": items,
        "total": len(items),
        "page": page,
        "size": size,
        "pages": max(1, math.ceil(len(items) / size)) if size > 0 else 1
    }
