from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum

class TableStatus(str, Enum):
    free = "free"
    occupied = "occupied"
    waiting_for_food = "waiting_for_food"
    bill_requested = "bill_requested"

class Table(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: int = Field(unique=True, index=True, gt=0)
    capacity: int = Field(gt=0, le=30) # o masă nu ar trebui să aibă capacitate sub 1, iar 30 e rezonabil ca un maxim
    status: TableStatus = Field(default=TableStatus.free)
    qr_code_url: Optional[str] = Field(default=None, max_length=255)
    location: Optional[str] = Field(default=None, max_length=100)
    waiter_id: Optional[int] = Field(default=None, foreign_key="user.id")
