from sqlmodel import Field, SQLModel
from typing import Optional

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
