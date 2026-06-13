from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum
from datetime import datetime, timezone

class OrderStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    served = "served"
    paid = "paid"
    completed = "completed"

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    table_id: int = Field(foreign_key="table.id")
    status: OrderStatus = Field(default=OrderStatus.pending)
    total_price: float = Field(default=0.0, ge=0.0) # Totalul nu poate fi negativ
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    special_requests: Optional[str] = Field(default=None, max_length=500)
