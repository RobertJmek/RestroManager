from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum

# 1. Definim Enum-ul pentru status
class OrderItemStatus(str, Enum):
    pending = "pending"
    ready_for_pickup = "ready_for_pickup"
    served = "served"

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", gt=0)
    menu_item_id: int = Field(foreign_key="menuitem.id", gt=0)
    quantity: int = Field(default=1, gt=0)
    special_instructions: Optional[str] = Field(default=None, max_length=500)
    
    # 2. Adăugăm câmpul status cu valoarea implicită "pending"
    status: OrderItemStatus = Field(
        default=OrderItemStatus.pending,
        sa_column_kwargs={"server_default": OrderItemStatus.pending}
    )