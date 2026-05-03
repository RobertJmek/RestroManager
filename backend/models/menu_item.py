from sqlmodel import Field, SQLModel
from typing import Optional

class MenuItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category_id: int = Field(foreign_key="category.id", gt=0)
    price: float = Field(gt=0.0) # prețul nu poate fi negativ
    image_url: Optional[str] = Field(default=None, max_length=50000)
    ingredients: Optional[str] = Field(default=None, max_length=1000)
    is_available: bool = Field(default=True)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    dietary_tags: Optional[str] = Field(default=None, max_length=255)
