from sqlmodel import Field, SQLModel
from typing import Optional

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", gt=0)
    menu_item_id: int = Field(foreign_key="menuitem.id", gt=0)
    quantity: int = Field(default=1, gt=0) # Nu poți comanda 0 sau cantități negative
    special_instructions: Optional[str] = Field(default=None, max_length=500)
